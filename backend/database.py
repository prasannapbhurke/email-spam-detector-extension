from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Railway provides DATABASE_URL. If not present, fallback to local SQLite.
db_url = os.getenv("DATABASE_URL")

if not db_url:
    DATABASE_URL = "sqlite:///./spam_assistant.db"
else:
    # Railway's postgres:// must be postgresql:// for SQLAlchemy 1.4+
    DATABASE_URL = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    email_text = Column(Text)
    prediction = Column(String)
    user_label = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Safely create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database table creation error: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
