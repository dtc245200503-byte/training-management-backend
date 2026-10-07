from app.routers.auth import router as auth_router
from app.routers.consultations import router as consultations_router
from app.routers.leads import router as leads_router
from app.routers.menu import router as menu_router
from app.routers.profile import router as profile_router
from app.routers.roles import router as roles_router
from app.routers.subjects import router as subjects_router
from app.routers.training_programs import router as training_programs_router
from app.routers.training_sessions import router as training_sessions_router
from app.routers.users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "roles_router",
    "menu_router",
    "profile_router",
    "subjects_router",
    "training_programs_router",
    "training_sessions_router",
    "consultations_router",
    "leads_router",
]
