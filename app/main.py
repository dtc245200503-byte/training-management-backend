from fastapi import FastAPI
from app.database import Base, engine
from app.routers.auth import router as auth_router

# Tự động tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Training Management System API",
    description="Backend API cho hệ thống quản lý đào tạo (TMS) - S1-01 Login",
    version="1.0.0",
)

app.include_router(auth_router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "TMS API is running"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
