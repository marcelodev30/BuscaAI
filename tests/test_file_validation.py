import pypdfium2.raw as pdfium_c
import pytest

from src.errors import AppError
from src.files import validation


def test_ensure_not_empty_rejects_empty_bytes():
    with pytest.raises(AppError) as exc_info:
        validation.ensure_not_empty(b"")

    assert exc_info.value.code == "FILE_EMPTY"


def test_ensure_pdf_magic_bytes_accepts_pdf(pdf_bytes):
    validation.ensure_pdf_magic_bytes(pdf_bytes())


def test_ensure_pdf_magic_bytes_rejects_other_formats():
    with pytest.raises(AppError) as exc_info:
        validation.ensure_pdf_magic_bytes(b"\x89PNG\r\n\x1a\n resto da imagem")

    assert exc_info.value.code == "INVALID_FILE_TYPE"


def test_count_pdf_pages(pdf_bytes):
    assert validation.count_pdf_pages(pdf_bytes(pages=3)) == 3


def test_count_pdf_pages_rejects_corrupted_pdf():
    with pytest.raises(AppError) as exc_info:
        validation.count_pdf_pages(b"%PDF-1.7 conteudo corrompido")

    assert exc_info.value.code == "INVALID_PDF"


def test_count_pdf_pages_rejects_password_protected(monkeypatch):
    monkeypatch.setattr(pdfium_c, "FPDF_GetLastError", lambda: pdfium_c.FPDF_ERR_PASSWORD)

    with pytest.raises(AppError) as exc_info:
        validation.count_pdf_pages(b"%PDF-1.7 protegido")

    assert exc_info.value.code == "PDF_PASSWORD_PROTECTED"


def test_compute_checksum_is_stable():
    assert validation.compute_checksum(b"abc") == validation.compute_checksum(b"abc")
    assert validation.compute_checksum(b"abc") != validation.compute_checksum(b"abd")
    assert len(validation.compute_checksum(b"abc")) == 64


def test_normalize_original_name_strips_path():
    assert validation.normalize_original_name("../../etc/manual.pdf") == "manual.pdf"


def test_normalize_original_name_rejects_empty():
    with pytest.raises(AppError) as exc_info:
        validation.normalize_original_name("   ")

    assert exc_info.value.code == "INVALID_FILE_NAME"


def test_normalize_original_name_truncates():
    name = validation.normalize_original_name("a" * 600 + ".pdf")

    assert len(name) == validation.MAX_ORIGINAL_NAME_LENGTH
