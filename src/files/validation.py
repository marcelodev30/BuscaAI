import hashlib
import io
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from fastapi import status

from src.errors import AppError

PDF_MAGIC_BYTES = b"%PDF-"
PDF_MIME_TYPE = "application/pdf"
MAX_ORIGINAL_NAME_LENGTH = 500


def ensure_not_empty(data: bytes) -> None:
    if not data:
        raise AppError("FILE_EMPTY", "O arquivo está vazio.", status.HTTP_400_BAD_REQUEST)


def ensure_pdf_magic_bytes(data: bytes) -> None:
    if not data.startswith(PDF_MAGIC_BYTES):
        raise AppError("INVALID_FILE_TYPE", "Apenas arquivos PDF são aceitos.", status.HTTP_400_BAD_REQUEST)


def count_pdf_pages(data: bytes) -> int:
    """Abre o PDF e devolve o número de páginas, rejeitando arquivo corrompido
    ou protegido por senha."""
    try:
        document = pdfium.PdfDocument(io.BytesIO(data))
    except pdfium.PdfiumError as exc:
        if pdfium_c.FPDF_GetLastError() == pdfium_c.FPDF_ERR_PASSWORD:
            raise AppError(
                "PDF_PASSWORD_PROTECTED",
                "O PDF está protegido por senha.",
                status.HTTP_400_BAD_REQUEST,
            ) from exc
        raise AppError("INVALID_PDF", "Não foi possível ler o PDF.", status.HTTP_400_BAD_REQUEST) from exc

    try:
        return len(document)
    finally:
        document.close()


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_original_name(filename: str | None) -> str:
    """O nome vem do cliente: trata como dado, nunca como caminho."""
    name = Path(filename or "").name.strip()
    if not name:
        raise AppError("INVALID_FILE_NAME", "Nome de arquivo inválido.", status.HTTP_400_BAD_REQUEST)
    return name[:MAX_ORIGINAL_NAME_LENGTH]
