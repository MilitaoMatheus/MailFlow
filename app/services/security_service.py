import re
import base64
import hashlib
import hmac
from typing import Tuple
from app.config import settings

# Regex para validação rigorosa de formato de e-mail (RFC 5322 simplificado robusto)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


class SecurityService:
    """Serviço responsável por hash de senhas, criptografia de credenciais SMTP e validações de segurança."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Gera um hash seguro para a senha utilizando PBKDF2 com HMAC-SHA256 e salt de 16 bytes."""
        import os
        salt = os.urandom(16)
        iterations = 100_000
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        # Formato: pbkdf2_sha256$iterations$salt_b64$key_b64
        salt_b64 = base64.b64encode(salt).decode("ascii")
        key_b64 = base64.b64encode(key).decode("ascii")
        return f"pbkdf2_sha256${iterations}${salt_b64}${key_b64}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha em texto confere com o hash seguro."""
        try:
            algorithm, iterations_str, salt_b64, key_b64 = hashed_password.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected_key = base64.b64decode(key_b64.encode("ascii"))
            computed_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(computed_key, expected_key)
        except Exception:
            return False

    @classmethod
    def _get_fernet(cls):
        """Inicializa ou gera chave Fernet para criptografia simétrica de credenciais SMTP."""
        try:
            from cryptography.fernet import Fernet
            key = settings.ENCRYPTION_KEY.encode("utf-8")
            # Se a chave não for válida para fernet (32 url-safe base64-encoded bytes), deriva uma chave fixa com sha256
            if len(key) != 44 or not key.endswith(b"="):
                derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
                return Fernet(derived)
            return Fernet(key)
        except Exception:
            # Fallback seguro para Fernet usando chave derivada da SECRET_KEY
            from cryptography.fernet import Fernet
            derived = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest())
            return Fernet(derived)

    @classmethod
    def encrypt_smtp_password(cls, password: str) -> str:
        """Criptografa a senha SMTP antes de salvar no banco de dados."""
        if not password:
            return ""
        fernet = cls._get_fernet()
        encrypted_bytes = fernet.encrypt(password.encode("utf-8"))
        return encrypted_bytes.decode("ascii")

    @classmethod
    def decrypt_smtp_password(cls, encrypted_password: str) -> str:
        """Descriptografa a senha SMTP para estabelecer conexão."""
        if not encrypted_password:
            return ""
        try:
            fernet = cls._get_fernet()
            decrypted_bytes = fernet.decrypt(encrypted_password.encode("ascii"))
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            # Se não conseguir descriptografar com a chave, não deve expor erro sensível
            return ""

    @staticmethod
    def validate_email_syntax(email: str) -> Tuple[bool, str]:
        """Valida o formato e caracteres de um endereço de e-mail."""
        if not email or not isinstance(email, str):
            return False, "O e-mail não pode ser vazio."

        email_clean = email.strip()
        if len(email_clean) > 254:
            return False, "O endereço de e-mail excede o tamanho máximo permitido (254 caracteres)."

        if not EMAIL_REGEX.match(email_clean):
            return False, f"O formato do e-mail '{email_clean}' é inválido."

        # Checar se tem pontos duplos ou partes vazias
        local_part, _, domain_part = email_clean.partition("@")
        if ".." in email_clean or not local_part or not domain_part:
            return False, f"O formato do e-mail '{email_clean}' contém caracteres inválidos."

        if "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
            return False, f"O domínio do e-mail '{domain_part}' é inválido."

        return True, email_clean.lower()
