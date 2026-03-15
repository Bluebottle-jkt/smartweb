"""
Base repository providing generic CRUD with pagination.
All concrete repositories inherit from this.
"""
from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[ModelT]:
        return self.db.query(self.model).filter(self.model.id == id).first()  # type: ignore[attr-defined]

    def list(self, *, skip: int = 0, limit: int = 20) -> List[ModelT]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        try:
            return self.db.query(self.model).count()
        except Exception:
            return 0

    def save(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, id: int) -> bool:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.flush()
            return True
        return False
