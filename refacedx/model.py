#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# refacedx/model.py
#
"""SQLAlchemy data model for Yamaha Reface DX Patches."""

__all__ = [
    'Author',
    'Patch',
    'Tag',
    'configure_session',
    'create_test_data',
    'initdb',
]

import datetime
import logging

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, Sequence, String, Table,
    TypeDecorator, Unicode, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, scoped_session, sessionmaker


log = logging.getLogger(__name__)
Base = declarative_base()
Session = sessionmaker(autocommit=True)
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def ellip(s, length=50, suffix='[...]'):
    if not s or len(s) <= length:
        return s
    else:
        return s[:length-len(suffix)] + suffix


def configure_session(db_uri, sessionmaker=Session, debug=False):
    engine = create_engine(db_uri, echo=debug)
    sessionmaker.configure(bind=engine)
    return sessionmaker()


def create_test_data(session):
    from functools import partial

    with session.begin():
        t1 = Tag(name='lead', description='Lead sound')
        t2 = Tag(name='bass', description='Bass sound')
        t3 = Tag(name='pad', description='Pad sound')
        t4 = Tag(name='bell', description='Bell type sound')
        session.add(t1)
        session.add(t2)
        session.add(t3)
        session.add(t4)

        a1 = Author(name='chris', displayname='Christopher Arndt')
        session.add(a1)

        m1 = Manufacturer(name='yamaha', displayname='Yamaha', sysex_id=b'\0\45\x43')
        session.add(m1)

        d1 = Device(name='refacedx', displayname='Reface DX', sysex_id=b'\x7F\x1C\x05')
        session.add(d1)

        p = partial(Patch, author=a1, manufacturer=m1, device=d1)

        p1 = p(name='PizzaToGo', displayname='PizzaToGo', data=b'\xF0\x43\0\xF7', tags=[t1, t2],
               description="A soft pizzicato sound ideal for percussive comping parts")
        p2 = p(name='Liquid Lead', displayname='Liquid Lead', data=b'\xF0\x43\0\xF7', tags=[t1])
        p3 = p(name='SunrizPad', displayname='SunrizPad', data=b'\xF0\x43\0\xF7', tags=[t3])
        p4 = p(name='Bell Pad', displayname='Bell Pad', data=b'\xF0\x43\0\xF7', tags=[t3])
        session.add(p1)
        session.add(p2)
        session.add(p3)
        session.add(p4)


def get_or_create(session, model, create_method='', create_method_kwargs=None, **kwargs):
    try:
        return session.query(model).filter_by(**kwargs).one(), True
    except NoResultFound:
        kwargs.update(create_method_kwargs or {})

        try:
            with session.begin_nested():
                created = getattr(model, create_method, model)(**kwargs)
                session.add(created)
            return created, False
        except IntegrityError:
            return session.query(model).filter_by(**kwargs).one(), True


def initdb(db_uri=None, session=None, drop_all=False, debug=False):
    """Create all tables in the database and add an initial admin user."""
    if not session:
        session = configure_session(db_uri, debug=debug)

    with session.begin():
        if drop_all:
            Base.metadata.drop_all(bind=session.get_bind())
        Base.metadata.create_all(bind=session.get_bind(), checkfirst=True)

    return session


class HexByteString(TypeDecorator):
    """Convert Python bytestring to string with hexadecimal digits and back for storage."""

    impl = String

    def process_bind_param(self, value, dialect):
        if not isinstance(value, bytes):
            raise TypeError("HexByteString columns only support bytes values.")
        return value.hex()

    def process_result_value(self, value, dialect):
        return bytes.fromhex(value) if value else None


patch_tag = Table('patch_tag', Base.metadata,
    Column('patch_id', Integer, ForeignKey('patch.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)


class Patch(Base):
    """Definition of patch table."""

    __tablename__ = 'patch'
    id = Column(Integer, Sequence('patch_id_seq'), primary_key=True)
    name = Column(Unicode(10), nullable=False)
    displayname = Column(Unicode(50), nullable=False)
    description = Column(Unicode(150))
    rating = Column(Integer)
    tags = relationship('Tag', secondary=patch_tag, backref='patches')
    manufacturer_id = Column(Integer, ForeignKey('manufacturer.id'))
    manufacturer = relationship("Manufacturer", backref=backref('patches', order_by=id))
    device_id = Column(Integer, ForeignKey('device.id'))
    device = relationship("Device", backref=backref('patches', order_by=id))
    # patch data (e.g. SysEx or other MIDI data)
    data = Column(LargeBinary, nullable=False)

    # meta data
    created = Column(DateTime, default=datetime.datetime.now)
    revision = Column(Integer, default=0)
    author_id = Column(Integer, ForeignKey('author.id'))
    author = relationship("Author", backref=backref('patches', order_by=id))

    def __repr__(self):
        return "<Patch(%r (#%i), %r rev=%i (%s)>" % (
            self.name,
            self.id,
            ellip(self.displayname),
            self.revision,
            self.created.strftime(DATETIME_FORMAT)
        )

    def __unicode__(self):
        return self.displayname


class Manufacturer(Base):
    """Definition of manufacturer table."""

    __tablename__ = 'manufacturer'
    id = Column(Integer, Sequence('manufacturer_id_seq'), primary_key=True)
    sysex_id = Column(HexByteString(10), unique=True)
    name = Column(Unicode(50), nullable=False, unique=True)
    displayname = Column(Unicode(150))

    def __repr__(self):
        return "<Manufacturer(%r (#%i), %r)>" % (
            self.name, self.id, self.displayname)

    def __unicode__(self):
        return self.name


class Device(Base):
    """Definition of device table."""

    __tablename__ = 'device'
    id = Column(Integer, Sequence('device_id_seq'), primary_key=True)
    sysex_id = Column(HexByteString(10), unique=True)
    name = Column(Unicode(50), nullable=False, unique=True)
    displayname = Column(Unicode(150))

    def __repr__(self):
        return "<Device(%r (#%i), %r)>" % (
            self.name, self.id, self.displayname)

    def __unicode__(self):
        return self.name


class Author(Base):
    """Definition of author table."""

    __tablename__ = 'author'
    id = Column(Integer, Sequence('author_id_seq'), primary_key=True)
    name = Column(Unicode(50), nullable=False)
    displayname = Column(Unicode(150))

    def __repr__(self):
        return "<Author(%r (#%i), %r)>" % (
            self.name, self.id, self.displayname)

    def __unicode__(self):
        return self.name


class Tag(Base):
    """Definition of question tag table."""

    __tablename__ = 'tag'
    id = Column(Integer, Sequence('tag_id_seq'), primary_key=True)
    name = Column(Unicode(50), nullable=False, unique=True)
    description = Column(Unicode(250))

    def __repr__(self):
        return "<Tag(%r (#%i), %r)>" % (
            self.name, self.id, ellip(self.description))

    def __unicode__(self):
        return self.name


if __name__ == '__main__':
    config = {
        'db_uri': 'sqlite:///data.sqlite',
        #'debug': True,
        'debug': False,
    }
    session = initdb(config['db_uri'], config['debug'])
    create_test_data(session)

    with session.begin():
        print(session.query(Tag).all())
        print(session.query(Author).all())
        for patch in  session.query(Patch).all():
            print(patch)
            print("Tags:", ", ".join(tag.name for tag in patch.tags))
