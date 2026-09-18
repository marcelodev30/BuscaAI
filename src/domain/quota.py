from fastapi import status

from src.errors import AppError

FALLBACK_PLAN = "free"

# Limites e quotas por plano (PRD §15).
NOTEBOOK_LIMIT_BY_PLAN = {"free": 3, "pro": 20}
FILES_PER_NOTEBOOK_BY_PLAN = {"free": 10, "pro": 100}
MAX_FILE_BYTES_BY_PLAN = {"free": 20 * 1024 * 1024, "pro": 50 * 1024 * 1024}
MAX_PAGES_PER_FILE_BY_PLAN = {"free": 200, "pro": 1000}
MONTHLY_PAGES_BY_PLAN = {"free": 300, "pro": 5000}


def _for_plan(limits: dict[str, int], plan: str) -> int:
    return limits.get(plan, limits[FALLBACK_PLAN])


def notebook_limit(plan: str) -> int:
    return _for_plan(NOTEBOOK_LIMIT_BY_PLAN, plan)


def files_per_notebook_limit(plan: str) -> int:
    return _for_plan(FILES_PER_NOTEBOOK_BY_PLAN, plan)


def max_file_bytes(plan: str) -> int:
    return _for_plan(MAX_FILE_BYTES_BY_PLAN, plan)


def max_pages_per_file(plan: str) -> int:
    return _for_plan(MAX_PAGES_PER_FILE_BY_PLAN, plan)


def monthly_pages_quota(plan: str) -> int:
    return _for_plan(MONTHLY_PAGES_BY_PLAN, plan)


def ensure_can_create_notebook(plan: str, current_count: int) -> None:
    if current_count >= notebook_limit(plan):
        raise AppError(
            "NOTEBOOK_LIMIT_REACHED",
            "Você atingiu o limite de notebooks do seu plano.",
            status.HTTP_403_FORBIDDEN,
        )


def ensure_can_add_file_to_notebook(plan: str, current_count: int) -> None:
    if current_count >= files_per_notebook_limit(plan):
        raise AppError(
            "NOTEBOOK_FILE_LIMIT_REACHED",
            "Você atingiu o limite de arquivos deste notebook.",
            status.HTTP_403_FORBIDDEN,
        )


def ensure_file_size_allowed(plan: str, size_bytes: int) -> None:
    if size_bytes > max_file_bytes(plan):
        raise AppError(
            "FILE_TOO_LARGE",
            "O arquivo excede o tamanho máximo permitido.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


def ensure_page_count_allowed(plan: str, page_count: int) -> None:
    if page_count > max_pages_per_file(plan):
        raise AppError(
            "FILE_TOO_MANY_PAGES",
            "O arquivo excede o número máximo de páginas permitido.",
            status.HTTP_403_FORBIDDEN,
        )


def ensure_monthly_page_quota(plan: str, pages_used: int, pages_requested: int) -> None:
    if pages_used + pages_requested > monthly_pages_quota(plan):
        raise AppError(
            "PAGE_QUOTA_EXCEEDED",
            "Você atingiu a quota de páginas do seu plano neste mês.",
            status.HTTP_403_FORBIDDEN,
        )
