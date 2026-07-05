import os
import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contract_analyzer.db")

# For SQLite, we need to allow multithreading access
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, index=True) # UUID string
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    analysis_json = Column(Text, nullable=True) # JSON stored as string

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
