import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models.template import Template
from app.models.contact import Contact
from app.models.user import User
from app.repositories.template_repository import TemplateRepository
from app.repositories.log_repository import LogRepository
from app.config import settings


class TemplateService:
    """Serviço de gerenciamento e renderização de templates modulares particionados (Header, Body, Footer)."""

    def __init__(self, db: Session):
        self.db = db
        self.template_repo = TemplateRepository(db)
        self.log_repo = LogRepository(db)

    def list_templates(self, user_id: int) -> List[Template]:
        return self.template_repo.list_templates(user_id)

    def get_template(self, user_id: int, template_id: int) -> Optional[Template]:
        return self.template_repo.get_by_id(user_id, template_id)

    def create_template(
        self,
        user_id: int,
        name: str,
        header: str,
        body: str,
        footer: str
    ) -> Tuple[bool, str, Optional[Template]]:
        name_clean = name.strip() if name else ""
        if not name_clean:
            return False, "O nome do template é obrigatório.", None

        if not body or not body.strip():
            return False, "O corpo (Body) da mensagem não pode ficar vazio.", None

        template = self.template_repo.create(
            user_id=user_id,
            name=name_clean,
            header=header or "",
            body=body or "",
            footer=footer or ""
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="TEMPLATE_CRIADO",
            description=f"Template '{template.name}' criado com sucesso."
        )

        return True, "Template criado com sucesso!", template

    def update_template(
        self,
        user_id: int,
        template_id: int,
        name: str,
        header: str,
        body: str,
        footer: str
    ) -> Tuple[bool, str, Optional[Template]]:
        template = self.template_repo.get_by_id(user_id, template_id)
        if not template:
            return False, "Template não encontrado.", None

        name_clean = name.strip() if name else ""
        if not name_clean:
            return False, "O nome do template é obrigatório.", None

        if not body or not body.strip():
            return False, "O corpo (Body) da mensagem não pode ficar vazio.", None

        updated = self.template_repo.update(
            user_id=user_id,
            template_id=template_id,
            name=name_clean,
            header=header or "",
            body=body or "",
            footer=footer or ""
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="TEMPLATE_ATUALIZADO",
            description=f"Template '{updated.name}' atualizado."
        )

        return True, "Template atualizado com sucesso!", updated

    def delete_template(self, user_id: int, template_id: int) -> Tuple[bool, str]:
        template = self.template_repo.get_by_id(user_id, template_id)
        if not template:
            return False, "Template não encontrado."

        name_saved = template.name
        self.template_repo.delete(user_id, template_id)

        self.log_repo.create_log(
            user_id=user_id,
            action="TEMPLATE_REMOVIDO",
            description=f"Template '{name_saved}' excluído."
        )

        return True, "Template excluído com sucesso!"

    @staticmethod
    def render_content(
        header: str,
        body: str,
        footer: str,
        contact_name: str,
        contact_email: str,
        company: Optional[str] = None,
        profile_name: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        extra_vars: Optional[Dict[str, str]] = None
    ) -> str:
        """Substitui variáveis dinâmicas e empacota Header, Body e Footer em documento HTML compatível com clientes de e-mail."""
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        
        # Variáveis disponíveis para substituição
        variables = {
            "nome": contact_name or "Cliente",
            "email": contact_email or "",
            "empresa": company or "",
            "data": now_str,
            "nome_perfil": profile_name or "",
            "link_descadastro": unsubscribe_url or "#"
        }
        if extra_vars:
            variables.update(extra_vars)

        def replace_vars(text: str) -> str:
            if not text:
                return ""
            res = text
            for key, val in variables.items():
                # Suporta {{nome}} e {{ nome }} com espaços opcionais
                pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", re.IGNORECASE)
                res = pattern.sub(str(val), res)
            return res

        rendered_header = replace_vars(header)
        rendered_body = replace_vars(body)
        rendered_footer = replace_vars(footer)

        # Se o footer não tiver link de descadastro explícito, injetamos aviso e link padrão
        if unsubscribe_url and "link_descadastro" not in (footer or "").lower() and "descadastro" not in (footer or "").lower():
            rendered_footer += (
                f'<div style="margin-top: 20px; font-size: 11px; color: #888888; text-align: center;">'
                f'Não deseja mais receber estes e-mails? '
                f'<a href="{unsubscribe_url}" style="color: #6366f1; text-decoration: underline;">Clique aqui para cancelar sua inscrição</a>.'
                f'</div>'
            )

        html_document = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-mail</title>
    <style>
        body {{ margin: 0; padding: 0; background-color: #f4f6f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #333333; }}
        .email-container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .email-header {{ background-color: #1e293b; color: #ffffff; padding: 24px; text-align: center; }}
        .email-body {{ padding: 32px 24px; line-height: 1.6; font-size: 15px; }}
        .email-footer {{ background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 24px; font-size: 12px; color: #64748b; text-align: center; }}
        a {{ color: #4f46e5; text-decoration: none; }}
        .btn {{ display: inline-block; padding: 12px 24px; background-color: #4f46e5; color: #ffffff !important; border-radius: 6px; font-weight: bold; text-decoration: none; margin: 16px 0; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <div class="email-container">
        <!-- HEADER -->
        {f'<div class="email-header">{rendered_header}</div>' if rendered_header.strip() else ''}
        
        <!-- BODY -->
        <div class="email-body">
            {rendered_body}
        </div>
        
        <!-- FOOTER -->
        {f'<div class="email-footer">{rendered_footer}</div>' if rendered_footer.strip() else ''}
    </div>
</body>
</html>"""
        return html_document

    def preview_template(
        self,
        template: Template,
        user: User,
        sample_name: str = "João da Silva",
        sample_email: str = "joao.silva@exemplo.com",
        sample_company: str = "Empresa Exemplo Ltda",
        base_url: str = settings.APP_BASE_URL
    ) -> str:
        """Gera preview formatado do template com dados fictícios."""
        unsubscribe_url = f"{base_url}/unsubscribe?token=preview-token-exemplo"
        return self.render_content(
            header=template.header,
            body=template.body,
            footer=template.footer,
            contact_name=sample_name,
            contact_email=sample_email,
            company=sample_company,
            profile_name=user.name,
            unsubscribe_url=unsubscribe_url
        )
