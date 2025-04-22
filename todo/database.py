# todo/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ❶ try to read DATABASE_URL from the environment; fall back to todosapp.db
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",          # name you’ll export in shell / .env
    "sqlite:///./todosapp.db"  # default when the var isn’t set
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
