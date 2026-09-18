import uuid

from src.notebooks.repository import NotebookRepository
from src.users.repository import UserRepository


async def _create_user(db_session, email: str):
    return await UserRepository(db_session).create(email=email, name=email.split("@")[0])


async def test_create_and_get_by_id(db_session):
    user = await _create_user(db_session, "ana@example.com")
    repository = NotebookRepository(db_session)

    notebook = await repository.create(user_id=user.id, name="Manual da farmácia", icon="📘")

    found = await repository.get_by_id(notebook.id, user.id)
    assert found is not None
    assert found.name == "Manual da farmácia"
    assert found.icon == "📘"


async def test_get_by_id_does_not_return_notebook_of_another_user(db_session):
    owner = await _create_user(db_session, "dono@example.com")
    other = await _create_user(db_session, "outro@example.com")
    repository = NotebookRepository(db_session)
    notebook = await repository.create(user_id=owner.id, name="Privado")

    found = await repository.get_by_id(notebook.id, other.id)

    assert found is None


async def test_get_by_id_returns_none_when_not_found(db_session):
    user = await _create_user(db_session, "bruno@example.com")
    repository = NotebookRepository(db_session)

    assert await repository.get_by_id(uuid.uuid4(), user.id) is None


async def test_list_by_user_returns_only_own_notebooks(db_session):
    owner = await _create_user(db_session, "carla@example.com")
    other = await _create_user(db_session, "duda@example.com")
    repository = NotebookRepository(db_session)
    await repository.create(user_id=owner.id, name="Meu A")
    await repository.create(user_id=owner.id, name="Meu B")
    await repository.create(user_id=other.id, name="De outro")

    notebooks = await repository.list_by_user(owner.id)

    assert {notebook.name for notebook in notebooks} == {"Meu A", "Meu B"}


async def test_count_by_user(db_session):
    user = await _create_user(db_session, "elis@example.com")
    repository = NotebookRepository(db_session)

    assert await repository.count_by_user(user.id) == 0

    await repository.create(user_id=user.id, name="Primeiro")
    assert await repository.count_by_user(user.id) == 1


async def test_update_applies_changes(db_session):
    user = await _create_user(db_session, "fabio@example.com")
    repository = NotebookRepository(db_session)
    notebook = await repository.create(user_id=user.id, name="Nome antigo", icon="📕")

    await repository.update(notebook, {"name": "Nome novo"})

    assert notebook.name == "Nome novo"
    assert notebook.icon == "📕"


async def test_delete_removes_notebook(db_session):
    user = await _create_user(db_session, "giulia@example.com")
    repository = NotebookRepository(db_session)
    notebook = await repository.create(user_id=user.id, name="Descartável")

    await repository.delete(notebook)

    assert await repository.get_by_id(notebook.id, user.id) is None
