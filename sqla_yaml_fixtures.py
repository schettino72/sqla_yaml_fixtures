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
        else:
            # a reference (key) was passed, get obj from store
            if isinstance(value, str):
                scalars[name] = store.get(value)
            else:
                # nested field which object was just created
                scalars[name] = value

    obj = model(**scalars)

    # add a nested objects with reference to parent
    for rel_name, back_populates, value in nested:
        value[back_populates] = obj
        _create_obj(ModelBase, store, rel_name, None, value)

    # save obj in store
    if key:
        store.put(key, obj)

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

