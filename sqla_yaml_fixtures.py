__version__ = (0, 1, 0)

import functools

import yaml
import sqlalchemy
from sqlalchemy.orm.relationships import RelationshipProperty



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


@functools.lru_cache()
def _get_rel_col_for(src_model, target_model_name):
    '''find the column in src_model that is a relationship to target_model
    @return column name
'''
    #FIXME deal with self-referential m2m
    for name, col in src_model._sa_class_manager.items():
        try:
            target = col.property.mapper.class_
        except AttributeError:
            continue
        if  target.__name__ == target_model_name:
            return name
    raise Exception('Not found')



def _create_obj(ModelBase, store, model_name, key, values):
    '''create obj from values
    @var values (dict): column:value
    '''
    # get reference to SqlAlchemy Mapper
    model = ModelBase._decl_class_registry[model_name]

    # scalars will be passed to mapper __init__
    scalars = {}

    # Nested data will be created after container object,
    # container object reference is found by back_populates
    # each element is a tuple (model-name, field_name, value)
    nested = []

    # references "2many" that are in a list
    many = [] # each element is 2-tuple (field_name, [values])

    for name, value in values.items():
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
            nested.append([rel_name, column.back_populates, value])
        # a reference (key) was passed, get obj from store
        elif isinstance(value, str):
            scalars[name] = store.get(value)
        elif isinstance(value, list):
            if not value:
                continue # empty list
            tgt_model_name = store.get(value[0]).__class__.__name__
            rel_model = ModelBase._decl_class_registry[rel_name]
            col_name = _get_rel_col_for(rel_model, tgt_model_name)
            refs = [rel_model(**{col_name: store.get(v)})
                    for v in value]
            many.append((name, refs))
        # nested field which object was just created
        else:
            scalars[name] = value

    obj = model(**scalars)

    # add a nested objects with reference to parent
    for rel_name, back_populates, value in nested:
        value[back_populates] = obj
        _create_obj(ModelBase, store, rel_name, None, value)

    # save obj in store
    if key:
        store.put(key, obj)

    # 2many references
    for field_name, value_list in many:
        setattr(obj, field_name, value_list)

    return obj


def load(ModelBase, session, fixture_text):
    # make sure backref attributes are created
    sqlalchemy.orm.configure_mappers()

    data = yaml.load(fixture_text)
    store = Store()
    for model_name, instances in data.items():
        for fields in instances:
            key = fields.pop('__key__', None)
            obj = _create_obj(ModelBase, store, model_name, key, fields)
            session.add(obj)
    session.commit()

