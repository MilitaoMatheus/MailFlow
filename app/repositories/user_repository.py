from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.user import User, UserStatus


class UserRepository(BaseRepository):

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(self, name: str, email: str, password_hash: str) -> User:
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            status=UserStatus.ATIVO
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.password_hash = new_password_hash
        self.db.commit()
        return True

    def update_profile(self, user_id: int, name: str, email: str) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.name = name.strip()
        user.email = email.strip().lower()
        self.db.commit()
        self.db.refresh(user)
        return user
