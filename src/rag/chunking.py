import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    chunk_id: str
    index: int
    text: str
    embed_text: str
    page: int | None
    section: str | None


def _page_of(chunk: Any) -> int | None:
    """Primeira página em que o chunk aparece, lida da proveniência do Docling."""
    for item in getattr(chunk.meta, "doc_items", None) or []:
        for provenance in getattr(item, "prov", None) or []:
            page_no = getattr(provenance, "page_no", None)
            if page_no is not None:
                return page_no
    return None


def _section_of(chunk: Any) -> str | None:
    headings = getattr(chunk.meta, "headings", None) or []
    return " > ".join(headings) if headings else None


def chunk_document(document: Any, file_id: uuid.UUID, chunker: Any) -> list[Chunk]:
    """O chunking é determinístico: mesma entrada, mesmos chunks na mesma ordem,
    então `chunk_id` derivado do índice é estável entre execuções (PRD §9)."""
    chunks = []
    for index, raw in enumerate(chunker.chunk(document)):
        text = raw.text.strip()
        if not text:
            continue

        chunks.append(
            Chunk(
                chunk_id=f"{file_id}:{index}",
                index=index,
                text=text,
                # O texto contextualizado carrega os títulos da seção e é o que
                # vai para o embedding; o texto puro é o que vira citação.
                embed_text=chunker.contextualize(raw),
                page=_page_of(raw),
                section=_section_of(raw),
            )
        )
    return chunks
