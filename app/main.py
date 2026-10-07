from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, SessionLocal, engine
from app.models import RefreshToken, User
from app.routers import auth_router, menu_router, roles_router, users_router
from app.security.password import hash_password

# Tạo bảng tự động và đồng bộ cấu trúc nếu cần
from app.init_db import ensure_db_schema, seed_data

ensure_db_schema()

# Khởi tạo dữ liệu mẫu nếu cần
with SessionLocal() as db:
    seed_data(db)

app = FastAPI(
    title="Training Management System API",
    description="Backend API cho hệ thống quản lý đào tạo (TMS) - Sprint 1",
    version="1.0.0",
)

# Cấu hình CORS cho phép frontend kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(menu_router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "TMS API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
