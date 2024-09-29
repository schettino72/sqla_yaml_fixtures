from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship, backref
import pytest

import sqla_yaml_fixtures


#################################################
# Sample schema used on tests

BaseModel = declarative_base()

user_friends = Table(
    'user_friends',
    BaseModel.metadata,
    Column(
        'user_id',
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        primary_key=True,
    ),
    Column(
        'friend_id',
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        primary_key=True,
    )
)

user_instruments = Table(
    'user_instruments',
    BaseModel.metadata,
    Column(
        'user_id',
        Integer,
        ForeignKey('user.id'),
        nullable=False,
        primary_key=True,
    ),
    Column(
        'instrument_id',
        Integer,
        ForeignKey('instrument.id'),
        nullable=False,
        primary_key=True,
    )
)


class Instrument(BaseModel):
    __tablename__ = 'instrument'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True)


class User(BaseModel):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(254), unique=True)
    roles = relationship('Role', overlaps="user")
    friends = relationship(
        'User',
        secondary=user_friends,
        primaryjoin=id==user_friends.c.user_id,
        secondaryjoin=id==user_friends.c.friend_id,
        order_by='User.username',
    )
    instruments = relationship(
        'Instrument',
        secondary=user_instruments,
        order_by='Instrument.name',
    )


class Role(BaseModel):
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('User', overlaps="roles")


class Profile(BaseModel):
    __tablename__ = 'profile'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(
        ForeignKey('user.id', deferrable=True, initially='DEFERRED'),
        nullable=False,
        unique=True)
    user = relationship(
        'User', uselist=False,
        backref=backref('profile', uselist=False,
                        cascade='all, delete-orphan'),
    )

    def __init__(self, nickname=None, the_user=None, **kwargs):
        if nickname is not None and "name" not in kwargs:
            self.name = nickname
        if the_user is not None:
            self.user = the_user
        super(Profile, self).__init__(**kwargs)


class Profile2(BaseModel):
    __tablename__ = 'profile2'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(
        ForeignKey('user.id', deferrable=True, initially='DEFERRED'),
        nullable=False,
        unique=True)
    user = relationship(
        'User', uselist=False,
        backref=backref('profile2', uselist=False,
                        cascade='all, delete-orphan'),
    )

    def __init__(self, user=None, **kwargs):
        assert user is not None
        self.user = user
        super(Profile2, self).__init__(**kwargs)


class Profile3(BaseModel):
    __tablename__ = 'profile3'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(
        ForeignKey('user.id', deferrable=True, initially='DEFERRED'),
        nullable=False,
        unique=True)
    # Note relationship has no back_ref
    user = relationship('User', uselist=False)

    def __init__(self, user=None, **kwargs):
        assert user is not None
        self.user = user
        super(Profile3, self).__init__(**kwargs)


class Group(BaseModel):
    __tablename__ = 'group'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)


class GroupMember(BaseModel):
    __tablename__ = 'group_member'
    id = Column(Integer, primary_key=True)
    group_id = Column(
        ForeignKey('group.id', deferrable=True, initially='DEFERRED'),
        nullable=False, index=True)
    profile_id = Column(
        ForeignKey('profile.id', deferrable=True, initially='DEFERRED'),
        nullable=False, index=True)

    group = relationship(
        'Group',
        backref=backref('members', cascade='all, delete-orphan'),
    )
    profile = relationship(
        'Profile',
        backref=backref('groups', lazy='dynamic'),
    )


class Genre(BaseModel):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    group_id = Column(
        ForeignKey('group.id', deferrable=True, initially='DEFERRED'),
        nullable=False, index=True)
    group = relationship(
        'Group',
        backref=backref('genres', cascade='all, delete-orphan'),
    )

#################################################

# fixtures based on
# https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2
@pytest.fixture(scope="session")
def engine():
    return create_engine('sqlite://')


@pytest.fixture(scope='session')
def tables(engine):
    BaseModel.metadata.create_all(engine)
    yield
    BaseModel.metadata.drop_all(engine)


@pytest.fixture
def session(engine, tables):
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    session = Session(bind=connection)

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


####################################################
# tests


class TestStore:
    def test_put_get(self):
        store = sqla_yaml_fixtures.Store()
        store.put('foo', 'bar')
        assert store.get('foo') == 'bar'

    def test_get_non_existent(self):
        store = sqla_yaml_fixtures.Store()
        assert pytest.raises(KeyError, store.get, 'foo')

    def test_duplicate_key_raises(self):
        store = sqla_yaml_fixtures.Store()
        store.put('foo', 'bar')
        assert pytest.raises(AssertionError, store.put, 'foo', 'second')

    def test_dotted_key(self):
        class Foo:
            bar = 52
        store = sqla_yaml_fixtures.Store()
        store.put('foo', Foo)
        assert store.get('foo.bar.__class__.__name__') == 'int'


def test_insert_simple(session):
    fixture = """
- User:
  - username: deedee
    email: deedee@example.com
  - username: joey
    email: joey@example.commit
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 2
    assert users[0].username == 'deedee'
    assert users[1].username == 'joey'


def test_store_returned(session):
    fixture = """
- User:
  - __key__: dee
    username: deedee
    email: deedee@example.com
"""
    store = sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].username == 'deedee'
    assert users[0].id is not None
    assert users[0].id == store.get('dee').id


def test_insert_invalid(session):
    fixture = """
- User:
  - username: deedee
    email: deedee@example.com
    color_no: blue
