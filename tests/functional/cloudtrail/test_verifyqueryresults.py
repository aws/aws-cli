from io import BytesIO
import json
import binascii
import copy
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

from awscli.testutils import BaseAWSCommandParamsTest
from tests import PublicPrivateKeyLoader

SAMPLE_PUBLIC_KEY_FINGERPRINT = "67b9fa73676d86966b449dd677850753"
SAMPLE_PUBLIC_KEY = (
    "MIIBCgKCAQEA1OxVzcylHnxhysU41BcHucQn47bywceJEPkze53R"
    "ZUaYtvTAXYf0ONbdk/yQ8c5Bq6l5nL0qjT1UNhVfccCsTaToL58w"
    "PePg9U29D+MtiQXz6yecW7Rzs5rP5i4EU2YDPoYaphIVowYZjkHy"
    "C72L/2lQ/Q5rSotIjUdCq6Wv6i7bFHLiCNtgP95xfL9pxytAyGdC"
    "zHDBJb/H60x7q/wqO6/HaZI38aY7piHqazd2vpaNxPShHyvpdR0P"
    "29tNFxo+5V4VVW2/QC1/QLTLLAzQNiO+ZOpsHa8rgYmPv0YI4sFA"
    "9vFhHyUdh9skopO7Jg/gAjAdtzuLCnXpfuwQ/+EXnQIDAQAB"
)
SAMPLE_EXPORT_FILE = "# Execution Time: 2022-05-24T21:51:51.723951Z "
SAMPLE_HASH_VALUE = (
    "3b9c358f36f0a31b6ad3e14f309c7cf198ac9246e8316f9ce543" "d5b19ac02b80"
)
SAMPLE_SIGNING_FILE = {
    "region": "us-east-1",
    "files": [{"fileHashValue": SAMPLE_HASH_VALUE, "fileName": "result_1.csv.gz"}],
    "hashAlgorithm": "SHA-256",
    "publicKeyFingerprint": "fingerprint",
    "signatureAlgorithm": "SHA256withRSA",
    "hashSignature": "signature",
    "queryCompleteTime": "2022-05-10T22:06:30Z",
}

SAMPLE_S3_BUCKET_NAME = "lake-bucket-name"
SAMPLE_S3_EXPORT_FILE_PREFIX = "lake-export-prefix/"


def get_private_key_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "test_resource",
        "sample_private_key.pem",
    )


