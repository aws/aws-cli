"""IoT commands that save response fields to files (upstream
tests/functional/iot)."""

import os
from typing import Final

import pytest

from apihelpers import ApiSession, Reply

pytestmark = pytest.mark.asyncio

FROM_CSR: Final = (
    'iot create-certificate-from-csr --certificate-signing-request "abc"'
)
# The quotes are part of the argument: the command splits on whitespace.
FROM_CSR_PARAMS: Final = {"certificateSigningRequest": '"abc"'}


async def test_saves_cert_to_file_for_create_certificate_from_csr(
    api: ApiSession,
) -> None:
    outfile = api.cwd / "cert.pem"
    result = await api.run(
        [*FROM_CSR.split(), "--certificate-pem-outfile", str(outfile)],
        replies={"certificatePem": "cert..."},
    )
    assert result.operations_with_params == [
        ("CreateCertificateFromCsr", FROM_CSR_PARAMS)
    ]
    assert outfile.read_text(encoding="utf-8") == "cert..."


async def test_saves_files_for_create_keys_and_cert(api: ApiSession) -> None:
    cert = api.cwd / "cert.pem"
    public = api.cwd / "key_rsa.pub"
    private = api.cwd / "key_rsa"
    result = await api.run(
        [
            "iot",
            "create-keys-and-certificate",
            "--certificate-pem-outfile",
            str(cert),
            "--public-key-outfile",
            str(public),
            "--private-key-outfile",
            str(private),
        ],
        replies={
            "certificatePem": "cert...",
            "keyPair": {"PublicKey": "public", "PrivateKey": "private"},
        },
    )
    assert result.operations_with_params == [
        ("CreateKeysAndCertificate", {})
    ]
    assert cert.read_text(encoding="utf-8") == "cert..."
    assert public.read_text(encoding="utf-8") == "public"
    assert private.read_text(encoding="utf-8") == "private"


async def test_bad_response(api: ApiSession) -> None:
    outfile = api.cwd / "cert.pem"
    error = {"Error": {"Code": "v1", "Message": "v2", "Type": "v3"}}
    await api.assert_params_for_cmd(
        [*FROM_CSR.split(), "--certificate-pem-outfile", str(outfile)],
        stderr_contains="v2",
        expected_rc=254,
        replies=Reply(error, status=403),
    )
    assert not outfile.exists()


async def test_ensures_file_is_writable_before_sending(
    api: ApiSession,
) -> None:
    outfile = os.sep.join(["", "does", "not", "exist_", "file.txt"])
    result = await api.assert_params_for_cmd(
        [*FROM_CSR.split(), "--certificate-pem-outfile", outfile],
        stderr_contains=f"Unable to write to file: {outfile}",
        expected_rc=252,
    )
    assert result.calls == ()
