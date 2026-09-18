import pytest

from src.storage.local import LocalStorage


def test_save_creates_nested_directories(tmp_path):
    storage = LocalStorage(tmp_path)

    storage.save("users/abc/notebooks/def/arquivo.pdf", b"conteudo")

    assert (tmp_path / "users/abc/notebooks/def/arquivo.pdf").read_bytes() == b"conteudo"


def test_delete_prefix_removes_only_that_subtree(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save("users/abc/notebooks/1/a.pdf", b"a")
    storage.save("users/abc/notebooks/2/b.pdf", b"b")

    storage.delete_prefix("users/abc/notebooks/1")

    assert not (tmp_path / "users/abc/notebooks/1").exists()
    assert (tmp_path / "users/abc/notebooks/2/b.pdf").exists()


def test_delete_prefix_is_silent_when_prefix_does_not_exist(tmp_path):
    LocalStorage(tmp_path).delete_prefix("users/abc/notebooks/inexistente")


def test_delete_prefix_refuses_to_wipe_base_dir(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save("users/abc/arquivo.pdf", b"a")

    with pytest.raises(ValueError):
        storage.delete_prefix("")

    assert (tmp_path / "users/abc/arquivo.pdf").exists()


def test_keys_cannot_escape_base_dir(tmp_path):
    storage = LocalStorage(tmp_path / "storage")

    with pytest.raises(ValueError):
        storage.save("../fora.pdf", b"a")

    with pytest.raises(ValueError):
        storage.delete_prefix("../..")
