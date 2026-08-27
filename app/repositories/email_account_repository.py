from typing import Optional
from app.repositories.base import BaseRepository
from app.models.email_account import EmailAccount, SmtpSecurity


class EmailAccountRepository(BaseRepository):

    def get_by_user_id(self, user_id: int) -> Optional[EmailAccount]:
        """Recupera a configuração SMTP do usuário específico."""
        return self.db.query(EmailAccount).filter(EmailAccount.user_id == user_id).first()

    def save_or_update(
        self,
        user_id: int,
        sender_name: str,
        email: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password_encrypted: str,
        smtp_security: str = SmtpSecurity.STARTTLS
    ) -> EmailAccount:
        """Cria ou atualiza a conta de e-mail/SMTP para o usuário isoladamente."""
        account = self.get_by_user_id(user_id)
        if not account:
            account = EmailAccount(
                user_id=user_id,
                sender_name=sender_name.strip(),
                email=email.strip().lower(),
                smtp_host=smtp_host.strip(),
                smtp_port=smtp_port,
                smtp_username=smtp_username.strip(),
                smtp_password_encrypted=smtp_password_encrypted,
                smtp_security=smtp_security.upper(),
                is_active=True
            )
            self.db.add(account)
        else:
            account.sender_name = sender_name.strip()
            account.email = email.strip().lower()
            account.smtp_host = smtp_host.strip()
            account.smtp_port = smtp_port
            account.smtp_username = smtp_username.strip()
            if smtp_password_encrypted:  # Atualiza senha apenas se fornecida
                account.smtp_password_encrypted = smtp_password_encrypted
            account.smtp_security = smtp_security.upper()
            account.is_active = True

        self.db.commit()
        self.db.refresh(account)
        return account
