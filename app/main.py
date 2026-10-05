from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base
import app.models  # Import toàn bộ models để SQLAlchemy nhận diện các định nghĩa bảng

from app.routers.auth import router as auth_router
from app.routers.rbac import router as rbac_router
from app.routers.user_roles import router as user_roles_router
from app.routers.accounts import router as accounts_router
from app.routers.users import router as users_router
from app.routers.me import router as me_router
from app.routers.role_permissions import router as role_permissions_router
from app.routers import curriculum


# 1. Tự động khởi tạo/tạo các bảng chưa có trong Database MySQL (bao gồm bảng subjects)
Base.metadata.create_all(bind=engine)


# 2. Khởi tạo FastAPI application
app = FastAPI(
    title="Training Management System API",
    version="1.0.0"
)

# 3. Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.2.7:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Đăng ký tất cả các Routers vào app
app.include_router(auth_router)
app.include_router(rbac_router)
app.include_router(user_roles_router)
app.include_router(accounts_router)
app.include_router(users_router)
app.include_router(me_router)
app.include_router(role_permissions_router)
app.include_router(curriculum.router)  # Router chương trình đào tạo


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/health/db")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "database": "connected"
    }