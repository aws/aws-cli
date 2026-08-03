import pytest

import botocore
from tests import FreezeTime, requires_crt
from tests.unit.auth.test_sigv4 import (
    DATE,
    REGION,
    SERVICE,
    SignatureTestCase,
    assert_equal,
    create_request_from_raw_request,
    generate_test_cases,
)


def _test_crt_signature_version_4(test_case):
    test_case = SignatureTestCase(test_case)
    request = create_request_from_raw_request(test_case.raw_request)

    # Use CRT logging to diagnose interim steps (canonical request, etc)
    # import awscrt.io
    # awscrt.io.init_logging(awscrt.io.LogLevel.Trace, 'stdout')
    auth = botocore.crt.auth.CrtSigV4Auth(
        test_case.credentials, SERVICE, REGION
    )
    auth.add_auth(request)
    actual_auth_header = request.headers["Authorization"]
    assert_equal(
        actual_auth_header,
        test_case.authorization_header,
        test_case.raw_request,
        "authheader",
    )


@requires_crt()
@pytest.mark.parametrize("test_case", generate_test_cases())
@FreezeTime(module=botocore.auth.datetime, date=DATE)
def test_signature_version_4(test_case):
    _test_crt_signature_version_4(test_case)
