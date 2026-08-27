from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import init_db
from app.controllers import (
    auth_router,
    dashboard_router,
    contact_router,
    template_router,
    campaign_router,
    settings_router,
    public_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o banco de dados e cria as tabelas automaticamente
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de Gerenciamento e Envio de E-mails/Newsletters Multi-tenant",
    version="1.0.0",
    lifespan=lifespan
)

# Garantir criação do diretório estático
settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Registro dos controladores/roteadores
app.include_router(public_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(contact_router)
app.include_router(template_router)
app.include_router(campaign_router)
app.include_router(settings_router)

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head><title>404 - Página Não Encontrada</title><script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-50 flex items-center justify-center min-h-screen p-4 text-center font-sans">
            <div class="bg-white p-8 rounded-2xl shadow-xl border border-slate-100 max-w-md">
                <h1 class="text-6xl font-bold text-indigo-600 mb-2">404</h1>
                <h2 class="text-xl font-bold text-slate-800 mb-2">Página Não Encontrada</h2>
                <p class="text-xs text-slate-500 mb-6">O endereço solicitado não existe ou foi movido.</p>
                <a href="/dashboard" class="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-semibold shadow-md">Voltar ao Início</a>
            </div>
        </body>
        </html>
        """,
        status_code=404
    )
