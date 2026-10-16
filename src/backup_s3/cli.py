"""Interface de linha de comando do backup cifrado.

Exemplos::

    backup-s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
    backup-s3 list --backend fake --root .s3fake
    backup-s3 restore <id> ./restaurado --backend fake --root .s3fake --passphrase "senha"
    backup-s3 verify <id> --backend fake --root .s3fake --passphrase "senha"
    backup-s3 rotate --keep 3 --backend fake --root .s3fake
"""

from __future__ import annotations

import argparse
import re
import sys

from .backup import BackupError, BackupManager, IntegrityError
from .crypto import CryptoError
from .storage import LocalFakeBackend, ObjectNotFoundError, S3Backend, StorageBackend


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backup-s3",
        description="Backup cifrado (AES-256-GCM) de diretorio local em S3 simulado, com rotacao.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_storage_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--backend", default="fake", choices=["fake", "s3"])
        p.add_argument("--root", default=".s3fake", help="raiz do backend fake")
        p.add_argument("--bucket", default="backup-remoto", help="bucket S3 (backend s3)")
        p.add_argument("--passphrase", help="senha de cifragem")

    p_backup = sub.add_parser("backup", help="faz backup cifrado de um diretorio")
    p_backup.add_argument("source", help="diretorio local a ser copiado")
    p_backup.add_argument("--keep", type=int, default=5, help="quantos backups manter apos rotacao")
    _add_storage_args(p_backup)

    p_restore = sub.add_parser("restore", help="restaura um backup e verifica o hash")
    p_restore.add_argument("backup_id")
    p_restore.add_argument("dest")
    _add_storage_args(p_restore)

    p_list = sub.add_parser("list", help="lista backups existentes")
    _add_storage_args(p_list)

    p_rotate = sub.add_parser("rotate", help="remove backups excedentes")
    p_rotate.add_argument("--keep", type=int, default=5)
    _add_storage_args(p_rotate)

    p_verify = sub.add_parser("verify", help="verifica integridade (hash) de um backup")
    p_verify.add_argument("backup_id")
    _add_storage_args(p_verify)

    return parser


def _storage(args) -> StorageBackend:
    if args.backend == "s3":
        return S3Backend(bucket=args.bucket)
    return LocalFakeBackend(root=args.root)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manager = BackupManager(storage=_storage(args), passphrase=args.passphrase)

    try:
        if args.command == "backup":
            info = manager.backup(args.source)
            manager.rotate(args.keep)
            print(f"Backup {info.id} concluido ({info.size_encrypted} bytes, {info.file_count} arquivos).")
        elif args.command == "restore":
            path = manager.restore(args.backup_id, args.dest)
            print(f"Restaurado em {path}")
        elif args.command == "list":
            for info in manager.list():
                print(f"{info.id}  {info.size_encrypted} bytes  {info.file_count} arquivos  {info.created_at}")
        elif args.command == "rotate":
            removed = manager.rotate(args.keep)
            print(f"Removidos {len(removed)} backup(s).")
        elif args.command == "verify":
            info = manager.verify(args.backup_id)
            print(f"Backup {info.id} valido (hash confere).")
        return 0
    except (IntegrityError, CryptoError, ObjectNotFoundError, BackupError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


_ID_RE = re.compile(r"Backup ([A-Za-z0-9]+) concluido")


def backup_id_from_output(output: str) -> str | None:
    """Extrai o id do backup impresso pelo comando ``backup``."""
    match = _ID_RE.search(output)
    return match.group(1) if match else None


if __name__ == "__main__":
    raise SystemExit(main())
