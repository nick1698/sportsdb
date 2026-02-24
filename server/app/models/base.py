from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Variable(Base):
    __tablename__ = "app_variable"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=True)
