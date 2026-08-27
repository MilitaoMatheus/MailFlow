import uuid
from typing import List, Dict, Any, Optional
from app.providers.base import BaseEmailProvider, EmailSendResult, ConnectionTestResult


class MockEmailProvider(BaseEmailProvider):
    """Provedor simulado para testes automatizados e desenvolvimento local offline."""

    def __init__(
        self,
        sender_name: str = "Mock Sender",
        sender_email: str = "mock@example.com",
        fail_domains: Optional[List[str]] = None,
        should_fail_connection: bool = False
    ):
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.fail_domains = fail_domains or ["fail.com", "error.org", "rejeitado.net"]
        self.should_fail_connection = should_fail_connection
        self.sent_emails: List[Dict[str, Any]] = []

    def test_connection(self) -> ConnectionTestResult:
        if self.should_fail_connection:
            return ConnectionTestResult(
                success=False,
                message="Falha simulada de conexão com servidor Mock SMTP."
            )
        return ConnectionTestResult(
            success=True,
            message="Conexão com servidor Mock SMTP bem-sucedida!"
        )

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        unsubscribe_url: Optional[str] = None
    ) -> EmailSendResult:
        domain = to_email.split("@")[-1].lower() if "@" in to_email else ""

        # Simular falha se pertencer aos domínios de teste de erro
        if domain in self.fail_domains or "erro" in to_email.lower() or "fail" in to_email.lower():
            return EmailSendResult(
                success=False,
                error_message=f"Falha de entrega simulada: domínio '{domain}' rejeitou a mensagem."
            )

        msg_id = f"<{uuid.uuid4()}@mock.local>"
        record = {
            "to_email": to_email,
            "to_name": to_name,
            "from_email": self.sender_email,
            "from_name": self.sender_name,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "unsubscribe_url": unsubscribe_url,
            "message_id": msg_id
        }
        self.sent_emails.append(record)

        return EmailSendResult(
            success=True,
            message_id=msg_id
        )

    def clear(self):
        self.sent_emails.clear()
