import pytest

from src.domain.quota import ensure_can_create_notebook, notebook_limit
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
