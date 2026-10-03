from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.routers.auth import router as auth_router
from app.routers.rbac import router as rbac_router
from app.routers.user_roles import router as user_roles_router
from app.routers.accounts import router as accounts_router
from app.routers.users import router as users_router
from app.routers.me import router as me_router
from app.routers.role_permissions import router as role_permissions_router


app = FastAPI(
    title="Training Management System API"
)

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

app.include_router(auth_router)
app.include_router(rbac_router)
app.include_router(user_roles_router)
app.include_router(accounts_router)
app.include_router(users_router)
app.include_router(me_router)
app.include_router(role_permissions_router)


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