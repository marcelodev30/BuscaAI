import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.domain.file_state import FileStatus


class Base(DeclarativeBase):
    pass


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)

    # NULL para usuários que entram apenas com Google (login email/senha fora do MVP).
    password_hash: Mapped[str | None] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=True),
        nullable=False,
        default=UserStatus.active,
        server_default=UserStatus.active.value,
    )
    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="free", server_default="free")

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GoogleIdentity(Base):
    """Identidade externa do Google associada a um User (CLAUDE.md §11: dado de
    identidade externa, tratado separado do domínio User)."""

    __tablename__ = "google_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    google_sub: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # jti do refresh token emitido mais recentemente, usado para invalidar o
    # anterior a cada rotação (ver src/auth/jwt.py).
    current_refresh_jti: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Notebook(Base):
    __tablename__ = "notebooks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class File(Base):
    """O arquivo é a própria unidade de processamento: o estado da fila e o
    checkpoint do pipeline ficam nesta tabela, sem tabela de job separada.
    O upload preenche identidade, checksum e estado; as colunas de
    processamento só passam a ser escritas na fase de Document Processing."""

    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("notebook_id", "checksum_sha256", name="uq_files_notebook_checksum"),
        CheckConstraint(
            "stage IS NULL OR stage IN ('extracting', 'chunking', 'embedding', 'indexing')",
            name="ck_files_stage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False
    )

    # identidade
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_key: Mapped[str | None] = mapped_column(Text)  # PDF original recebido no upload
    storage_key: Mapped[str | None] = mapped_column(Text)  # JSON estruturado do Docling
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # estado
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, name="file_status", native_enum=True),
        nullable=False,
        default=FileStatus.pending,
        server_default=FileStatus.pending.value,
    )
    stage: Mapped[str | None] = mapped_column(String(30))
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))

    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    # fila
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default=text("3"))
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # checkpoint do processamento em lote
    chunks_total: Mapped[int | None] = mapped_column(Integer)
    chunks_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    batch_size: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=64, server_default=text("64"))

    # resultado
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # versões, para saber o que vale reprocessar
    parser_version: Mapped[str | None] = mapped_column(String(50))
    chunking_version: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
