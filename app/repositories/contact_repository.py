from typing import List, Optional
from sqlalchemy import or_, desc
from app.repositories.base import BaseRepository
from app.models.contact import Contact, ContactStatus, generate_unsubscribe_token


class ContactRepository(BaseRepository):

    def get_by_id(self, user_id: int, contact_id: int) -> Optional[Contact]:
        """Busca contato garantindo que pertence exclusivamente ao user_id informado."""
        return self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == user_id
        ).first()

    def get_by_email(self, user_id: int, email: str) -> Optional[Contact]:
        """Busca contato por e-mail dentro da lista do usuário."""
        return self.db.query(Contact).filter(
            Contact.user_id == user_id,
            Contact.email == email.strip().lower()
        ).first()

    def get_by_unsubscribe_token(self, token: str) -> Optional[Contact]:
        """Busca contato pelo token único de descadastro público."""
        if not token:
            return None
        return self.db.query(Contact).filter(Contact.unsubscribe_token == token.strip()).first()

    def list_contacts(
        self,
        user_id: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Contact]:
        """Lista contatos do usuário com suporte a busca, filtro por status e paginação."""
        query = self.db.query(Contact).filter(Contact.user_id == user_id)

        if status and status.upper() in (ContactStatus.ATIVO, ContactStatus.INATIVO, ContactStatus.INVALIDO, ContactStatus.DESCADASTRADO):
            query = query.filter(Contact.status == status.upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Contact.name.ilike(term),
                    Contact.email.ilike(term),
                    Contact.company.ilike(term)
                )
            )

        return query.order_by(desc(Contact.created_at)).offset(offset).limit(limit).all()

    def count_contacts(
        self,
        user_id: int,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Conta total de contatos com filtros aplicados."""
        query = self.db.query(Contact).filter(Contact.user_id == user_id)

        if status and status.upper() in (ContactStatus.ATIVO, ContactStatus.INATIVO, ContactStatus.INVALIDO, ContactStatus.DESCADASTRADO):
            query = query.filter(Contact.status == status.upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Contact.name.ilike(term),
                    Contact.email.ilike(term),
                    Contact.company.ilike(term)
                )
            )

        return query.count()

    def get_contacts_by_ids(self, user_id: int, contact_ids: List[int]) -> List[Contact]:
        """Recupera lista de contatos por IDs garantindo que todos pertençam ao user_id."""
        if not contact_ids:
            return []
        return self.db.query(Contact).filter(
            Contact.user_id == user_id,
            Contact.id.in_(contact_ids)
        ).all()

    def get_all_active_contacts(self, user_id: int) -> List[Contact]:
        """Recupera todos os contatos com status ATIVO para o perfil."""
        return self.db.query(Contact).filter(
            Contact.user_id == user_id,
            Contact.status == ContactStatus.ATIVO
        ).order_by(Contact.name.asc()).all()

    def create(
        self,
        user_id: int,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        status: str = ContactStatus.ATIVO
    ) -> Contact:
        """Cadastra um novo contato isolado para o usuário."""
        contact = Contact(
            user_id=user_id,
            name=name.strip(),
            email=email.strip().lower(),
            company=company.strip() if company else None,
            phone=phone.strip() if phone else None,
            status=status.upper(),
            unsubscribe_token=generate_unsubscribe_token()
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def update(
        self,
        user_id: int,
        contact_id: int,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[Contact]:
        """Atualiza dados do contato garantindo a propriedade."""
        contact = self.get_by_id(user_id, contact_id)
        if not contact:
            return None

        contact.name = name.strip()
        contact.email = email.strip().lower()
        contact.company = company.strip() if company else None
        contact.phone = phone.strip() if phone else None
        if status:
            contact.status = status.upper()

        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete(self, user_id: int, contact_id: int) -> bool:
        """Exclui contato garantindo que pertence ao usuário."""
        contact = self.get_by_id(user_id, contact_id)
        if not contact:
            return False
        self.db.delete(contact)
        self.db.commit()
        return True

    def toggle_status(self, user_id: int, contact_id: int) -> Optional[Contact]:
        """Alterna status entre ATIVO e INATIVO."""
        contact = self.get_by_id(user_id, contact_id)
        if not contact:
            return None
        if contact.status == ContactStatus.ATIVO:
            contact.status = ContactStatus.INATIVO
        elif contact.status == ContactStatus.INATIVO:
            contact.status = ContactStatus.ATIVO
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def unsubscribe(self, token: str) -> Optional[Contact]:
        """Altera status para DESCADASTRADO a partir do token único de descadastro."""
        contact = self.get_by_unsubscribe_token(token)
        if not contact:
            return None
        contact.status = ContactStatus.DESCADASTRADO
        self.db.commit()
        self.db.refresh(contact)
        return contact
