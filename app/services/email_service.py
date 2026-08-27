from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.email_account import EmailAccount, SmtpSecurity
from app.repositories.email_account_repository import EmailAccountRepository
from app.repositories.log_repository import LogRepository
from app.services.security_service import SecurityService
from app.providers.base import BaseEmailProvider, ConnectionTestResult
from app.providers.smtp_provider import SmtpEmailProvider
from app.providers.mock_provider import MockEmailProvider


class EmailService:
    """Serviço responsável pela orquestração do envio de e-mails e gerenciamento de conexões SMTP por perfil."""

    def __init__(self, db: Session):
        self.db = db
        self.email_acc_repo = EmailAccountRepository(db)
        self.log_repo = LogRepository(db)

    def get_smtp_account(self, user_id: int) -> Optional[EmailAccount]:
        return self.email_acc_repo.get_by_user_id(user_id)

    def save_smtp_settings(
        self,
        user_id: int,
        sender_name: str,
        email: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: Optional[str],
        smtp_security: str = SmtpSecurity.STARTTLS
    ) -> Tuple[bool, str, Optional[EmailAccount]]:
        """Salva as configurações SMTP do perfil com criptografia na senha."""
        if not sender_name or not sender_name.strip():
            return False, "Nome do remetente é obrigatório.", None

        is_valid, clean_email = SecurityService.validate_email_syntax(email)
        if not is_valid:
            return False, f"E-mail do remetente inválido: {clean_email}", None

        if not smtp_host or not smtp_host.strip():
            return False, "Servidor SMTP é obrigatório.", None

        if not smtp_port or smtp_port <= 0 or smtp_port > 65535:
            return False, "Porta SMTP inválida (deve estar entre 1 e 65535).", None

        existing_account = self.email_acc_repo.get_by_user_id(user_id)
        
        # Criptografar nova senha se informada
        encrypted_pwd = ""
        if smtp_password and smtp_password.strip():
            encrypted_pwd = SecurityService.encrypt_smtp_password(smtp_password.strip())
        elif existing_account:
            encrypted_pwd = existing_account.smtp_password_encrypted
        else:
            return False, "Senha ou App Password do SMTP é obrigatória.", None

        account = self.email_acc_repo.save_or_update(
            user_id=user_id,
            sender_name=sender_name.strip(),
            email=clean_email,
            smtp_host=smtp_host.strip(),
            smtp_port=smtp_port,
            smtp_username=smtp_username.strip(),
            smtp_password_encrypted=encrypted_pwd,
            smtp_security=smtp_security.upper()
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="SMTP_CONFIG_SALVA",
            description=f"Configurações SMTP salvas para {account.email} ({account.smtp_host}:{account.smtp_port})."
        )

        return True, "Configurações SMTP salvas com sucesso!", account

    def get_provider(self, user_id: int) -> Tuple[Optional[BaseEmailProvider], Optional[str]]:
        """Instancia o provedor de e-mail apropriado para o perfil."""
        if settings.MOCK_EMAIL_SENDING:
            return MockEmailProvider(), None

        account = self.email_acc_repo.get_by_user_id(user_id)
        if not account or not account.is_active:
            return None, "Nenhuma conta de e-mail / SMTP ativa configurada para o seu perfil. Acesse Configurações para configurar."

        plain_password = SecurityService.decrypt_smtp_password(account.smtp_password_encrypted)
        if not plain_password:
            return None, "Senha do SMTP não pôde ser recuperada. Por favor, reconfigure a senha em Configurações de E-mail."

        provider = SmtpEmailProvider(
            sender_name=account.sender_name,
            sender_email=account.email,
            smtp_host=account.smtp_host,
            smtp_port=account.smtp_port,
            smtp_username=account.smtp_username,
            smtp_password=plain_password,
            smtp_security=account.smtp_security
        )
        return provider, None

    def test_connection(self, user_id: int) -> ConnectionTestResult:
        """Testa a conexão SMTP com as credenciais do usuário."""
        provider, err = self.get_provider(user_id)
        if not provider:
            return ConnectionTestResult(success=False, message=err or "Configuração SMTP não encontrada.")
        
        return provider.test_connection()
