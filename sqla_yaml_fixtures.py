import yaml
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
    scalars = {}
    for name, value in values.items():
        column = getattr(getattr(model, name), 'property')
        if column and isinstance(column, RelationshipProperty):
            scalars[name] = store.get(value)
        else:
            scalars[name] = value

    obj = model(**scalars)

    # save obj in store
    if key:
        store.put(key, obj)

    return obj


def load(ModelBase, session, fixture_text):
    data = yaml.load(fixture_text)
    store = Store() # key-value
    for model_name, instances in data.items():
        for fields in instances:
            key = fields.pop('__key__', None)
            obj = _create_obj(ModelBase, store, model_name, key, fields)
            session.add(obj)
    session.commit()

