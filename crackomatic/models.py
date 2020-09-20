from contextlib import contextmanager

from sqlalchemy import func, create_engine, Column, Integer, String, Boolean, \
    DateTime, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session

Base = declarative_base()
engine = None


class AttrDict(dict):
    __slots__ = ()
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def init_db(path):
    global engine
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(**kwargs):
    """Provide a transactional scope around a series of operations."""
    session = scoped_session(sessionmaker(bind=engine, **kwargs))
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def freeze(model):
    """Create an object that contains the same data as the database object
    but is not attached to any session"""
    attrs = []
    vals = []
    for attr in dir(model):
        val = getattr(model, attr)
        if not attr.startswith('_'):
            attrs.append(attr)
            vals.append(val)
    result = AttrDict(zip(attrs, vals))
    return result


class Audit(Base):
    __tablename__ = 'audits'
    id = Column(Integer, primary_key=True)
    uuid = Column(String(32), nullable=False)
    user = Column(String(64), nullable=False)
    domain = Column(String(64), nullable=False)
    dc_ip = Column(String(64), nullable=True)
    password = Column(String(256), nullable=True)
    ldap_url = Column(String(64), nullable=False)
    ca_file = Column(String(512), nullable=False)
    email_field = Column(String(64), nullable=False)
    user_filter = Column(String(1024), nullable=False)
    admin_filter = Column(String(1024), nullable=False)
    subject = Column(String(256), nullable=False)
    message = Column(String(2048), nullable=False)
    include_cracked = Column(Boolean, nullable=False, default=False)
    start = Column(DateTime, nullable=True)
    end = Column(DateTime, nullable=True)
    state = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=True)
    report = relationship(
        'Report',
        backref='audits',
        uselist=False,
        lazy=True,
    )

    def __repr__(self):
        return '<Audit {}@{}>'.format(self.id, self.start)


class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    audit_id = Column(Integer, ForeignKey('audits.id'), nullable=False)
    total_hashes = Column(Integer, nullable=False)
    cracked = Column(Float, nullable=False)
    mean_pw_len = Column(Float, nullable=True)
    lengths = Column(String)
    cliques = Column(String)
    largest_clique = Column(Integer)
    cliquiness = Column(Float, nullable=True)
    char_classes = Column(String)
    top_basewords = Column(String)
    top_patterns = Column(String)


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    user_facing = Column(Boolean)
    level = Column(String(16))
    timestamp = Column(DateTime)
    user_id = Column(String(256))
    message = Column(Text)

    def __repr__(self):
        return '<Event {}@{}>'.format(self.id, self.timestamp)


class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    logger = Column(String)
    level = Column(String)
    trace = Column(String)
    msg = Column(String)
    created_at = Column(DateTime, default=func.now())


class Meta(Base):
    __tablename__ = 'meta'
    id = Column(Boolean, primary_key=True, default=True, nullable=False)
    # This column stores the app's version, so we know when to migrate
    version = Column(String(16))


class Config(Base):
    __tablename__ = 'config'
    id = Column(Boolean, primary_key=True, default=True, nullable=False)
    config_json = Column(Text)


class LocalUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(256), nullable=False, unique=True)
    password = Column(String(256), nullable=False)
    # Reserved for the future
    active = Column(Boolean(), nullable=False, default=True)
    role = Column(Integer(), nullable=True, default=0)
