from app.controllers.auth_controller import router as auth_router
from app.controllers.dashboard_controller import router as dashboard_router
from app.controllers.contact_controller import router as contact_router
from app.controllers.template_controller import router as template_router
from app.controllers.campaign_controller import router as campaign_router
from app.controllers.settings_controller import router as settings_router
from app.controllers.public_controller import router as public_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "contact_router",
    "template_router",
    "campaign_router",
    "settings_router",
    "public_router"
]
