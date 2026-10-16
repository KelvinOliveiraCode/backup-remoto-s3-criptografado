"""Testes do modulo backup (criar, listar, restaurar, rotacionar, verificar)."""

from __future__ import annotations

import hashlib

import pytest

from backup_s3 import BackupError, IntegrityError
from backup_s3.backup import BackupManager
from backup_s3.storage import ObjectNotFoundError


def _make_source(tmp_path, files):
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    for rel, content in files.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return source


def test_backup_creates_object_and_meta(storage, tmp_path):
    source = _make_source(tmp_path, {"a.txt": b"hello", "sub/b.txt": b"world"})
    mgr = BackupManager(storage=storage, passphrase="senha")
    info = mgr.backup(source)
    assert info.file_count == 2
    assert info.size_encrypted > 0
    obj_key = mgr._prefix + info.object_key()
    assert info.hash_sha256 == hashlib.sha256(storage.get(obj_key)).hexdigest()
    meta = storage.get(mgr._prefix + info.meta_key())
    assert info.id.encode() in meta


def test_restore_recovers_files(storage, tmp_path):
    source = _make_source(tmp_path, {"a.txt": b"hello", "sub/b.txt": b"world"})
    mgr = BackupManager(storage=storage, passphrase="senha")
    info = mgr.backup(source)
    dest = tmp_path / "dest"
    mgr.restore(info.id, dest)
    assert (dest / "a.txt").read_bytes() == b"hello"
    assert (dest / "sub" / "b.txt").read_bytes() == b"world"


def test_restore_missing_backup_raises(storage, tmp_path):
    mgr = BackupManager(storage=storage, passphrase="senha")
    with pytest.raises(ObjectNotFoundError):
        mgr.restore("nao-existe", tmp_path / "dest")


def test_restore_tampered_hash_raises(storage, tmp_path):
    source = _make_source(tmp_path, {"a.txt": b"hello"})
    mgr = BackupManager(storage=storage, passphrase="senha")
    info = mgr.backup(source)
    obj_key = mgr._prefix + info.object_key()
    pkg = storage.get(obj_key)
    storage.put(obj_key, pkg[:-1] + bytes([pkg[-1] ^ 0xFF]))
    with pytest.raises(IntegrityError):
        mgr.restore(info.id, tmp_path / "dest")


def test_verify_ok(storage, tmp_path):
    source = _make_source(tmp_path, {"a.txt": b"hello"})
    mgr = BackupManager(storage=storage, passphrase="senha")
    info = mgr.backup(source)
    result = mgr.verify(info.id)
    assert result.id == info.id


def test_verify_tampered_raises(storage, tmp_path):
    source = _make_source(tmp_path, {"a.txt": b"hello"})
    mgr = BackupManager(storage=storage, passphrase="senha")
    info = mgr.backup(source)
    obj_key = mgr._prefix + info.object_key()
    pkg = storage.get(obj_key)
    storage.put(obj_key, pkg[:-1] + bytes([pkg[-1] ^ 0xFF]))
    with pytest.raises(IntegrityError):
        mgr.verify(info.id)


def test_list_ordered_most_recent_first(storage, tmp_path):
    mgr = BackupManager(storage=storage, passphrase="senha")
    ids = []
    for i in range(3):
        source = _make_source(tmp_path, {f"f{i}.txt": b"x"})
        ids.append(mgr.backup(source).id)
    listed = [b.id for b in mgr.list()]
    assert listed[0] == ids[-1]
    assert set(listed) == set(ids)


def test_rotate_keeps_n_most_recent(storage, tmp_path):
    mgr = BackupManager(storage=storage, passphrase="senha")
    ids = []
    for i in range(5):
        source = _make_source(tmp_path, {f"f{i}.txt": b"x"})
        ids.append(mgr.backup(source).id)
    removed = mgr.rotate(keep=2)
    assert len(removed) == 3
    remaining = {b.id for b in mgr.list()}
    assert remaining == {ids[-1], ids[-2]}
    for info in removed:
        assert not storage.exists(mgr._prefix + info.object_key())
        assert not storage.exists(mgr._prefix + info.meta_key())


def test_backup_nonexistent_source_raises(storage):
    mgr = BackupManager(storage=storage, passphrase="senha")
    with pytest.raises(BackupError):
        mgr.backup("caminho/que/nao/existe")