"""
    with pytest.raises(Exception) as exc_info:
        sqla_yaml_fixtures.load(BaseModel, session, fixture)
    assert 'User' in str(exc_info)
    assert 'color_no' in str(exc_info)


def test_insert_relation(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
- Profile:
  - user: joey
    name: Jeffrey
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile.name == 'Jeffrey'


def test_insert_nested(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      name: Jeffrey
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile.name == 'Jeffrey'


def test_insert_nested_back_populate(session):
    fixture = """
- User:
  - username: joey
    email: joey@example.com
    profile2:
      name: Jeffrey
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile2.name == 'Jeffrey'


def test_insert_nested_NO_back_populate(session):
    fixture = """
- Profile3:
  - name: Jeffrey
    user:
      username: joey
      email: joey@example.com
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    profiles = session.query(Profile3).all()
    assert len(profiles) == 1
    assert profiles[0].name == 'Jeffrey'
    assert profiles[0].user.username == 'joey'


def test_insert_nested_list(session):
    fixture = """
- Group:
  - name: Ramones
    genres:
      - name: rock
      - name: punk
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    genres = session.query(Genre).all()
    assert len(genres) == 2
    assert genres[0].name == 'rock'
    assert genres[0].group.name == 'Ramones'
    assert genres[1].name == 'punk'
    assert genres[1].group.name == 'Ramones'


def test_init_param(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      nickname: Joey
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile.name == 'Joey'


def test_init_param_ref(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com

- Profile:
  - the_user: {ref: joey}
    name: Jeffrey
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile.name == 'Jeffrey'


def test_2many(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      name: Jeffrey

- Group:
  - name: Ramones
    members: [joey.profile]
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    groups = session.query(Group).all()
    assert len(groups) == 1
    assert groups[0].members[0].profile.name == 'Jeffrey'
    assert groups[0].members[0].profile.groups[0].group.name == 'Ramones'


def test_2many_secondary(session):
    fixture = """
- Instrument:
  - __key__: drums
    name: drums
  - __key__: guitar
    name: guitar

- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    instruments:
      - drums
      - guitar
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).order_by(User.username).all()
    assert users[0].username == 'joey'
    assert users[0].instruments[0].name == 'drums'
    assert users[0].instruments[1].name == 'guitar'


def test_self_referencing_2many_secondary(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
  - __key__: johnny
    username: johnny
  - __key__: tommy
    username: tommy
    email: tommy@example.com
    friends:
      - joey
      - johnny
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).order_by(User.username).all()
    assert len(users[0].friends) == 0
    assert len(users[1].friends) == 0
    assert len(users[2].friends) == 2
    assert users[2].username == 'tommy'
    assert users[2].friends[0].username == 'joey'
    assert users[2].friends[1].username == 'johnny'


def test_2many_no_backref(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    roles:
      - name: owner
      - name: editor
      - name: viewer
"""
    data = sqla_yaml_fixtures.load(BaseModel, session, fixture)
    roles = session.query(Role).all()
    assert len(roles) == 3
    assert roles[0].user_id == data.get('joey').id


def test_2many_invalid_ref(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      name: Jeffrey

- Group:
  - name: Ramones
    members: [joey] # should be joey.profile
"""
    with pytest.raises(Exception) as exc_info:
        sqla_yaml_fixtures.load(BaseModel, session, fixture)
    assert 'Group' in str(exc_info)
    assert 'members' in str(exc_info)
    assert 'joey' in str(exc_info)


def test_2many_empty_is_ok(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      name: Jeffrey

- Group:
  - name: Ramones
    members: []
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    groups = session.query(Group).all()
    assert len(groups) == 1
    assert len(groups[0].members) == 0


def test_empty_entry_is_ok(session):
    fixture = """
- User:
  - __key__: joey
    username: joey
    email: joey@example.com
    profile:
      nickname: Joey

- Profile:

"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(User).all()
    assert len(users) == 1
    assert users[0].profile.name == 'Joey'


def test_yaml_root_sequence(session):
    fixture = """
User:
  - username: deedee
    email: deedee@example.com
"""
    with pytest.raises(Exception) as exc_info:
        sqla_yaml_fixtures.load(BaseModel, session, fixture)
    assert 'Top level YAML' in str(exc_info)
    assert 'sequence' in str(exc_info)


def test_yaml_root_item_single_element(session):
    fixture = """
- User:
  - username: deedee
    email: deedee@example.com
  Group:
  - name: Ramones
"""
    with pytest.raises(Exception) as exc_info:
        sqla_yaml_fixtures.load(BaseModel, session, fixture)
    assert 'Sequence item must contain only one mapper' in str(exc_info)
    assert 'Group' in str(exc_info)
    assert 'User' in str(exc_info)


def test_mapper_must_contain_list(session):
    fixture = """
- User:
    username: deedee
    email: deedee@example.com
"""
    with pytest.raises(Exception) as exc_info:
        sqla_yaml_fixtures.load(BaseModel, session, fixture)
    assert 'must contain a sequence(list)' in str(exc_info)
    assert 'User' in str(exc_info)


### test custom loader

class Person(BaseModel):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(254), unique=True)

    @classmethod
    def create(cls, session, data):
        name = data['username']
        email = '{}@ramones.org'.format(name)
        user = cls(username=name, email=email)
        return user

def test_custom_loader(session):
    fixture = """
- 'Person:create':
  - username: joey
  - username: deedee
"""
    sqla_yaml_fixtures.load(BaseModel, session, fixture)
    users = session.query(Person).order_by(Person.username).all()
    assert len(users) == 2
    assert users[0].username == 'deedee'
    assert users[0].email == 'deedee@ramones.org'
    assert users[1].username == 'joey'
    assert users[1].email == 'joey@ramones.org'
