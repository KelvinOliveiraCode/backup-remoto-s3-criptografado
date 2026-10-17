# backup-remoto-s3-criptografado

Encrypted backup of a local directory to an S3-like bucket, with rotation of old backups and SHA-256 integrity verification. No real AWS credentials.

Version 0.1.0. Python >= 3.10.

## Features

- Encrypts with AES-256-GCM (`cryptography` library); the key is derived from the passphrase via PBKDF2-SHA256 with 200,000 iterations.
- The encrypted package is serialized as salt (16 bytes) + nonce (12 bytes) + ciphertext + tag (16 bytes).
- Sends to an S3 bucket via `boto3` or to a local fake backend (no AWS credentials, no network).
- Generates a deterministic tar archive of the source directory before encrypting.
- Stores the SHA-256 hash of the package in metadata alongside the object.
- Rotation: keeps only the N most recent backups.
- Restore: downloads, verifies the hash against stored metadata, decrypts, extracts.
- The `verify` command checks integrity and decryptability without restoring.

## Requirements

- Python 3.10 or higher
- Dependencies: `boto3>=1.28.0`, `cryptography>=42.0.0`
- Tests (optional): `pytest>=8.0.0`, `moto>=5.0.0`

## Installation

Install the package in editable mode:

```
pip install -e .
```

This provides the `backup-s3` command (entry point) and execution via `python -m backup_s3`.

## Usage

Local fake backend (no AWS credentials, no network):

```
backup-s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
backup-s3 list --backend fake --root .s3fake
backup-s3 restore <id> ./restored --backend fake --root .s3fake --passphrase "senha"
backup-s3 verify <id> --backend fake --root .s3fake --passphrase "senha"
backup-s3 rotate --keep 3 --backend fake --root .s3fake
```

Also runnable as a module:

```
python -m backup_s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
```

Real S3 bucket or `moto`-simulated S3:

```
backup-s3 backup ./dados --backend s3 --bucket my-bucket --passphrase "senha"
```

Common arguments:

- `--backend fake|s3` (default: `fake`)
- `--root` root directory of the fake backend (default: `.s3fake`)
- `--bucket` S3 bucket name (default: `backup-remoto`)
- `--passphrase` encryption passphrase

The `backup` command applies rotation automatically after creating the backup, keeping the N most recent (default 5, adjustable with `--keep`).

## Tests

```
pip install -e ".[test]"
python -m pytest -q
```

The suite runs on two backends: local fake and `moto` (simulated S3). 36 tests pass.

## Package structure

- `src/backup_s3/__init__.py` — public API and version.
- `src/backup_s3/crypto.py` — AES-256-GCM encryption and PBKDF2-SHA256 key derivation.
- `src/backup_s3/storage.py` — `StorageBackend`, `S3Backend` (`boto3`), `LocalFakeBackend` (local, no credentials), `create_storage`.
- `src/backup_s3/backup.py` — `BackupManager`: backup, list, restore, verify hash, rotate.
- `src/backup_s3/cli.py` — commands `backup`, `list`, `restore`, `verify`, `rotate`.
- `src/backup_s3/__main__.py` — execution as `python -m backup_s3`.
- `tests/` — tests for `crypto`, `storage`, `backup` and `cli`.

## Security

Do not store the passphrase in scripts or shell history. Use environment variables or read the passphrase at runtime. The S3 backend uses dummy credentials (`test`/`test`) by default; in production replace with real credentials or let `boto3` resolve them from the environment.

Encryption is symmetric: the same passphrase is required to encrypt and decrypt. Without the passphrase the data cannot be recovered.

## License

MIT

## Author

Kelvin Oliveira
