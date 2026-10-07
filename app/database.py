import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Nếu không tìm thấy biến DATABASE_URL trong file .env, tự động lấy chuỗi SQLite mặc định
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Cấu hình connect_args riêng cho SQLite để tránh lỗi đa luồng trong FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()