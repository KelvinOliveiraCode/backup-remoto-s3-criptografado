"""Fixtures de armazenamento para os testes.

Suporta dois backends: ``fake`` (diretorio local, sem rede) e ``s3``
(moto simulando AWS, credenciais dummy). Cada teste de backup/rotacao
roda nos dois backends.
"""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from backup_s3.storage import LocalFakeBackend, S3Backend


@pytest.fixture
def fake_storage(tmp_path):
    return LocalFakeBackend(root=tmp_path / "s3fake")


@pytest.fixture
def s3_storage():
    with mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.create_bucket(Bucket="backup-remoto")
        yield S3Backend(bucket="backup-remoto")


@pytest.fixture(params=["fake", "s3"])
def storage(request, fake_storage, s3_storage):
    if request.param == "fake":
        return fake_storage
    return s3_storage
