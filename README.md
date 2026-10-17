# backup-remoto-s3-criptografado

Backup cifrado de um diretório local em um bucket tipo S3, com rotação de backups antigos e verificação de integridade por hash SHA-256. Sem credenciais AWS reais.

Versão 0.1.0. Python >= 3.10.

## Características

- Cifra com AES-256-GCM (biblioteca `cryptography`); a chave deriva da senha via PBKDF2-SHA256 com 200.000 iterações.
- O pacote cifrado é serializado como salt (16 bytes) + nonce (12 bytes) + ciphertext + tag (16 bytes).
- Envia para um bucket S3 via `boto3` ou para um backend falso local (sem credenciais AWS, sem rede).
- Gera um arquivo tar determinístico do diretório de origem antes de cifrar.
- Armazena o hash SHA-256 do pacote em metadados ao lado do objeto.
- Rotação: mantém apenas os N backups mais recentes.
- Restaura: baixa, verifica o hash contra o metadado armazenado, decifra e extrai.
- O comando `verify` checa integridade e decifrabilidade sem restaurar.

## Requisitos

- Python 3.10 ou superior
- Dependências: `boto3>=1.28.0`, `cryptography>=42.0.0`
- Testes (opcional): `pytest>=8.0.0`, `moto>=5.0.0`

## Instalação

Instale o pacote em modo editável:

```
pip install -e .
```

Isso disponibiliza o comando `backup-s3` (ponto de entrada) e a execução via `python -m backup_s3`.

## Como usar

Backend falso local (sem credenciais AWS, sem rede):

```
backup-s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
backup-s3 list --backend fake --root .s3fake
backup-s3 restore <id> ./restaurado --backend fake --root .s3fake --passphrase "senha"
backup-s3 verify <id> --backend fake --root .s3fake --passphrase "senha"
backup-s3 rotate --keep 3 --backend fake --root .s3fake
```

Também é possível rodar como módulo:

```
python -m backup_s3 backup ./dados --backend fake --root .s3fake --passphrase "senha"
```

Backend S3 real ou simulado com o `moto`:

```
backup-s3 backup ./dados --backend s3 --bucket meu-bucket --passphrase "senha"
```

Argumentos comuns:

- `--backend fake|s3` (padrão: `fake`)
- `--root` raiz do diretório do backend falso (padrão: `.s3fake`)
- `--bucket` nome do bucket S3 (padrão: `backup-remoto`)
- `--passphrase` senha de cifragem

O comando `backup` aplica rotação automaticamente depois de criar o backup, mantendo os N mais recentes (padrão 5, ajuste com `--keep`).

## Testes

```
pip install -e ".[test]"
python -m pytest -q
```

A suíte roda em dois backends: falso local e `moto` (S3 simulado). 36 testes passam.

## Estrutura do pacote

- `src/backup_s3/__init__.py` — API pública e versão.
- `src/backup_s3/crypto.py` — cifragem AES-256-GCM e derivação de chave PBKDF2-SHA256.
- `src/backup_s3/storage.py` — `StorageBackend`, `S3Backend` (`boto3`), `LocalFakeBackend` (local, sem credenciais), `create_storage`.
- `src/backup_s3/backup.py` — `BackupManager`: backup, listar, restaurar, verificar hash, rotacionar.
- `src/backup_s3/cli.py` — comandos `backup`, `list`, `restore`, `verify`, `rotate`.
- `src/backup_s3/__main__.py` — execução como `python -m backup_s3`.
- `tests/` — testes para `crypto`, `storage`, `backup` e `cli`.

## Segurança

Não armazene a senha em scripts nem no histórico do shell. Use variáveis de ambiente ou leia a senha em tempo de execução. O backend S3 usa credenciais fictícias (`test`/`test`) por padrão; em produção substitua pelas credenciais reais ou deixe o `boto3` resolvê-las do ambiente.

A cifragem é simétrica: a mesma senha é necessária para cifrar e decifrar. Sem a senha não é possível recuperar os dados.

## Licença

MIT

## Autor

Kelvin Oliveira
