from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    DATABASE_URL = "sqlite:///./spam_assistant.db"
else:
    DATABASE_URL = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    email_text = Column(Text)
    prediction = Column(String)
    user_label = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    id = Column(Integer, primary_key=True, index=True)
    email_text = Column(Text)
    label = Column(String, index=True)
    risk_score = Column(Integer, index=True)
    hybrid_model_score = Column(Float)
    phishing_score = Column(Float)
    domain_score = Column(Float)
    stylometry_score = Column(Float)
    attack_type = Column(String, index=True)
    cached = Column(Boolean, default=False)
    analysis_mode = Column(String, default="full")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)


def _ensure_column(table_name: str, column_name: str, column_sql: str):
    if not DATABASE_URL.startswith("sqlite"):
        return

    try:
        with engine.begin() as connection:
            result = connection.exec_driver_sql(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in result.fetchall()}
            if column_name not in existing_columns:
                connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
    except Exception as error:
        print(f"Schema migration warning for {table_name}.{column_name}: {error}")


try:
    Base.metadata.create_all(bind=engine)
    _ensure_column("prediction_logs", "hybrid_model_score", "FLOAT")
    _ensure_column("prediction_logs", "phishing_score", "FLOAT")
    _ensure_column("prediction_logs", "domain_score", "FLOAT")
    _ensure_column("prediction_logs", "stylometry_score", "FLOAT")
    _ensure_column("prediction_logs", "attack_type", "VARCHAR")
    _ensure_column("prediction_logs", "cached", "BOOLEAN DEFAULT 0")
    _ensure_column("prediction_logs", "analysis_mode", "VARCHAR DEFAULT 'full'")
    _ensure_column("prediction_logs", "timestamp", "DATETIME")
except Exception as error:
    print(f"Database table creation error: {error}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
