import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, PickleType
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(String, primary_key=True)  # Hash of company + url
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String)
    url = Column(String, unique=True, nullable=False)
    posted_at = Column(DateTime, default=datetime.utcnow)
    found_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(PickleType, default=[]) # Serialized list of strings

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(String, primary_key=True) # user_id + interest
    user_id = Column(String, nullable=False)
    interest = Column(String, nullable=False)

def init_db(db_path='jobs.db'):
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
