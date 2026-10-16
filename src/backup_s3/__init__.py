"""backup-remoto-s3-criptografado.

Backup cifrado de diretorio local em bucket S3 simulado, com rotacao
de backups antigos e verificacao de integridade por hash SHA-256.
Sem credenciais AWS reais.
"""

from .backup import (
    BackupError,
    BackupInfo,
    BackupManager,
    IntegrityError,
)
from .crypto import CryptoError, decrypt, encrypt
from .storage import (
    LocalFakeBackend,
    ObjectNotFoundError,
    S3Backend,
    StorageBackend,
    create_storage,
)

__all__ = [
    "BackupError",
    "BackupInfo",
    "BackupManager",
    "CryptoError",
    "IntegrityError",
    "LocalFakeBackend",
    "ObjectNotFoundError",
    "S3Backend",
    "StorageBackend",
    "create_storage",
    "decrypt",
    "encrypt",
]

__version__ = "0.1.0"
