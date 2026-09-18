import pytest

from src.domain.quota import (
    ensure_can_add_file_to_notebook,
    ensure_can_create_notebook,
    ensure_file_size_allowed,
    ensure_monthly_page_quota,
    ensure_page_count_allowed,
    max_file_bytes,
    notebook_limit,
)
from src.errors import AppError


def test_notebook_limit_by_plan():
    assert notebook_limit("free") == 3
    assert notebook_limit("pro") == 20


def test_notebook_limit_falls_back_to_free_for_unknown_plan():
    assert notebook_limit("plano-inexistente") == notebook_limit("free")


def test_ensure_can_create_notebook_allows_below_limit():
    ensure_can_create_notebook("free", current_count=2)


def test_ensure_can_create_notebook_rejects_at_limit():
    with pytest.raises(AppError) as exc_info:
        ensure_can_create_notebook("free", current_count=3)

    assert exc_info.value.code == "NOTEBOOK_LIMIT_REACHED"
    assert exc_info.value.status_code == 403


def test_ensure_can_create_notebook_uses_plan_limit():
    ensure_can_create_notebook("pro", current_count=19)

    with pytest.raises(AppError):
        ensure_can_create_notebook("pro", current_count=20)


def test_ensure_can_add_file_to_notebook():
    ensure_can_add_file_to_notebook("free", current_count=9)

    with pytest.raises(AppError) as exc_info:
        ensure_can_add_file_to_notebook("free", current_count=10)

    assert exc_info.value.code == "NOTEBOOK_FILE_LIMIT_REACHED"


def test_ensure_file_size_allowed():
    ensure_file_size_allowed("free", max_file_bytes("free"))

    with pytest.raises(AppError) as exc_info:
        ensure_file_size_allowed("free", max_file_bytes("free") + 1)

    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert exc_info.value.status_code == 413


def test_free_and_pro_file_sizes_follow_prd():
    assert max_file_bytes("free") == 20 * 1024 * 1024
    assert max_file_bytes("pro") == 50 * 1024 * 1024


def test_ensure_page_count_allowed():
    ensure_page_count_allowed("free", 200)

    with pytest.raises(AppError) as exc_info:
        ensure_page_count_allowed("free", 201)

    assert exc_info.value.code == "FILE_TOO_MANY_PAGES"


def test_ensure_monthly_page_quota():
    ensure_monthly_page_quota("free", pages_used=290, pages_requested=10)

    with pytest.raises(AppError) as exc_info:
        ensure_monthly_page_quota("free", pages_used=290, pages_requested=11)

    assert exc_info.value.code == "PAGE_QUOTA_EXCEEDED"
