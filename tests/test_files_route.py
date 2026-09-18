from src.domain import quota


def _create_notebook(client, headers, name="Notebook"):
    return client.post("/v1/notebooks", json={"name": name}, headers=headers).json()


def _upload(client, headers, notebook_id, data: bytes, filename: str = "manual.pdf"):
    return client.post(
        f"/v1/notebooks/{notebook_id}/files",
        files={"upload": (filename, data, "application/pdf")},
        headers=headers,
    )


async def test_upload_pdf(client, user_factory, auth_headers, pdf_bytes, storage_dir):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], pdf_bytes(pages=3))

    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "manual.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["status"] == "pending"
    assert body["page_count"] == 3
    assert body["error_code"] is None
    # o PDF original foi gravado com prefixo por usuário
    saved = list(storage_dir.rglob("*.pdf"))
    assert len(saved) == 1
    assert f"users/{user.id}/notebooks/{notebook['id']}" in saved[0].as_posix()


async def test_upload_requires_authentication(client, user_factory, auth_headers, pdf_bytes):
    user = await user_factory()
    notebook = _create_notebook(client, auth_headers(user))

    response = client.post(
        f"/v1/notebooks/{notebook['id']}/files",
        files={"upload": ("manual.pdf", pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 401


async def test_upload_to_notebook_of_another_user_returns_not_found(
    client, user_factory, auth_headers, pdf_bytes
):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    notebook = _create_notebook(client, auth_headers(owner))

    response = _upload(client, auth_headers(other), notebook["id"], pdf_bytes())

    assert response.status_code == 404
    assert response.json()["code"] == "NOTEBOOK_NOT_FOUND"


async def test_upload_rejects_non_pdf(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], b"\x89PNG\r\n\x1a\n imagem", filename="foto.png")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


async def test_upload_rejects_empty_file(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], b"")

    assert response.status_code == 400
    assert response.json()["code"] == "FILE_EMPTY"


async def test_upload_rejects_corrupted_pdf(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], b"%PDF-1.7 corrompido")

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PDF"


async def test_upload_rejects_file_above_size_limit(client, user_factory, auth_headers, pdf_bytes, monkeypatch):
    monkeypatch.setitem(quota.MAX_FILE_BYTES_BY_PLAN, "free", 100)
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], pdf_bytes())

    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"


async def test_upload_rejects_file_above_page_limit(client, user_factory, auth_headers, pdf_bytes, monkeypatch):
    monkeypatch.setitem(quota.MAX_PAGES_PER_FILE_BY_PLAN, "free", 1)
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    response = _upload(client, headers, notebook["id"], pdf_bytes(pages=2))

    assert response.status_code == 403
    assert response.json()["code"] == "FILE_TOO_MANY_PAGES"


async def test_upload_rejects_duplicated_file_in_same_notebook(client, user_factory, auth_headers, pdf_bytes):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)
    data = pdf_bytes()

    assert _upload(client, headers, notebook["id"], data).status_code == 201
    response = _upload(client, headers, notebook["id"], data)

    assert response.status_code == 409
    assert response.json()["code"] == "FILE_DUPLICATED"


async def test_same_file_allowed_in_another_notebook(client, user_factory, auth_headers, pdf_bytes):
    user = await user_factory()
    headers = auth_headers(user)
    first = _create_notebook(client, headers, name="Primeiro")
    second = _create_notebook(client, headers, name="Segundo")
    data = pdf_bytes()

    assert _upload(client, headers, first["id"], data).status_code == 201
    assert _upload(client, headers, second["id"], data).status_code == 201


async def test_upload_rejects_when_notebook_file_limit_reached(
    client, user_factory, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setitem(quota.FILES_PER_NOTEBOOK_BY_PLAN, "free", 1)
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    assert _upload(client, headers, notebook["id"], pdf_bytes(width=595)).status_code == 201
    response = _upload(client, headers, notebook["id"], pdf_bytes(width=600))

    assert response.status_code == 403
    assert response.json()["code"] == "NOTEBOOK_FILE_LIMIT_REACHED"


async def test_upload_rejects_when_monthly_page_quota_exceeded(
    client, user_factory, auth_headers, pdf_bytes, monkeypatch
):
    monkeypatch.setitem(quota.MONTHLY_PAGES_BY_PLAN, "free", 2)
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)

    assert _upload(client, headers, notebook["id"], pdf_bytes(pages=2, width=595)).status_code == 201
    response = _upload(client, headers, notebook["id"], pdf_bytes(pages=2, width=600))

    assert response.status_code == 403
    assert response.json()["code"] == "PAGE_QUOTA_EXCEEDED"


async def test_list_files_of_notebook(client, user_factory, auth_headers, pdf_bytes):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = _create_notebook(client, headers)
    _upload(client, headers, notebook["id"], pdf_bytes(), filename="a.pdf")

    response = client.get(f"/v1/notebooks/{notebook['id']}/files", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["original_name"] == "a.pdf"


async def test_list_files_of_another_user_notebook_returns_not_found(
    client, user_factory, auth_headers, pdf_bytes
):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    notebook = _create_notebook(client, auth_headers(owner))
    _upload(client, auth_headers(owner), notebook["id"], pdf_bytes())

    response = client.get(f"/v1/notebooks/{notebook['id']}/files", headers=auth_headers(other))

    assert response.status_code == 404
    assert response.json()["code"] == "NOTEBOOK_NOT_FOUND"
