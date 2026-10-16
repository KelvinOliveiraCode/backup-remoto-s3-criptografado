# backup-remoto-s3-criptografado

## Português

### Descrição
Faz backup cifrado de um diretório local em um bucket tipo S3, com rotação de backups antigos e verificação de integridade por hash SHA-256.

- Cifra com AES-256-GCM (biblioteca `cryptography`); a chave deriva da senha via PBKDF2-SHA256.
- Envia para um bucket S3 (via `boto3`) ou para um backend falso local (sem credenciais AWS, sem rede).
- Rotação: mantém apenas os N backups mais recentes.
- Restaura: baixa, verifica o hash do objeto contra o metadado armazenado, decifra e extrai.
- Sem credenciais AWS reais.

### Como usar
Instale as dependências e rode o módulo:

```
pip install -e .
python -m backup_s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 list --backend fake --root .s3fake
python -m backup_s3 restore <id> ./restaurado --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 verify <id> --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 rotate --keep 3 --backend fake --root .s3fake
```

Use `--backend s3 --bucket <nome>` para um bucket S3 real ou simulado com o `moto`.

### Testes
```
python -m pytest -q
```

A suíte roda em dois backends: falso local e `moto` (S3 simulado). 36 testes passam.

### Licença
MIT

### Autor
Kelvin Oliveira

## English

### Description
Encrypted backup of a local directory to an S3-like bucket, with rotation of old backups and SHA-256 integrity verification.

- Encrypts with AES-256-GCM (`cryptography`); the key is derived from the passphrase via PBKDF2-SHA256.
- Sends to an S3 bucket (via `boto3`) or to a local fake backend (no AWS credentials, no network).
- Rotation: keeps only the N most recent backups.
- Restore: downloads, verifies the object hash against stored metadata, decrypts, extracts.
- No real AWS credentials.

### Usage
Install dependencies and run the module:

```
pip install -e .
python -m backup_s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 list --backend fake --root .s3fake
python -m backup_s3 restore <id> ./restaurado --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 verify <id> --backend fake --root .s3fake --passphrase "senha"
python -m backup_s3 rotate --keep 3 --backend fake --root .s3fake
```

Use `--backend s3 --bucket <name>` for a real or `moto`-simulated S3 bucket.

### Tests
```
python -m pytest -q
```

The suite runs on two backends: local fake and `moto` (simulated S3). 36 tests pass.

### License
MIT

### Author
Kelvin Oliveira
