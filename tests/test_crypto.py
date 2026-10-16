"""Testes do modulo crypto (cifra AES-256-GCM + PBKDF2)."""

from __future__ import annotations

import pytest

from backup_s3.crypto import CryptoError, decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    plaintext = b"dados sensiveis do backup"
    package = encrypt(plaintext, "senha-secreta")
    assert package != plaintext
    assert decrypt(package, "senha-secreta") == plaintext


def test_encrypt_different_package_each_call():
    plaintext = b"mesmo texto"
    assert encrypt(plaintext, "senha") != encrypt(plaintext, "senha")


def test_decrypt_wrong_passphrase_raises():
    package = encrypt(b"x", "senha-correta")
    with pytest.raises(CryptoError):
        decrypt(package, "senha-errada")


def test_decrypt_tampered_ciphertext_raises():
    package = encrypt(b"x", "senha")
    tampered = package[:-1] + bytes([package[-1] ^ 0xFF])
    with pytest.raises(CryptoError):
        decrypt(tampered, "senha")


def test_encrypt_empty_bytes():
    assert decrypt(encrypt(b"", "senha"), "senha") == b""


def test_decrypt_truncated_package_raises():
    with pytest.raises(CryptoError):
        decrypt(b"pacote-curto", "senha")
