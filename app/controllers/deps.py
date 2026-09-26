from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Recupera o usuário atual a partir do cookie de sessão se presente e válido."""
    token = request.cookies.get("session_token")
    if not token:
        return None

    payload = AuthService.decode_session_payload(token)
    if not payload:
        return None

    user_id = payload.get("uid")
    token_ver = payload.get("ver", 1)

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        return None

    # Validação de invalidação de sessão (ex: após troca de senha)
    if getattr(user, "token_version", 1) != token_ver:
        return None

    return user


def require_auth_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Garante que o usuário esteja autenticado para acessar rotas protegidas."""
    user = get_current_user_optional(request, db)
    if not user:
        # Se for requisição web comum, redireciona para tela de login
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user
