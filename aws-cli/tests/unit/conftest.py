import base64
from functools import partial

import pytest
from awscrt.crypto import EC
from botocore.utils import build_dpop_header

EC_PRIVATE_KEY_SEC1_BASE64 = (
    'MHcCAQEEIHjt7c+VnkIkN6RW7QgZPFNLb/9AZEhqSYYMtwrlLb3WoAoGCCqGSM49'
    'AwEHoUQDQgAEv2FjRpMtADMZ4zoZxshV9chEkembgzZnXSUNe+DA8dKqXN/7qTcZ'
    'jYJHKIi+Rn88zUGqCJo3DWF/X+ufVfdU2g=='
)


@pytest.fixture
def private_key():
    """Loads a fixed private key"""
    return EC.new_key_from_der_data(
        base64.b64decode(EC_PRIVATE_KEY_SEC1_BASE64)
    )


@pytest.fixture
def fake_build_dpop_header(private_key):
    """Overrides DPoP signing with frozen key, URI, and UID"""
    return partial(
        build_dpop_header,
        private_key=private_key,
        uri='https://foobar/v1/token',
        uid='uniqueid',
        ts=1760014198,
    )
