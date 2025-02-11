from functools import lru_cache

import yaml
import sqlalchemy
from sqlalchemy.orm.relationships import RelationshipProperty


__version__ = (1, 2, 'dev0')


class Store:
    '''Simple key-value store

    Key might be a dot-separated where each name after a dot
    represents and attribute of the value-object.
    '''

    def __init__(self):
        self._store = {}

    def get(self, key):
        parts = key.split('.')
        ref_obj = self._store[parts.pop(0)]
        while parts:
            ref_obj = getattr(ref_obj, parts.pop(0))
        return ref_obj

    def put(self, key, value):
        assert key not in self._store, "Duplicate key:{}".format(key)
        self._store[key] = value


#############################
### ORM

def from_registry(Base, model_name):
    """Compatibility for SQLAlchemy 1.4 changes

    https://github.com/sqlalchemy/sqlalchemy/commit/450f5c0d6519a439f4025c3892fe4cf3ee2d892c
    """
    if hasattr(Base, '_decl_class_registry'): # SQLAlchemy < 1.4
        return Base._decl_class_registry[model_name]
    else:
        return Base.registry._class_registry[model_name]



@lru_cache()
def _get_rel_col_for(src_model, target_model_name):
    '''find the column in src_model that is a relationship to target_model
    @return column name
    '''
    # FIXME deal with self-referential m2m
    for name, col in src_model._sa_class_manager.items():
        try:
            target = col.property.mapper.class_
        except AttributeError:
            continue
        if target.__name__ == target_model_name:
            return name
    msg = 'Mapper `{}` has no field with relationship to type `{}`'
    raise Exception(msg.format(src_model.__name__, target_model_name))


def _create_obj(ModelBase, session, store,
                model_name, creator, key, values):
    '''create obj from values

    :var store (Store):
    :var model_name (str): name of Model/Mapper
    :var creator (str): classmethod name used to create obj.
                        Takes 2 parameters (session, values)
    :var key (str): key for obj in Store
    :var values (dict): column:value
    '''
    # get reference to SqlAlchemy Mapper
    model = from_registry(ModelBase, model_name)

    # scalars will be passed to mapper __init__
    scalars = {}

    # Nested data will be created after container object,
    # container object reference is found by back_populates
    # each element is a tuple (model-name, field_name, value)
    nested = []

    # references "2many" that are in a list
    many = []  # each element is 2-tuple (field_name, [values])

    for name, value in values.items():
        try:
            try:
                column = getattr(getattr(model, name), 'property')
            except AttributeError:
                # __init__ param that is not a column
                if isinstance(value, dict):
                    scalars[name] = store.get(value['ref'])
                else:
                    scalars[name] = value
                continue

            # simple value assignemnt
            if not isinstance(column, RelationshipProperty):
                scalars[name] = value
                continue

            # relationship
            rel_name = column.mapper.class_.__name__
            if isinstance(value, dict):
                # If column includes a back_populates, we assume
                # the constructor of the nested object takes a reference
                # to its parent.
                if column.back_populates:
                    nested.append([rel_name, column.back_populates,
                                   value])
                # If there is no back_populates create the nested object
                # first
                else:
                    scalars[name] = _create_obj(
                        ModelBase, session, store,
                        rel_name, None, None, value)

            # a reference (key) was passed, get obj from store
            elif isinstance(value, str):
                scalars[name] = store.get(value)

            elif isinstance(value, list):
                if not value:
                    continue  # empty list
                # if list element are string they are references
                if isinstance(value[0], str):
                    secondary = getattr(column, 'secondary', None)
                    if secondary is None:
                        # assume association object and find other reference
                        tgt_model_name = store.get(value[0]).__class__.__name__
                        rel_model = from_registry(ModelBase, rel_name)
                        col_name = _get_rel_col_for(rel_model, tgt_model_name)
                        refs = [rel_model(**{col_name: store.get(v)})
                                for v in value]
                    else:
                        refs = [store.get(v) for v in value]
                    many.append((name, refs))

                # else they are a list of nested elements
                else:
                    if column.back_populates:
                        nested.extend(
                            [rel_name, column.back_populates, v]
                            for v in value)
                    # If there is no back_populates create the nested objects
                    # first
                    else:
                        scalars[name] = [_create_obj(
                            ModelBase, session, store,
                            rel_name, None, None, v)
                            for v in value]

            # nested field which object was just created
            else:
                scalars[name] = value

        except Exception as orig_exp:
            raise Exception('Error processing {}.{}={}\n{}'.format(
                model_name, name, value, str(orig_exp)))

    if creator is None:
        creator = 'from_fixture' if hasattr(model, 'from_fixture') else None

    if creator is None:
        obj = model(**scalars)
    else:
        obj = getattr(model, creator)(session, scalars)

    # add a nested objects with reference to parent
    for rel_name, back_populates, value in nested:
        value[back_populates] = obj
        _create_obj(ModelBase, session, store,
                    rel_name, None, None, value)

    # save obj in store
    if key:
        store.put(key, obj)

    # 2many references
    for field_name, value_list in many:
        setattr(obj, field_name, value_list)

    return obj


