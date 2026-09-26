from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any


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

    def get_session(self) -> Optional[Any]:
        """Retorna uma sessão ou conexão SMTP ativa para ser reutilizada em lote."""
        return None

    def close_session(self, session: Any) -> None:
        """Encerra a sessão ou conexão ativa se aplicável."""
        pass

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        attachments: Optional[list] = None,
        active_connection: Optional[Any] = None
    ) -> EmailSendResult:
        """Envia um e-mail individual para o destinatário."""
        pass

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Testa se as credenciais e o servidor estão respondendo corretamente."""
        pass
