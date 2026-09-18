import enum


class FileStatus(str, enum.Enum):
    """Ciclo de vida do arquivo (PRD §9, CLAUDE.md §15). As transições são
    responsabilidade do pipeline de processamento; o upload sempre cria em
    `pending`."""

    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    empty = "empty"
    deleting = "deleting"
