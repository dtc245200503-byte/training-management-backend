from app.routers.auth import router as auth_router
from app.routers.menu import router as menu_router
from app.routers.roles import router as roles_router
from app.routers.users import router as users_router

__all__ = ["auth_router", "users_router", "roles_router", "menu_router"]
