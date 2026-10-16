"""Cifragem simetrica AES-256-GCM com derivacao de chave via PBKDF2.

O pacote cifrado e organizado como: salt (16) + nonce (12) + ciphertext + tag (16).
A autenticacao do GCM garante que qualquer alteracao nos dados seja detectada
na decifracao.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16
NONCE_SIZE = 12  # nonce padrao para GCM
KEY_SIZE = 32  # AES-256
TAG_SIZE = 16
ITERATIONS = 200_000


class CryptoError(ValueError):
    """Erro na cifra ou na verificacao de integridade do pacote."""


@dataclass(frozen=True)
class EncryptedPackage:
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    tag: bytes

    def serialize(self) -> bytes:
        """Serializa para salt + nonce + ciphertext + tag."""
        return self.salt + self.nonce + self.ciphertext + self.tag

    @classmethod
    def deserialize(cls, data: bytes) -> EncryptedPackage:
        if len(data) < SALT_SIZE + NONCE_SIZE + TAG_SIZE:
            raise CryptoError("pacote cifrado muito curto")
        salt = data[:SALT_SIZE]
        nonce = data[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
        tag = data[-TAG_SIZE:]
        ciphertext = data[SALT_SIZE + NONCE_SIZE : -TAG_SIZE]
        return cls(salt=salt, nonce=nonce, ciphertext=ciphertext, tag=tag)


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt(plaintext: bytes, passphrase: str) -> bytes:
    """Cifra ``plaintext`` com AES-256-GCM.

    Retorna os bytes serializados (salt + nonce + ciphertext + tag).
    Cada chamada usa salt e nonce aleatorios, então o mesmo texto
    produz pacotes diferentes a cada vez.
    """
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _derive_key(passphrase, salt)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return EncryptedPackage(salt, nonce, ciphertext, encryptor.tag).serialize()


def decrypt(package: bytes, passphrase: str) -> bytes:
    """Decifra o pacote e verifica a integridade.

    Levanta :class:`CryptoError` se o pacote estiver corrompido ou a
    senha estiver incorreta (etiqueta GCM invalida).
    """
    pkg = EncryptedPackage.deserialize(package)
    key = _derive_key(passphrase, pkg.salt)
    cipher = Cipher(algorithms.AES(key), modes.GCM(pkg.nonce, pkg.tag))
    decryptor = cipher.decryptor()
    try:
        return decryptor.update(pkg.ciphertext) + decryptor.finalize()
    except Exception as exc:  # InvalidTag -> corrompido ou senha errada
        raise CryptoError(
            "falha ao decifrar: pacote corrompido ou senha incorreta"
        ) from exc
