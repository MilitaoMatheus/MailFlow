from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailSendResult:
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ConnectionTestResult:
    success: bool
    message: str


class BaseEmailProvider(ABC):
    """Interface abstrata para provedores de envio de e-mail."""

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        unsubscribe_url: Optional[str] = None
    ) -> EmailSendResult:
        """Envia um e-mail individual para o destinatário."""
        pass

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Testa se as credenciais e o servidor estão respondendo corretamente."""
        pass
