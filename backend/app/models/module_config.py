from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModuleConfig(Base):
    __tablename__ = "module_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