class TestVerifyQueryResults(BaseAWSCommandParamsTest):
    def test_get_file_form_s3_happy_case(self):
        (
            public_key,
            private_key,
        ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
            get_private_key_path()
        )

        sign_file = copy.deepcopy(SAMPLE_SIGNING_FILE)
        signature = private_key.sign(
            SAMPLE_HASH_VALUE.encode(), PKCS1v15(), hashes.SHA256()
        )
        sign_file["hashSignature"] = binascii.hexlify(signature).decode()

        self.parsed_responses = [
            {"Body": BytesIO(json.dumps(sign_file).encode("utf-8"))},
            {"Body": BytesIO(b"file")},
            {"PublicKeyList": [{"Fingerprint": "fingerprint", "Value": public_key}]},
        ]

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --s3-bucket={SAMPLE_S3_BUCKET_NAME}"
            f" --s3-prefix={SAMPLE_S3_EXPORT_FILE_PREFIX} "
        )

        self.assertIn("Successfully validated sign and query result files\n", stdout)
        self.assertEqual(self.operations_called[0][0].name, "GetObject")
        self.assertEqual(self.operations_called[0][1]["Bucket"], SAMPLE_S3_BUCKET_NAME)
        self.assertEqual(
            self.operations_called[0][1]["Key"], "lake-export-prefix/result_sign.json"
        )

        self.assertEqual(self.operations_called[1][0].name, "GetObject")
        self.assertEqual(self.operations_called[1][1]["Bucket"], SAMPLE_S3_BUCKET_NAME)
        self.assertEqual(
            self.operations_called[1][1]["Key"], "lake-export-prefix/result_1.csv.gz"
        )

        self.assertEqual(self.operations_called[2][0].name, "ListPublicKeys")

    def test_get_file_form_s3_invalid_signature(self):
        sign_file = copy.deepcopy(SAMPLE_SIGNING_FILE)
        (
            public_key,
            private_key,
        ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
            get_private_key_path()
        )
        signature = private_key.sign(b"123", PKCS1v15(), hashes.SHA256())
        sign_file["hashSignature"] = binascii.hexlify(signature).decode()

        self.parsed_responses = [
            {"Body": BytesIO(json.dumps(sign_file).encode("utf-8"))},
            {"Body": BytesIO(b"file")},
            {"PublicKeyList": [{"Fingerprint": "fingerprint", "Value": public_key}]},
        ]

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --s3-bucket={SAMPLE_S3_BUCKET_NAME}"
            f" --s3-prefix={SAMPLE_S3_EXPORT_FILE_PREFIX} ",
            255,
        )
        self.assertIn("Invalid signature in sign file", stderr)

    def test_get_file_form_s3_invalid_sign_file(self):
        (
            public_key,
            private_key,
        ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
            get_private_key_path()
        )
        self.parsed_responses = [
            {"Body": BytesIO(b"123")},
            {"Body": BytesIO(b"file")},
            {"PublicKeyList": [{"Fingerprint": "fingerprint", "Value": public_key}]},
        ]

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --s3-bucket={SAMPLE_S3_BUCKET_NAME}"
            f" --s3-prefix={SAMPLE_S3_EXPORT_FILE_PREFIX} "
            f" --endpoint-url=https://testurl/ ",
            255,
        )
        self.assertIn("Invalid sign file provided", stderr)

        self.assertEqual(self.operations_called[0][0].name, "GetObject")
        self.assertEqual(len(self.operations_called), 1)

        self.assertNotIn("testurl", self.last_request_dict["url"])

    def test_invalid_parameter_both_empty(self):
        stdout, stderr, rc = self.run_cmd("cloudtrail verify-query-results ", 252)
        self.assertIn("Require parameter --s3-bucket or --local-export-path.", stderr)
        self.assertEqual(len(self.operations_called), 0)

    def test_invalid_parameter_both_provided(self):
        stdout, stderr, rc = self.run_cmd(
            "cloudtrail verify-query-results "
            "--s3-bucket=test-bucket "
            "--local-export-path=/test/",
            252,
        )
        self.assertIn(
            "Parameter --local-export-path can not be specified with parameter"
            " --s3-bucket nor --s3-prefix.",
            stderr,
        )
        self.assertEqual(len(self.operations_called), 0)

    def test_get_file_form_s3_incorrect_hash_value(self):
        sign_file = copy.deepcopy(SAMPLE_SIGNING_FILE)
        (
            public_key,
            private_key,
        ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
            get_private_key_path()
        )
        signature = private_key.sign(
            SAMPLE_HASH_VALUE.encode(), PKCS1v15(), hashes.SHA256()
        )
        sign_file["hashSignature"] = binascii.hexlify(signature).decode()

        self.parsed_responses = [
            {"Body": BytesIO(json.dumps(sign_file).encode("utf-8"))},
            {"Body": BytesIO(b"123")},
            {"PublicKeyList": [{"Fingerprint": "fingerprint", "Value": public_key}]},
        ]

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --s3-bucket={SAMPLE_S3_BUCKET_NAME}"
            f" --s3-prefix={SAMPLE_S3_EXPORT_FILE_PREFIX} ",
            255,
        )
        self.assertIn("has inconsistent hash value with hash value recorded", stderr)

        self.assertEqual(self.operations_called[0][0].name, "GetObject")
        self.assertEqual(self.operations_called[1][0].name, "GetObject")
        self.assertEqual(len(self.operations_called), 2)

    def test_get_file_form_local_form_local_success(self):
        self.parsed_responses = [
            {
                "PublicKeyList": [
                    {
                        "Fingerprint": SAMPLE_PUBLIC_KEY_FINGERPRINT,
                        "Value": SAMPLE_PUBLIC_KEY,
                    }
                ]
            }
        ]

        current_dir = os.path.dirname(os.path.realpath(__file__))
        local_export_file_path = os.path.join(current_dir, "test_resource")

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --local-export-path={local_export_file_path}"
        )
        self.assertIn("Successfully validated sign and query result files\n", stdout)

        self.assertEqual(self.operations_called[0][0].name, "ListPublicKeys")
        self.assertEqual(len(self.operations_called), 1)

    def test_override_endpoint_url(self):
        self.parsed_responses = [
            {
                "PublicKeyList": [
                    {
                        "Fingerprint": SAMPLE_PUBLIC_KEY_FINGERPRINT,
                        "Value": SAMPLE_PUBLIC_KEY,
                    }
                ]
            }
        ]

        current_dir = os.path.dirname(os.path.realpath(__file__))
        local_export_file_path = os.path.join(current_dir, "test_resource")

        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail verify-query-results --local-export-path={local_export_file_path}"
            f" --endpoint-url=https://testurl/ "
        )

        self.assertIn("Successfully validated sign and query result files\n", stdout)
        self.assertEqual(self.last_request_dict["url"], "https://testurl/")
