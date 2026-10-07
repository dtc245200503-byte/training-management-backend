import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import Base, SessionLocal, engine
from app.models import RefreshToken, User
from app.routers import (
    auth_router,
    consultations_router,
    leads_router,
    menu_router,
    profile_router,
    roles_router,
    subjects_router,
    training_programs_router,
    training_sessions_router,
    users_router,
)
from app.security.password import hash_password

# Đảm bảo thư mục lưu trữ file tĩnh tồn tại
os.makedirs("uploads/avatars", exist_ok=True)

# Tạo bảng tự động và đồng bộ cấu trúc nếu cần
from app.init_db import ensure_db_schema, seed_data

ensure_db_schema()

# Khởi tạo dữ liệu mẫu nếu cần
with SessionLocal() as db:
    seed_data(db)

app = FastAPI(
    title="Training Management System API",
    description="Backend API cho hệ thống quản lý đào tạo (TMS) - Sprint 1 & Sprint 2",
    version="1.1.0",
)

# Cấu hình CORS cho phép frontend kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phục vụ file tĩnh (ví dụ: avatar người dùng)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(menu_router)
app.include_router(profile_router)
app.include_router(subjects_router)
app.include_router(training_programs_router)
app.include_router(training_sessions_router)
app.include_router(consultations_router)
app.include_router(leads_router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "TMS API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
