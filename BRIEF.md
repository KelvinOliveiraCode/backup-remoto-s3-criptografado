# BRIEF — backup-remoto-s3-criptografado

## Projeto
Backup cifrado S3 com rotação (área DevOps/Cloud). Stack: Python + boto3.

## Entregas
- `pyproject.toml` — dependências (boto3, cryptography), entry point `backup-s3`, layout `src/`.
- `src/backup_s3/__init__.py` — API pública.
- `src/backup_s3/crypto.py` — AES-256-GCM + PBKDF2-SHA256.
- `src/backup_s3/storage.py` — `StorageBackend`, `S3Backend` (boto3), `LocalFakeBackend` (sem credenciais/rede), `create_storage`.
- `src/backup_s3/backup.py` — `BackupManager`: backup, listar, restaurar, verificar hash, rotacionar.
- `src/backup_s3/cli.py` — comandos backup, list, restore, verify, rotate.
- `src/backup_s3/__main__.py` — `python -m backup_s3`.
- `tests/` — conftest + test_crypto, test_storage, test_backup, test_cli (36 testes, backends falso local e moto/S3).
- `README.md` — bilíngue PT-BR + EN (título, descrição, como usar, testes, licença MIT, autor Kelvin Oliveira).
- `BRIEF.md` — este arquivo.

## Como verificar
```
cd C:\Users\Kelvin\AppData\Local\Temp\opencode\github-staging\projects\backup-remoto-s3-criptografado
pip install -e .
python -m ruff check .
python -m pytest -q
```

Resultado esperado: `ruff` sem avisos e 36 testes passando (falso local + `moto`).

## Critérios de aceitação
- backup e restaura funcionam (cifra AES-256-GCM, rotação de antigos, verificação de hash SHA-256)
- suíte de testes passa
- README PT-BR + EN completo
- sem credenciais AWS reais
