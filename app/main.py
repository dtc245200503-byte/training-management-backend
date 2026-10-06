from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.routers.auth import router as auth_router
from app.security.password import hash_password

# Tạo bảng tự động nếu chưa có
Base.metadata.create_all(bind=engine)

# Khởi tạo tài khoản mẫu nếu database chưa có người dùng
with SessionLocal() as db:
    if db.query(User).count() == 0:
        demo_users = [
            User(
                email="user@example.com",
                password_hash=hash_password("password123"),
                full_name="Nguyễn Văn A",
                is_active=True,
            ),
            User(
                email="admin@example.com",
                password_hash=hash_password("password123"),
                full_name="Quản trị viên",
                is_active=True,
            ),
        ]
        db.add_all(demo_users)
        db.commit()

app = FastAPI(
    title="Training Management System API",
    description="Backend API cho hệ thống quản lý đào tạo (TMS) - S1-01 Login",
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


@app.get("/", tags=["Health"])
def root():
    return {"message": "TMS API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
