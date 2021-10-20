import botocore.crt.auth

from tests.unit.auth.test_signers import (
    TestS3SigV4Auth, TestSigV4Presign, TestSigV4Resign
)


class TestCrtS3SigV4Auth(TestS3SigV4Auth):
    # Repeat TestS3SigV4Auth tests, but using CRT signer
    AuthClass = botocore.crt.auth.CrtS3SigV4Auth


class TestCrtSigV4Resign(TestSigV4Resign):
    AuthClass = botocore.crt.auth.CrtSigV4Auth


class TestCrtSigV4Presign(TestSigV4Presign):
    AuthClass = botocore.crt.auth.CrtSigV4QueryAuth
