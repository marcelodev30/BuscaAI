from fastapi import status

from src.errors import AppError

# Limite de notebooks por plano (PRD §15).
NOTEBOOK_LIMIT_BY_PLAN = {
    "free": 3,
    "pro": 20,
}

FALLBACK_PLAN = "free"


def notebook_limit(plan: str) -> int:
    return NOTEBOOK_LIMIT_BY_PLAN.get(plan, NOTEBOOK_LIMIT_BY_PLAN[FALLBACK_PLAN])


def ensure_can_create_notebook(plan: str, current_count: int) -> None:
    if current_count >= notebook_limit(plan):
        raise AppError(
            "NOTEBOOK_LIMIT_REACHED",
            "Você atingiu o limite de notebooks do seu plano.",
            status.HTTP_403_FORBIDDEN,
        )
