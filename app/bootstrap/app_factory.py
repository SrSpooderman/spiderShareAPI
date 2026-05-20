from fastapi import FastAPI

from app.modules.auth.entrypoints.routes import router as auth_router
from app.modules.steam.entrypoints.routes import router as steam_router
from app.modules.users.entrypoints.routes import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="SpiderShare")

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(steam_router)

    return app
