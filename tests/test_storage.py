"""Testes do modulo storage (abstracao de objetos tipo S3)."""

from __future__ import annotations

import pytest

from backup_s3.storage import ObjectNotFoundError


def test_put_get_roundtrip(storage):
    storage.put("arquivo.txt", b"conteudo")
    assert storage.get("arquivo.txt") == b"conteudo"


def test_get_missing_raises(storage):
    with pytest.raises(ObjectNotFoundError):
        storage.get("nao-existe.txt")


def test_delete_then_get_missing(storage):
    storage.put("a.txt", b"1")
    storage.delete("a.txt")
    with pytest.raises(ObjectNotFoundError):
        storage.get("a.txt")


def test_list_returns_keys(storage):
    storage.put("sub/a.txt", b"1")
    storage.put("sub/b.txt", b"2")
    storage.put("raiz.txt", b"3")
    keys = {obj.key for obj in storage.list()}
    assert keys == {"sub/a.txt", "sub/b.txt", "raiz.txt"}


def test_exists_true_and_false(storage):
    assert not storage.exists("nao-existe.txt")
    storage.put("existe.txt", b"x")
    assert storage.exists("existe.txt")
