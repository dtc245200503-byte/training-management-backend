import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.getcwd())

from app.database import engine
from app.models.curriculum import CurriculumSubject

def create_tables():
    print("Đang khởi tạo bảng curriculum_subjects...")
    # Lấy Base từ metadata của model đã import
    CurriculumSubject.metadata.create_all(bind=engine)
    print("Tạo bảng thành công!")

if __name__ == "__main__":
    create_tables()