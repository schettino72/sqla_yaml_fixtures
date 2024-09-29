from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, backref

BaseModel = declarative_base()

class User(BaseModel):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(254), unique=True)


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

