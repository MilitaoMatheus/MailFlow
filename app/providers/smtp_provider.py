import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid, formatdate
from typing import Optional
from app.providers.base import BaseEmailProvider, EmailSendResult, ConnectionTestResult
from app.models.email_account import SmtpSecurity


class SmtpEmailProvider(BaseEmailProvider):
    """Provedor de envio de e-mail via protocolo SMTP padrão (Gmail, Outlook, servidores próprios)."""

    def __init__(
        self,
        sender_name: str,
        sender_email: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_security: str = SmtpSecurity.STARTTLS,
        timeout: int = 15
    ):
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_security = smtp_security.upper()
        self.timeout = timeout

    def _get_connection(self):
        """Estabelece a conexão SMTP apropriada de acordo com o tipo de segurança configurado."""
        if self.smtp_security == SmtpSecurity.SSL:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout)
            if self.smtp_security in (SmtpSecurity.STARTTLS, SmtpSecurity.TLS):
                server.starttls()

        if self.smtp_username and self.smtp_password:
            server.login(self.smtp_username, self.smtp_password)

        return server

    def test_connection(self) -> ConnectionTestResult:
        """Verifica a conectividade e autenticação com o servidor SMTP."""
        try:
            server = self._get_connection()
            server.quit()
            return ConnectionTestResult(
                success=True,
                message=f"Conexão com servidor SMTP ({self.smtp_host}:{self.smtp_port}) autenticada com sucesso!"
            )
        except smtplib.SMTPAuthenticationError as e:
            return ConnectionTestResult(
                success=False,
                message=f"Falha de autenticação SMTP: Usuário ou senha incorretos ({e.smtp_code})."
            )
        except (socket.gaierror, socket.timeout, smtplib.SMTPConnectError, OSError) as e:
            return ConnectionTestResult(
                success=False,
                message=f"Não foi possível conectar ao servidor SMTP {self.smtp_host}:{self.smtp_port}. Verifique host e porta. ({str(e)})"
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Erro na conexão SMTP: {str(e)}"
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
        """Cria a mensagem MIME e envia via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((self.sender_name, self.sender_email))
            msg["To"] = formataddr((to_name, to_email))
            msg["Date"] = formatdate(localtime=True)
            msg_id = make_msgid()
            msg["Message-ID"] = msg_id

            # Header para descadastro compatível com RFC 2369 / RFC 8058
            if unsubscribe_url:
                msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
                msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

            # Versão em texto puro (fallback)
            if not text_content:
                # Gerar fallback simples removendo tags básicas se necessário
                text_content = f"{subject}\n\nPara visualizar o conteúdo completo, utilize um leitor compatível com HTML."

            part_text = MIMEText(text_content, "plain", "utf-8")
            part_html = MIMEText(html_content, "html", "utf-8")

            msg.attach(part_text)
            msg.attach(part_html)

            server = self._get_connection()
            server.sendmail(self.sender_email, [to_email], msg.as_string())
            server.quit()

            return EmailSendResult(
                success=True,
                message_id=msg_id
            )
        except smtplib.SMTPRecipientsRefused as e:
            return EmailSendResult(
                success=False,
                error_message=f"Destinatário recusado pelo servidor SMTP: {str(e)}"
            )
        except smtplib.SMTPAuthenticationError:
            return EmailSendResult(
                success=False,
                error_message="Erro de autenticação SMTP. Verifique o usuário e a senha da conta."
            )
        except (socket.timeout, smtplib.SMTPConnectError, OSError) as e:
            return EmailSendResult(
                success=False,
                error_message=f"Tempo limite ou falha de conexão SMTP: {str(e)}"
            )
        except Exception as e:
            return EmailSendResult(
                success=False,
                error_message=f"Erro no envio: {str(e)}"
            )
