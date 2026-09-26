import uvicorn
from app.config import settings

import sys

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print(f"[MailFlow] Iniciando {settings.APP_NAME} em http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"[MailFlow] Multi-Tenancy Isolado Ativo | Banco de Dados: {settings.DATABASE_URL}")
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
