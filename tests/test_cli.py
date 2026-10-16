"""Testes da interface de linha de comando (CLI)."""

from __future__ import annotations

import re

from backup_s3.cli import main

_ID_RE = re.compile(r"Backup ([A-Za-z0-9]+) concluido")


def test_cli_backup_restore_list(tmp_path, capsys):
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.txt").write_text("hello")
    root = tmp_path / "fake"

    assert (
        main(
            [
                "backup",
                str(source),
                "--backend",
                "fake",
                "--root",
                str(root),
                "--passphrase",
                "senha",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    match = _ID_RE.search(out)
    assert match, out
    bid = match.group(1)

    assert main(["list", "--backend", "fake", "--root", str(root)]) == 0
    assert bid in capsys.readouterr().out

    dest = tmp_path / "dest"
    assert (
        main(
            [
                "restore",
                bid,
                str(dest),
                "--backend",
                "fake",
                "--root",
                str(root),
                "--passphrase",
                "senha",
            ]
        )
        == 0
    )
    assert (dest / "a.txt").read_text() == "hello"


def test_cli_verify_ok_and_tampered(tmp_path, capsys):
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.txt").write_text("hello")
    root = tmp_path / "fake"
    main(
        [
            "backup",
            str(source),
            "--backend",
            "fake",
            "--root",
            str(root),
            "--passphrase",
            "senha",
        ]
    )
    out = capsys.readouterr().out
    bid = re.search(r"Backup ([A-Za-z0-9]+) concluido", out).group(1)

    assert (
        main(
            ["verify", bid, "--backend", "fake", "--root", str(root), "--passphrase", "senha"]
        )
        == 0
    )

    # Adulterar o objeto cifrado.
    from backup_s3.storage import LocalFakeBackend

    storage = LocalFakeBackend(root=root)
    enc = next(o for o in storage.list() if o.key.endswith(".enc"))
    pkg = storage.get(enc.key)
    storage.put(enc.key, pkg[:-1] + bytes([pkg[-1] ^ 0xFF]))

    assert (
        main(
            ["verify", bid, "--backend", "fake", "--root", str(root), "--passphrase", "senha"]
        )
        == 1
    )
