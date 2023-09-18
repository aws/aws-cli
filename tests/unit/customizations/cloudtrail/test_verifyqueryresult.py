import binascii
import json
import os
from io import BytesIO
import copy

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

from awscli.testutils import mock, unittest
from awscli.customizations.cloudtrail.verifyqueryresults import (
    Sha256RsaSignatureValidator,
    S3SignFileProvider,
    LocalSignFileProvider,
    SIGN_FILE_NAME,
    S3ExportFilesHashValidator,
    LocalExportFilesHashValidator,
    ValidationError,
    InformationCollectionError,
)
from tests import PublicPrivateKeyLoader

s3_bucket = "s3-bucket-name"
S3_PREFIX = "s3/prefix/"
S3_PATH = "s3://{}/{}".format(s3_bucket, S3_PREFIX)
LOCAL_FILE_PREFIX = "/local/prefix/"
SAMPLE_SIGNING_FILE = {
    "region": "us-east-1",
    "files": [
        {
            "fileHashValue": "c147efcfc2d7ea666a9e4f5187b115c90903f0fc896a56d"
            "f9a6ef5d8f3fc9f31",
            "fileName": "result_1.csv.gz",
        }
    ],
    "hashAlgorithm": "SHA-256",
    "signatureAlgorithm": "SHA256withRSA",
    "hashSignature": "hashSignature",
}


def get_private_key_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "test_resource",
        "sample_private_key.pem",
    )


class TestSignFileProvider(unittest.TestCase):
    def test_get_sign_file_from_s3_success(self):
        sign_file_s3_response = {
            "Body": BytesIO(json.dumps(SAMPLE_SIGNING_FILE).encode("utf-8"))
        }

        s3_client = mock.Mock()
        s3_client.get_object.side_effect = [sign_file_s3_response]

        provider = S3SignFileProvider(
            s3_client=s3_client,
            s3_bucket=s3_bucket,
            s3_path_prefix=S3_PREFIX,
        )

        sign_file = provider.provide_sign_file()
        self.assertEqual(sign_file, SAMPLE_SIGNING_FILE)
        s3_client.get_object.assert_has_calls(
            [mock.call(Bucket=s3_bucket, Key=S3_PREFIX + SIGN_FILE_NAME)]
        )

    def test_get_sign_file_from_s3_fail_with_invalid_sign_file(self):
        with self.assertRaises(InformationCollectionError) as context:
            sign_file_s3_response = {"Body": BytesIO(b"{123")}

            s3_client = mock.Mock()
            s3_client.get_object.side_effect = [sign_file_s3_response]

            provider = S3SignFileProvider(
                s3_client=s3_client,
                s3_bucket=s3_bucket,
                s3_path_prefix=S3_PREFIX,
            )

            provider.provide_sign_file()

            self.assertTrue("Unable to load sign file" in context)

    def test_get_sign_file_from_local_success(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        provider = LocalSignFileProvider(
            local_path_prefix=os.path.join(current_dir, "test_resource")
        )
        sign_file = provider.provide_sign_file()
        self.assertEqual(sign_file["hashSignature"], "hashSignature")


class TestExportFilesHashValidator(unittest.TestCase):
    def test_traverse_from_s3_success(self):
        s3_input_file1 = {"Body": BytesIO(b"file1")}

        s3_client = mock.Mock()
        s3_client.get_object.side_effect = [s3_input_file1]

        validator = S3ExportFilesHashValidator(
            s3_client=s3_client,
            s3_bucket=s3_bucket,
            s3_path_prefix=S3_PREFIX,
        )
        validator.validate_export_files(SAMPLE_SIGNING_FILE)

        s3_client.get_object.assert_has_calls(
            [
                mock.call(
                    Bucket=s3_bucket,
                    Key=S3_PREFIX + SAMPLE_SIGNING_FILE["files"][0]["fileName"],
                )
            ]
        )

    def test_traverse_from_local_success(self):

        current_dir = os.path.dirname(os.path.realpath(__file__))
        validator = LocalExportFilesHashValidator(
            local_path_prefix=os.path.join(current_dir, "test_resource")
        )

        validator.validate_export_files(SAMPLE_SIGNING_FILE)

    def test_traverse_from_local_fail_with_hash_error(self):
        sign_file = copy.deepcopy(SAMPLE_SIGNING_FILE)
        sign_file["files"][0]["fileName"] = "result_2.csv.gz"

        current_dir = os.path.dirname(os.path.realpath(__file__))
        with self.assertRaises(ValidationError) as context:
            validator = LocalExportFilesHashValidator(
                local_path_prefix=os.path.join(current_dir, "test_resource")
            )

            validator.validate_export_files(sign_file)

            self.assertTrue("wrong hash value" in context)

    def test_traverse_from_local_no_export_file(self):
        sign_file = copy.deepcopy(SAMPLE_SIGNING_FILE)
        sign_file["files"] = []

        with self.assertRaises(ValidationError) as context:
            validator = LocalExportFilesHashValidator(
                local_path_prefix=LOCAL_FILE_PREFIX
            )

            validator.validate_export_files(sign_file)

            self.assertTrue("No export file was found in sign file" in context)


class TestSha256RSADigestValidator(unittest.TestCase):
    def setUp(self):
        self._sign_file = {
            "region": "us-east-1",
            "files": [
                {"fileHashValue": "fileHashValue1", "fileName": "result_1.csv.gz"},
                {"fileHashValue": "fileHashValue2", "fileName": "result_2.csv.gz"},
            ],
            "hashAlgorithm": "SHA-256",
            "signatureAlgorithm": "SHA256withRSA",
            "hashSignature": "hashSignature",
        }

    def test_validates_digests_success(self):
        (
            public_key,
            private_key,
        ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
            get_private_key_path()
        )
        string_to_sign = "{} {}".format(
            self._sign_file["files"][0]["fileHashValue"],
            self._sign_file["files"][1]["fileHashValue"],
        )

        signature = private_key.sign(
            string_to_sign.encode(), PKCS1v15(), hashes.SHA256()
        )
        self._sign_file["hashSignature"] = binascii.hexlify(signature)
        validator = Sha256RsaSignatureValidator()
        validator.validate(public_key, self._sign_file)

    def test_validates_digests_fail_with_public_key_format(self):
        with self.assertRaises(ValidationError) as context:
            (
                public_key,
                private_key,
            ) = PublicPrivateKeyLoader.load_private_key_and_generate_public_key(
                get_private_key_path()
            )
            string_to_sign = "{} {}".format(
                self._sign_file["files"][0]["fileHashValue"],
                self._sign_file["files"][1]["fileHashValue"],
            )
            signature = private_key.sign(
                string_to_sign.encode(), PKCS1v15(), hashes.SHA256()
            )
            self._sign_file["hashSignature"] = binascii.hexlify(signature)
            validator = Sha256RsaSignatureValidator()
            validator.validate("124", self._sign_file)

            self.assertTrue("unable to load PKCS #1 key" in context)
