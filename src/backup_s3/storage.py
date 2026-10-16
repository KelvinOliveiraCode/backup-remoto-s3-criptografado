"""Abstracao de armazenamento de objetos (S3 ou falso local).

Contrato: as chaves sao usadas exatamente como passadas, sem prefixo
oculto. Quem aplica o prefixo de escopo (ex. "backups/") e o chamante
(BackupManager). Assim os backends S3 e falso local se comportam igual.
Nao exige credenciais AWS reais nem rede no backend falso.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    last_modified: str  # ISO 8601


class ObjectNotFoundError(FileNotFoundError):
    """Objeto nao existe no armazenamento."""


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
        """Grava ``data`` em ``key``."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Lê os bytes de ``key``. Levanta ObjectNotFoundError se ausente."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove ``key`` (sem erro se ja nao existir)."""

    @abstractmethod
    def list(self, prefix: str = "") -> list[ObjectInfo]:
        """Lista objetos sob ``prefix``."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Retorna True se ``key`` existe."""


class S3Backend(StorageBackend):
    """Backend sobre Amazon S3 via boto3.

    Chaves sao gravadas/leras brutas no bucket (sem prefixo oculto).
    Credenciais dummy por default (test/test); em producao use as reais
    ou deixe o boto3 resolv-las do ambiente.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        aws_access_key_id: str = "test",
        aws_secret_access_key: str = "test",
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(key) from exc
            raise
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def list(self, prefix: str = "") -> list[ObjectInfo]:
        resp = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        items: list[ObjectInfo] = []
        for obj in resp.get("Contents", []):
            items.append(
                ObjectInfo(
                    key=obj["Key"],
                    size=int(obj["Size"]),
                    last_modified=obj["LastModified"].isoformat(),
                )
            )
        return items

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("404", "NotFound", "NoSuchKey"):
                return False
            raise


class LocalFakeBackend(StorageBackend):
    """Simula um bucket S3 em um diretorio local. Sem credenciais, sem rede."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._root / key

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise ObjectNotFoundError(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def list(self, prefix: str = "") -> list[ObjectInfo]:
        base = self._root / prefix if prefix else self._root
        items: list[ObjectInfo] = []
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(self._root).as_posix()
                    stat = path.stat()
                    items.append(
                        ObjectInfo(
                            key=rel,
                            size=stat.st_size,
                            last_modified=datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ).isoformat(),
                        )
                    )
        return items

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


def create_storage(backend: str = "fake", **kwargs) -> StorageBackend:
    """Factory de backends.

    Exemplos::

        create_storage("fake", root=".s3fake")
        create_storage("s3", bucket="meu-bucket")
    """
    if backend == "s3":
        return S3Backend(**kwargs)
    if backend == "fake":
        return LocalFakeBackend(kwargs.get("root", ".s3fake"))
    raise ValueError(f"backend desconhecido: {backend}")
