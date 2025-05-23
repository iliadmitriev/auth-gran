from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> User | None:
        logger.debug("Fetching user", user_id=user_id)
        return self.db.get(User, user_id)

    def get_user_by_email(self, email: str) -> User | None:
        logger.debug("Fetching user by email", email=email)
        return self.db.query(User).filter(User.email == email).first()

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user: UserCreate) -> User:
        logger.info("Creating new user", email=user.email)
        hashed_password = get_password_hash(user.password)
        db_user = User(email=user.email, hashed_password=hashed_password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        logger.info("User created successfully", user_id=db_user.id)
        return db_user

    def update_user(self, user_id: int, user: UserUpdate) -> User | None:
        db_user = self.get_user(user_id)
        if not db_user:
            return None

        if user.email:
            db_user.email = user.email
        if user.password:
            db_user.hashed_password = get_password_hash(user.password).decode("utf-8")
        if user.is_active is not None:
            db_user.is_active = user.is_active
        if user.is_admin is not None:
            db_user.is_admin = user.is_admin

        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def delete_user(self, user_id: int) -> User | None:
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        self.db.delete(db_user)
        self.db.commit()
        return db_user
