from sqlalchemy import Column, Integer, String, Text
from app.database import Base # Hoặc từ app.db.base tùy cấu hình dự án của bạn

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    subject_name = Column(String(255), nullable=False) # Hoặc Column(String(255), nullable=False) cho tên môn
    description = Column(Text, nullable=True)