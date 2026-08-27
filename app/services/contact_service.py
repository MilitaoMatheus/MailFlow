import csv
import io
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models.contact import Contact, ContactStatus
from app.repositories.contact_repository import ContactRepository
from app.repositories.log_repository import LogRepository
from app.services.security_service import SecurityService


class ContactService:
    """Serviço de gerenciamento de contatos, importação/exportação CSV e descadastro."""

    def __init__(self, db: Session):
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.log_repo = LogRepository(db)

    def list_contacts(
        self,
        user_id: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> Dict[str, Any]:
        """Retorna contatos paginados com contagem total."""
        page = max(1, page)
        offset = (page - 1) * page_size
        
        contacts = self.contact_repo.list_contacts(
            user_id=user_id,
            search=search,
            status=status,
            limit=page_size,
            offset=offset
        )
        total_count = self.contact_repo.count_contacts(
            user_id=user_id,
            search=search,
            status=status
        )
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return {
            "contacts": contacts,
            "total_count": total_count,
            "current_page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    def get_contact(self, user_id: int, contact_id: int) -> Optional[Contact]:
        return self.contact_repo.get_by_id(user_id, contact_id)

    def create_contact(
        self,
        user_id: int,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Contact]]:
        """Cadastra um novo contato com validação sintática e de duplicidade."""
        name_clean = name.strip() if name else ""
        if not name_clean:
            return False, "O nome do contato é obrigatório.", None

        is_valid_email, clean_email_or_err = SecurityService.validate_email_syntax(email)
        if not is_valid_email:
            # Se for inválido, podemos rejeitar ou marcar com status INVALIDO
            return False, f"E-mail inválido: {clean_email_or_err}", None

        clean_email = clean_email_or_err

        # Verificar duplicidade para este perfil
        existing = self.contact_repo.get_by_email(user_id, clean_email)
        if existing:
            return False, f"O contato com e-mail '{clean_email}' já está cadastrado na sua lista.", None

        final_status = status.upper() if status and status.upper() in (
            ContactStatus.ATIVO, ContactStatus.INATIVO, ContactStatus.INVALIDO, ContactStatus.DESCADASTRADO
        ) else ContactStatus.ATIVO

        contact = self.contact_repo.create(
            user_id=user_id,
            name=name_clean,
            email=clean_email,
            company=company,
            phone=phone,
            status=final_status
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="CONTATO_CRIADO",
            description=f"Contato '{contact.name}' ({contact.email}) cadastrado com sucesso."
        )

        return True, "Contato cadastrado com sucesso!", contact

    def update_contact(
        self,
        user_id: int,
        contact_id: int,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Contact]]:
        """Atualiza contato existente."""
        contact = self.contact_repo.get_by_id(user_id, contact_id)
        if not contact:
            return False, "Contato não encontrado.", None

        name_clean = name.strip() if name else ""
        if not name_clean:
            return False, "O nome do contato é obrigatório.", None

        is_valid_email, clean_email_or_err = SecurityService.validate_email_syntax(email)
        if not is_valid_email:
            return False, f"E-mail inválido: {clean_email_or_err}", None

        clean_email = clean_email_or_err

        # Checar se outro contato deste usuário já possui esse e-mail
        existing = self.contact_repo.get_by_email(user_id, clean_email)
        if existing and existing.id != contact_id:
            return False, f"Já existe outro contato com o e-mail '{clean_email}'.", None

        final_status = status.upper() if status and status.upper() in (
            ContactStatus.ATIVO, ContactStatus.INATIVO, ContactStatus.INVALIDO, ContactStatus.DESCADASTRADO
        ) else contact.status

        updated = self.contact_repo.update(
            user_id=user_id,
            contact_id=contact_id,
            name=name_clean,
            email=clean_email,
            company=company,
            phone=phone,
            status=final_status
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="CONTATO_ATUALIZADO",
            description=f"Contato '{updated.name}' ({updated.email}) atualizado."
        )

        return True, "Contato atualizado com sucesso!", updated

    def delete_contact(self, user_id: int, contact_id: int) -> Tuple[bool, str]:
        """Remove contato da base do usuário."""
        contact = self.contact_repo.get_by_id(user_id, contact_id)
        if not contact:
            return False, "Contato não encontrado."

        email_saved = contact.email
        self.contact_repo.delete(user_id, contact_id)

        self.log_repo.create_log(
            user_id=user_id,
            action="CONTATO_REMOVIDO",
            description=f"Contato '{contact.name}' ({email_saved}) removido."
        )

        return True, "Contato excluído com sucesso!"

    def toggle_status(self, user_id: int, contact_id: int) -> Tuple[bool, str, Optional[Contact]]:
        """Alterna status entre ATIVO e INATIVO."""
        contact = self.contact_repo.toggle_status(user_id, contact_id)
        if not contact:
            return False, "Contato não encontrado.", None
        return True, f"Status do contato alterado para {contact.status}.", contact

    def import_csv(self, user_id: int, csv_text: str) -> Dict[str, Any]:
        """Importa contatos a partir de arquivo CSV com detecção de delimitador e validação de linhas."""
        result = {
            "total_rows": 0,
            "imported": 0,
            "duplicates": 0,
            "invalid": 0,
            "errors": []
        }

        if not csv_text or not csv_text.strip():
            result["errors"].append("O arquivo CSV está vazio.")
            return result

        # Detecção de dialeto / delimitador (, ou ; ou tab)
        first_line = csv_text.strip().split("\n")[0]
        delimiter = ";" if ";" in first_line and first_line.count(";") > first_line.count(",") else ","
        if "\t" in first_line and first_line.count("\t") > first_line.count(delimiter):
            delimiter = "\t"

        reader = csv.DictReader(io.StringIO(csv_text.strip()), delimiter=delimiter)
        if not reader.fieldnames:
            result["errors"].append("Cabeçalhos do CSV não encontrados.")
            return result

        # Mapeamento flexível de colunas
        field_map = {}
        for fn in reader.fieldnames:
            clean_fn = fn.strip().lower()
            if clean_fn in ("nome", "name", "contato", "destinatario"):
                field_map["name"] = fn
            elif clean_fn in ("email", "e-mail", "correio"):
                field_map["email"] = fn
            elif clean_fn in ("empresa", "company", "organizacao", "organization"):
                field_map["company"] = fn
            elif clean_fn in ("telefone", "phone", "celular", "tel"):
                field_map["phone"] = fn

        if "email" not in field_map:
            result["errors"].append("Coluna de e-mail ('email' ou 'e-mail') não encontrada no cabeçalho do CSV.")
            return result

        row_num = 1
        for row in reader:
            row_num += 1
            result["total_rows"] += 1

            raw_email = row.get(field_map["email"], "").strip()
            raw_name = row.get(field_map.get("name", ""), "").strip() if "name" in field_map else ""
            if not raw_name:
                raw_name = raw_email.split("@")[0] if "@" in raw_email else "Contato"

            raw_company = row.get(field_map.get("company", ""), "").strip() if "company" in field_map else None
            raw_phone = row.get(field_map.get("phone", ""), "").strip() if "phone" in field_map else None

            # Validar e-mail
            is_valid, clean_email = SecurityService.validate_email_syntax(raw_email)
            if not is_valid:
                result["invalid"] += 1
                result["errors"].append(f"Linha {row_num}: E-mail '{raw_email}' inválido.")
                continue

            # Verificar duplicidade
            existing = self.contact_repo.get_by_email(user_id, clean_email)
            if existing:
                result["duplicates"] += 1
                continue

            # Inserir contato ativo
            self.contact_repo.create(
                user_id=user_id,
                name=raw_name,
                email=clean_email,
                company=raw_company,
                phone=raw_phone,
                status=ContactStatus.ATIVO
            )
            result["imported"] += 1

        self.log_repo.create_log(
            user_id=user_id,
            action="CSV_IMPORT",
            description=f"Importação CSV: {result['imported']} importados, {result['duplicates']} duplicados, {result['invalid']} inválidos."
        )

        return result

    def export_csv(self, user_id: int) -> str:
        """Gera conteúdo CSV formatado com todos os contatos do usuário."""
        contacts = self.contact_repo.list_contacts(user_id=user_id, limit=10000)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")

        writer.writerow(["ID", "Nome", "E-mail", "Empresa", "Telefone", "Status", "Data Cadastro"])
        for c in contacts:
            created_str = c.created_at.strftime("%d/%m/%Y %H:%M") if c.created_at else ""
            writer.writerow([c.id, c.name, c.email, c.company or "", c.phone or "", c.status, created_str])

        return output.getvalue()

    def unsubscribe_by_token(self, token: str) -> Tuple[bool, str, Optional[Contact]]:
        """Processa solicitação de descadastro através do token público seguro."""
        contact = self.contact_repo.unsubscribe(token)
        if not contact:
            return False, "Token de descadastro inválido ou inexistente.", None

        self.log_repo.create_log(
            user_id=contact.user_id,
            action="DESCADASTRADO",
            description=f"Contato '{contact.name}' ({contact.email}) solicitou descadastro (opt-out)."
        )

        return True, f"O e-mail '{contact.email}' foi descadastrado com sucesso.", contact
