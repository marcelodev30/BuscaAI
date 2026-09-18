async def test_create_notebook(client, user_factory, auth_headers):
    user = await user_factory()

    response = client.post(
        "/v1/notebooks", json={"name": "Manual da escola", "icon": "📗"}, headers=auth_headers(user)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Manual da escola"
    assert body["icon"] == "📗"
    assert body["id"]


async def test_create_notebook_without_icon(client, user_factory, auth_headers):
    user = await user_factory()

    response = client.post("/v1/notebooks", json={"name": "Sem ícone"}, headers=auth_headers(user))

    assert response.status_code == 201
    assert response.json()["icon"] is None


def test_create_notebook_requires_authentication(client):
    response = client.post("/v1/notebooks", json={"name": "Qualquer"})

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


async def test_create_notebook_rejects_blank_name(client, user_factory, auth_headers):
    user = await user_factory()

    response = client.post("/v1/notebooks", json={"name": "   "}, headers=auth_headers(user))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_create_notebook_rejects_when_plan_limit_reached(client, user_factory, auth_headers):
    user = await user_factory(plan="free")
    headers = auth_headers(user)
    for index in range(3):
        assert client.post("/v1/notebooks", json={"name": f"Notebook {index}"}, headers=headers).status_code == 201

    response = client.post("/v1/notebooks", json={"name": "Quarto"}, headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "NOTEBOOK_LIMIT_REACHED"


async def test_list_notebooks_returns_only_own(client, user_factory, auth_headers):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    client.post("/v1/notebooks", json={"name": "Do dono"}, headers=auth_headers(owner))
    client.post("/v1/notebooks", json={"name": "Do outro"}, headers=auth_headers(other))

    response = client.get("/v1/notebooks", headers=auth_headers(owner))

    assert response.status_code == 200
    assert [notebook["name"] for notebook in response.json()] == ["Do dono"]


async def test_get_notebook_of_another_user_returns_not_found(client, user_factory, auth_headers):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    created = client.post("/v1/notebooks", json={"name": "Privado"}, headers=auth_headers(owner)).json()

    response = client.get(f"/v1/notebooks/{created['id']}", headers=auth_headers(other))

    assert response.status_code == 404
    assert response.json()["code"] == "NOTEBOOK_NOT_FOUND"


async def test_get_own_notebook(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Meu"}, headers=headers).json()

    response = client.get(f"/v1/notebooks/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_rename_notebook(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Antigo", "icon": "📘"}, headers=headers).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={"name": "Novo"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Novo"
    assert body["icon"] == "📘"


async def test_change_notebook_icon(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Meu", "icon": "📘"}, headers=headers).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={"icon": "📙"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["icon"] == "📙"
    assert body["name"] == "Meu"


async def test_update_notebook_rejects_null_name(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Original"}, headers=headers).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={"name": None}, headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert client.get(f"/v1/notebooks/{created['id']}", headers=headers).json()["name"] == "Original"


async def test_update_notebook_with_empty_body_changes_nothing(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Original", "icon": "📘"}, headers=headers).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Original"
    assert response.json()["icon"] == "📘"


async def test_update_notebook_clears_icon_with_null(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Meu", "icon": "📘"}, headers=headers).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={"icon": None}, headers=headers)

    assert response.status_code == 200
    assert response.json()["icon"] is None


async def test_update_notebook_of_another_user_returns_not_found(client, user_factory, auth_headers):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    created = client.post("/v1/notebooks", json={"name": "Privado"}, headers=auth_headers(owner)).json()

    response = client.patch(f"/v1/notebooks/{created['id']}", json={"name": "Invadido"}, headers=auth_headers(other))

    assert response.status_code == 404
    assert response.json()["code"] == "NOTEBOOK_NOT_FOUND"


async def test_delete_notebook(client, user_factory, auth_headers):
    user = await user_factory()
    headers = auth_headers(user)
    created = client.post("/v1/notebooks", json={"name": "Descartável"}, headers=headers).json()

    response = client.delete(f"/v1/notebooks/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/v1/notebooks/{created['id']}", headers=headers).status_code == 404


async def test_delete_notebook_of_another_user_returns_not_found(client, user_factory, auth_headers):
    owner = await user_factory(email="dono@example.com")
    other = await user_factory(email="outro@example.com")
    created = client.post("/v1/notebooks", json={"name": "Privado"}, headers=auth_headers(owner)).json()

    response = client.delete(f"/v1/notebooks/{created['id']}", headers=auth_headers(other))

    assert response.status_code == 404
    assert client.get(f"/v1/notebooks/{created['id']}", headers=auth_headers(owner)).status_code == 200


async def test_delete_notebook_removes_stored_pdfs(client, user_factory, auth_headers, pdf_bytes, storage_dir):
    user = await user_factory()
    headers = auth_headers(user)
    notebook = client.post("/v1/notebooks", json={"name": "Com arquivos"}, headers=headers).json()
    client.post(
        f"/v1/notebooks/{notebook['id']}/files",
        files={"upload": ("manual.pdf", pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    assert list(storage_dir.rglob("*.pdf"))

    assert client.delete(f"/v1/notebooks/{notebook['id']}", headers=headers).status_code == 204

    assert list(storage_dir.rglob("*.pdf")) == []


async def test_delete_notebook_keeps_files_of_other_notebooks(
    client, user_factory, auth_headers, pdf_bytes, storage_dir
):
    user = await user_factory()
    headers = auth_headers(user)
    kept = client.post("/v1/notebooks", json={"name": "Fica"}, headers=headers).json()
    removed = client.post("/v1/notebooks", json={"name": "Some"}, headers=headers).json()
    for notebook in (kept, removed):
        client.post(
            f"/v1/notebooks/{notebook['id']}/files",
            files={"upload": ("manual.pdf", pdf_bytes(), "application/pdf")},
            headers=headers,
        )

    client.delete(f"/v1/notebooks/{removed['id']}", headers=headers)

    remaining = [path.as_posix() for path in storage_dir.rglob("*.pdf")]
    assert len(remaining) == 1
    assert kept["id"] in remaining[0]
