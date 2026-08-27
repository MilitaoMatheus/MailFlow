import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"🚀 Iniciando {settings.APP_NAME} em http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"🔒 Multi-Tenancy Isolado Ativo | Banco de Dados: {settings.DATABASE_URL}")
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
