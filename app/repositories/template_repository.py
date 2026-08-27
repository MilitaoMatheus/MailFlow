from typing import List, Optional
from sqlalchemy import desc
from app.repositories.base import BaseRepository
from app.models.template import Template


class TemplateRepository(BaseRepository):

    def get_by_id(self, user_id: int, template_id: int) -> Optional[Template]:
        """Recupera template garantindo que pertence exclusivamente ao usuário informado."""
        return self.db.query(Template).filter(
            Template.id == template_id,
            Template.user_id == user_id
        ).first()

    def list_templates(self, user_id: int) -> List[Template]:
        """Lista todos os templates do usuário."""
        return self.db.query(Template).filter(
            Template.user_id == user_id
        ).order_by(desc(Template.created_at)).all()

    def create(
        self,
        user_id: int,
        name: str,
        header: str,
        body: str,
        footer: str
    ) -> Template:
        """Cria um novo template particionado (Header, Body, Footer) para o usuário."""
        template = Template(
            user_id=user_id,
            name=name.strip(),
            header=header.strip() if header else "",
            body=body.strip() if body else "",
            footer=footer.strip() if footer else ""
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def update(
        self,
        user_id: int,
        template_id: int,
        name: str,
        header: str,
        body: str,
        footer: str
    ) -> Optional[Template]:
        """Atualiza template garantindo que pertence ao usuário."""
        template = self.get_by_id(user_id, template_id)
        if not template:
            return None

        template.name = name.strip()
        template.header = header.strip() if header else ""
        template.body = body.strip() if body else ""
        template.footer = footer.strip() if footer else ""

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, user_id: int, template_id: int) -> bool:
        """Exclui template garantindo propriedade."""
        template = self.get_by_id(user_id, template_id)
        if not template:
            return False
        self.db.delete(template)
        self.db.commit()
        return True
