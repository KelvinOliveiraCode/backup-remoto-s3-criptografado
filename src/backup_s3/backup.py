"""Backup cifrado de diretorio local em armazenamento tipo S3.

Fluxo:
1. gera um arquivo tar deterministico do diretorio de origem;
2. cifra com AES-256-GCM (senha derivada via PBKDF2);
3. envia para o armazenamento junto com metadados (hash SHA-256);
4. rotacao remove backups antigos além do limite;
5. restaura baixa, verifica o hash, decifra e extrai.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .crypto import decrypt, encrypt
from .storage import ObjectNotFoundError, StorageBackend

DEFAULT_PREFIX = "backups/"


class BackupError(RuntimeError):
    """Erro geral de operacao de backup."""


class IntegrityError(BackupError):
    """Hash do objeto baixado nao confere com o metadado armazenado."""


@dataclass(frozen=True)
class BackupInfo:
    id: str
    created_at: str
    source: str
    size_encrypted: int
    hash_sha256: str
    file_count: int

    def object_key(self) -> str:
        return f"{self.id}.enc"

    def meta_key(self) -> str:
        return f"{self.id}.meta.json"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_archive(source: Path) -> tuple[bytes, int]:
    """Gera um tar deterministico do diretorio.

    Retorna (bytes do arquivo tar, quantidade de arquivos).
    """
    source = source.resolve()
    if not source.is_dir():
        raise BackupError(f"origem nao e um diretorio: {source}")
    files = sorted(p for p in source.rglob("*") if p.is_file())
    buffer = io.BytesIO()
    count = 0
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for path in files:
            arcname = path.relative_to(source).as_posix()
            tar.add(path, arcname=arcname, recursive=False)
            count += 1
    return buffer.getvalue(), count


class BackupManager:
    def __init__(
        self,
        storage: StorageBackend,
        passphrase: str | None = None,
        prefix: str = DEFAULT_PREFIX,
    ) -> None:
        self._storage = storage
        self._passphrase = passphrase
        self._prefix = prefix.rstrip("/") + "/"

    def _require_passphrase(self) -> str:
        if self._passphrase is None:
            raise BackupError("passphrase nao informada")
        return self._passphrase

    def backup(self, source: str | Path) -> BackupInfo:
        """Faz backup cifrado de ``source``. Retorna as informacoes do backup."""
        source = Path(source)
        plaintext, file_count = _make_archive(source)
        package = encrypt(plaintext, self._require_passphrase())
        digest = hashlib.sha256(package).hexdigest()
        now = _now()
        info = BackupInfo(
            id=now.strftime("%Y%m%dT%H%M%S%f"),
            created_at=now.isoformat(),
            source=str(source.resolve()),
            size_encrypted=len(package),
            hash_sha256=digest,
            file_count=file_count,
        )
        self._storage.put(self._prefix + info.object_key(), package)
        meta = json.dumps(asdict(info), ensure_ascii=False, indent=2).encode("utf-8")
        self._storage.put(self._prefix + info.meta_key(), meta)
        return info

    def list(self) -> list[BackupInfo]:
        """Lista backups existentes, do mais recente para o mais antigo."""
        metas: list[BackupInfo] = []
        for obj in self._storage.list(prefix=self._prefix):
            if not obj.key.endswith(".meta.json"):
                continue
            try:
                data = json.loads(self._storage.get(obj.key))
                metas.append(BackupInfo(**data))
            except (json.JSONDecodeError, TypeError, KeyError, ValueError, ObjectNotFoundError):
                # Meta invalida ou corrompida: ignora e segue.
                continue
        metas.sort(key=lambda b: b.created_at, reverse=True)
        return metas

    def _find_meta(self, backup_id: str) -> BackupInfo:
        for info in self.list():
            if info.id == backup_id:
                return info
        raise ObjectNotFoundError(f"backup nao encontrado: {backup_id}")

    def _read_object(self, backup_id: str) -> tuple[BackupInfo, bytes]:
        meta = self._find_meta(backup_id)
        package = self._storage.get(self._prefix + meta.object_key())
        return meta, package

    def restore(self, backup_id: str, dest: str | Path) -> Path:
        """Restaura ``backup_id`` em ``dest`` apos verificar o hash."""
        dest = Path(dest)
        meta, package = self._read_object(backup_id)
        actual = hashlib.sha256(package).hexdigest()
        if actual != meta.hash_sha256:
            raise IntegrityError(
                "hash nao confere para backup "
                f"{backup_id}: esperado {meta.hash_sha256}, obtido {actual}"
            )
        plaintext = decrypt(package, self._require_passphrase())
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(plaintext)) as tar:
            tar.extractall(dest, filter="data")
        return dest

    def verify(self, backup_id: str) -> BackupInfo:
        """Verifica integridade (hash) e decifrabilidade de um backup."""
        meta, package = self._read_object(backup_id)
        actual = hashlib.sha256(package).hexdigest()
        if actual != meta.hash_sha256:
            raise IntegrityError(
                "hash nao confere para backup "
                f"{backup_id}: esperado {meta.hash_sha256}, obtido {actual}"
            )
        decrypt(package, self._require_passphrase())
        return meta

    def rotate(self, keep: int = 5) -> list[BackupInfo]:
        """Remove backups antigos alem dos ``keep`` mais recentes.

        Retorna a lista dos backups removidos.
        """
        if keep < 0:
            raise ValueError("keep deve ser >= 0")
        backups = self.list()
        removed: list[BackupInfo] = []
        for info in backups[keep:]:
            self._storage.delete(self._prefix + info.object_key())
            self._storage.delete(self._prefix + info.meta_key())
            removed.append(info)
        return removed
