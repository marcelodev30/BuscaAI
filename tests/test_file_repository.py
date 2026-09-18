import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.file_state import FileStatus
from src.files.repository import FileRepository
from src.notebooks.repository import NotebookRepository
from src.users.repository import UserRepository


async def _user_with_notebook(db_session, email: str):
    user = await UserRepository(db_session).create(email=email, name=email.split("@")[0])
    notebook = await NotebookRepository(db_session).create(user_id=user.id, name="Notebook")
    return user, notebook


async def _create_file(repository, user, notebook, *, checksum: str, pages: int = 1):
    file_id = uuid.uuid4()
    return await repository.create(
        file_id=file_id,
        user_id=user.id,
        notebook_id=notebook.id,
        original_name="manual.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        checksum_sha256=checksum,
        page_count=pages,
        source_key=f"users/{user.id}/notebooks/{notebook.id}/{file_id}.pdf",
    )


async def test_create_starts_as_pending(db_session):
    user, notebook = await _user_with_notebook(db_session, "ana@example.com")
    repository = FileRepository(db_session)

    file = await _create_file(repository, user, notebook, checksum="a" * 64, pages=7)

    assert file.status == FileStatus.pending
    assert file.page_count == 7
    assert file.chunk_count == 0
    assert file.attempt == 0
    assert file.max_attempts == 3
    assert file.source_key.startswith(f"users/{user.id}/")


async def test_same_checksum_twice_in_notebook_violates_constraint(db_session):
    user, notebook = await _user_with_notebook(db_session, "bruno@example.com")
    repository = FileRepository(db_session)
    await _create_file(repository, user, notebook, checksum="b" * 64)

    with pytest.raises(IntegrityError):
        await _create_file(repository, user, notebook, checksum="b" * 64)


async def test_same_checksum_allowed_in_another_notebook(db_session):
    user, notebook = await _user_with_notebook(db_session, "carla@example.com")
    other_notebook = await NotebookRepository(db_session).create(user_id=user.id, name="Outro")
    repository = FileRepository(db_session)
    await _create_file(repository, user, notebook, checksum="c" * 64)

    file = await _create_file(repository, user, other_notebook, checksum="c" * 64)

    assert file.id is not None


async def test_list_by_notebook_is_scoped_to_owner(db_session):
    owner, notebook = await _user_with_notebook(db_session, "dono@example.com")
    other = await UserRepository(db_session).create(email="outro@example.com", name="Outro")
    repository = FileRepository(db_session)
    await _create_file(repository, owner, notebook, checksum="d" * 64)

    assert len(await repository.list_by_notebook(notebook.id, owner.id)) == 1
    assert await repository.list_by_notebook(notebook.id, other.id) == []


async def test_count_by_notebook(db_session):
    user, notebook = await _user_with_notebook(db_session, "elis@example.com")
    repository = FileRepository(db_session)

    assert await repository.count_by_notebook(notebook.id, user.id) == 0

    await _create_file(repository, user, notebook, checksum="e" * 64)
    assert await repository.count_by_notebook(notebook.id, user.id) == 1


async def test_sum_pages_since_counts_only_period_and_user(db_session):
    user, notebook = await _user_with_notebook(db_session, "fabio@example.com")
    other, other_notebook = await _user_with_notebook(db_session, "giulia@example.com")
    repository = FileRepository(db_session)
    await _create_file(repository, user, notebook, checksum="f" * 64, pages=10)
    await _create_file(repository, other, other_notebook, checksum="g" * 64, pages=99)

    since = datetime.now(timezone.utc) - timedelta(days=1)
    assert await repository.sum_pages_since(user.id, since) == 10

    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert await repository.sum_pages_since(user.id, future) == 0
