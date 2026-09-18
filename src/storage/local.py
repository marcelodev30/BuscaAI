import uuid
from pathlib import Path

from fastapi import Request


class LocalStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _resolve(self, key: str) -> Path:
        path = (self.base_dir / key).resolve()
        if not path.is_relative_to(self.base_dir.resolve()):
            raise ValueError(f"Chave de storage fora do diretório base: {key}")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)


def source_key_for(user_id: uuid.UUID, notebook_id: uuid.UUID, file_id: uuid.UUID) -> str:
    return f"users/{user_id}/notebooks/{notebook_id}/{file_id}.pdf"


def get_storage(request: Request) -> LocalStorage:
    return request.app.state.storage
