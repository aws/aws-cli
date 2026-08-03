import botocore
from botocore.compat import HAS_CRT
from tests import requires_crt
from tests.unit.auth.test_signers import (
    TestS3SigV4Auth,
    TestSigV4Presign,
    TestSigV4Resign,
)


@requires_crt()
def test_crt_supported_auth_types_list():
    # The list CRT_SUPPORTED_AUTH_TYPES is available even when awscrt is not
    # installed. Its entries must always match the keys of the
    # CRT_AUTH_TYPE_MAPS dict which is only available when CRT is installed.
    with_crt_list = set(botocore.crt.CRT_SUPPORTED_AUTH_TYPES)
    without_crt_list = set(botocore.crt.auth.CRT_AUTH_TYPE_MAPS.keys())
    assert with_crt_list == without_crt_list


@requires_crt()
class TestCrtS3SigV4Auth(TestS3SigV4Auth):
    # Repeat TestS3SigV4Auth tests, but using CRT signer
    if HAS_CRT:
        AuthClass = botocore.crt.auth.CrtS3SigV4Auth


@requires_crt()
class TestCrtSigV4Resign(TestSigV4Resign):
    # Run same tests against CRT auth
    if HAS_CRT:
        AuthClass = botocore.crt.auth.CrtSigV4Auth


@requires_crt()
class TestCrtSigV4Presign(TestSigV4Presign):
    # Run same tests against CRT auth
    if HAS_CRT:
        AuthClass = botocore.crt.auth.CrtSigV4QueryAuth