def load(ModelBase, session, fixture_text, loader=None):
    # make sure backref attributes are created
    sqlalchemy.orm.configure_mappers()

    # Data should be sequence of entry per mapper name
    # to enforce that FKs (__key__ entries) are defined first
    if loader is None:
        loader = yaml.FullLoader
    data = yaml.load(fixture_text, Loader=loader)
    if not isinstance(data, list):
        raise ValueError('Top level YAML should be sequence (list).')

    store = Store()
    for model_entry in data:
        if len(model_entry) != 1:
            msg = ('Sequence item must contain only one mapper,'
                   ' found: {}.')
            raise ValueError(msg.format(', '.join(model_entry.keys())))

        model_name, instances = model_entry.popitem()
        # model_name can be a simple model name or <Name>:<creator>
        if ':' in model_name:
            model_name, creator = model_name.split(':')
        else:
            creator = None

        if instances is None:
            # Ignore empty entry
            continue
        if not isinstance(instances, list):
            msg = '`{}` must contain a sequence(list).'
            raise ValueError(msg.format(model_name))
        for fields in instances:
            key = fields.pop('__key__', None)
            obj = _create_obj(ModelBase, session, store,
                              model_name, creator, key, fields)
            session.add(obj)
    session.commit()
    return store



#############################
### Core SQLAlchemy


async def _insert_row(tables, connection, store, table_name, key, values):
    """
    Create and insert a row into the given table from the provided values.

    :param tables: Dictionary of SQLAlchemy Core tables (replaces models).
    :param connection: SQLAlchemy connection object for executing queries.
    :param store: Store of previously created objects.
    :param table_name: Name of the table (string).
    :param key: Optional key for the object in the store.
    :param values: Column values for the row to be inserted.
    """
    # Get reference to the SQLAlchemy Core table
    table = tables[table_name]

    # Resolve references in values (i.e., nested objects)
    resolved_values = {}
    for name, value in values.items():
        # print('sqlaf - insert row', table, name, value)
        col = table.c.get(name)
        if col is None:
            raise Exception(f'Inavlid column name: {table}.{name} = {value}')
        if col.foreign_keys:
            assert len(col.foreign_keys) == 1
            fk = next(iter(col.foreign_keys))
            fk_col = fk.target_fullname.split('.')[-1]
            obj = store.get(value)
            resolved_values[name] = getattr(obj, fk_col)
        else:
            resolved_values[name] = value

    # Execute insert statement
    insert_stmt = table.insert().values(**resolved_values).returning(table)
    result = await connection.execute(insert_stmt)
    obj = result.fetchone()


    # Store the inserted row if a key is provided
    if key:
        store.put(key, obj)

    return obj


async def load_core(metadata, connection, fixture_text, loader=None):
    """
    Load data from YAML into the database using SQLAlchemy Core.

    :param metadata: SQLAlchemy MetaData object.
    :param connection: SQLAlchemy connection object.
    :param fixture_text: YAML string with data to load.
    :param loader: YAML loader (optional).
    """
    if loader is None:
        loader = yaml.FullLoader
    data = yaml.load(fixture_text, Loader=loader)

    if not isinstance(data, list):
        raise ValueError('Top level YAML should be a sequence (list).')

    # Reflect the tables from the metadata
    tables = {table.name: table for table in metadata.sorted_tables}

    store = Store()

    # Iterate through the YAML data
    for model_entry in data:
        if len(model_entry) != 1:
            raise ValueError('Each YAML entry must contain only one table.')

        table_name, instances = model_entry.popitem()

        if instances is None:
            continue

        if not isinstance(instances, list):
            raise ValueError(f'`{table_name}` must contain a sequence (list).')

        for fields in instances:
            key = fields.pop('__key__', None)
            await _insert_row(tables, connection, store, table_name, key, fields)

    # Commit the transaction
    # await connection.commit()

    return store
