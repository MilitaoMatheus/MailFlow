import time
import base64
import json
import hmac
import hashlib
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.repositories.log_repository import LogRepository
from app.services.security_service import SecurityService


class AuthService:
    """Serviço de autenticação, registro e gerenciamento de sessões seguras."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.log_repo = LogRepository(db)

    def register(self, name: str, email: str, password: str, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Cadastra um novo perfil no sistema."""
        name = name.strip() if name else ""
        if not name or len(name) < 2:
            return False, "O nome deve ter no mínimo 2 caracteres.", None

        is_valid, email_or_err = SecurityService.validate_email_syntax(email)
        if not is_valid:
            return False, email_or_err, None

        clean_email = email_or_err

        if not password or len(password) < 6:
            return False, "A senha deve ter no mínimo 6 caracteres.", None

        existing_user = self.user_repo.get_by_email(clean_email)
        if existing_user:
            return False, "Este endereço de e-mail já está cadastrado.", None

        pwd_hash = SecurityService.hash_password(password)
        user = self.user_repo.create(name=name, email=clean_email, password_hash=pwd_hash)

        self.log_repo.create_log(
            user_id=user.id,
            action="CADASTRO",
            description=f"Novo perfil '{user.name}' cadastrado com sucesso.",
            ip_address=ip_address
        )

        return True, "Cadastro realizado com sucesso!", user

    def authenticate(self, email: str, password: str, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Autentica usuário conferindo e-mail e hash da senha."""
        if not email or not password:
            return False, "E-mail e senha são obrigatórios.", None

        user = self.user_repo.get_by_email(email.strip().lower())
        if not user:
            self.log_repo.create_log(
                user_id=None,
                action="LOGIN_FALHA",
                description=f"Tentativa de login falha para e-mail inexistente: {email.strip().lower()}",
                ip_address=ip_address
            )
            return False, "E-mail ou senha incorretos.", None

        if user.status != UserStatus.ATIVO:
            return False, "Este perfil está inativo. Entre em contato com o suporte.", None

        if not SecurityService.verify_password(password, user.password_hash):
            self.log_repo.create_log(
                user_id=user.id,
                action="LOGIN_FALHA",
                description="Tentativa de login falha: senha incorreta.",
                ip_address=ip_address
            )
            return False, "E-mail ou senha incorretos.", None

        self.log_repo.create_log(
            user_id=user.id,
            action="LOGIN",
            description="Login realizado com sucesso.",
            ip_address=ip_address
        )

        return True, "Login realizado com sucesso!", user

    def change_password(self, user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Altera a senha do usuário com verificação da senha atual."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False, "Usuário não encontrado."

        if not SecurityService.verify_password(current_password, user.password_hash):
            return False, "Senha atual incorreta."

        if len(new_password) < 6:
            return False, "A nova senha deve ter no mínimo 6 caracteres."

        new_hash = SecurityService.hash_password(new_password)
        self.user_repo.update_password(user_id, new_hash)

        self.log_repo.create_log(
            user_id=user.id,
            action="ALTERACAO_SENHA",
            description="Senha alterada com sucesso."
        )

        return True, "Senha alterada com sucesso!"

    # --- Gerenciamento de Sessão Criptografada / Assinada ---

    @staticmethod
    def create_session_token(user_id: int, expires_in_seconds: int = 86400 * 7) -> str:
        """Gera um token de sessão assinado com HMAC-SHA256 (independente de libs externas)."""
        payload = {
            "uid": user_id,
            "exp": int(time.time()) + expires_in_seconds
        }
        data_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        data_b64 = base64.urlsafe_b64encode(data_json).decode('ascii').rstrip('=')
        
        signature = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            data_b64.encode('ascii'),
            hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode('ascii').rstrip('=')
        
        return f"{data_b64}.{sig_b64}"

    @staticmethod
    def decode_session_token(token: str) -> Optional[int]:
        """Decodifica e valida a assinatura e expiração do token de sessão."""
        if not token or "." not in token:
            return None
        try:
            data_b64, sig_b64 = token.split(".", 1)
            
            # Recalcular assinatura esperada
            expected_sig = hmac.new(
                settings.SECRET_KEY.encode('utf-8'),
                data_b64.encode('ascii'),
                hashlib.sha256
            ).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('ascii').rstrip('=')

            if not hmac.compare_digest(sig_b64, expected_sig_b64):
                return None

            # Decodificar payload
            rem = len(data_b64) % 4
            if rem > 0:
                data_b64 += "=" * (4 - rem)
            payload = json.loads(base64.urlsafe_b64decode(data_b64.encode('ascii')).decode('utf-8'))

            if int(time.time()) > payload.get("exp", 0):
                return None  # Expirado

            return payload.get("uid")
        except Exception:
            return None
