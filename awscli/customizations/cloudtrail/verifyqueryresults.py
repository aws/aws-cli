import base64
import binascii
import json
import hashlib
import sys
from abc import ABC, abstractmethod
from os import path

import cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_der_public_key
from awscli.customizations.exceptions import ParamValidationError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.cloudtrail.utils import parse_date, PublicKeyProvider

SIGN_FILE_NAME = "result_sign.json"


def format_prefix(prefix):
    """
    Make prefix end with '/'

    :rtype: string
    :return: Return the prefix that end with '/'
    """
    if prefix == "" or prefix[-1] == "/":
        return prefix
    else:
        return prefix + "/"


class ValidationError(Exception):
    """Exception raised when something wrong in the validation process."""

    def __init__(self, message):
        message = f"ValidationError: {message}"
        super().__init__(message)


class InformationCollectionError(ValueError):
    """Exception raised when fail to collect required information."""

    def __init__(self, message):
        message = f"InformationCollectionError: {message}"
        super().__init__(message)


class Sha256RsaSignatureValidator:
    """
    Validates SHA256withRSA signed signature.
    """

    def validate(self, public_key_base64, sign_file):
        """Validates the signature with public key.

        Throws a ValidationError when the signature is invalid.

        :type public_key_base64: string
        :param public_key_base64: Public key bytes in base 64.
        :type sign_file: dict
        :param sign_file: Dict of sign file data returned when JSON
            decoding a manifest.
        """
        try:
            public_key = self._load_public_key(public_key_base64)
            signature_bytes = binascii.unhexlify(sign_file["hashSignature"])
            hashing = hashes.SHA256()
            public_key.verify(
                signature_bytes,
                self._create_string_to_sign(sign_file),
                PKCS1v15(),
                hashing,
            )
        except cryptography.exceptions.InvalidSignature:
            raise ValidationError("Invalid signature in sign file")

    def _create_string_to_sign(self, sign_file):
        hash_list = []
        for file_info in sign_file["files"]:
            hash_list.append(file_info["fileHashValue"])

        string_to_sign = " ".join(hash_list)
        return string_to_sign.encode()

    def _load_public_key(self, public_key_base64):
        try:
            decoded_key = base64.b64decode(public_key_base64)
            return load_der_public_key(decoded_key, default_backend())
        except ValueError:
            raise ValidationError(
                f"Sign file invalid, unable to load PKCS #1 key: {public_key_base64}"
            )


class BaseSignFileProvider(ABC):
    @abstractmethod
    def provide_sign_file(self):
        """
        Get the sign file and query execute time.

        :rtype: string, string
        :return: Return the sign file and dateTime of the query export time.
        """
        pass

    def _load_sign_file(self, sign_file_str):
        try:
            return json.loads(sign_file_str)
        except json.JSONDecodeError as e:
            raise InformationCollectionError(
                f"Unable to load result_sign.json file, due to {str(e)}"
            )


class LocalSignFileProvider(BaseSignFileProvider):
    def __init__(
        self,
        local_path_prefix=None,
    ):
        self._local_path_prefix = local_path_prefix

    def provide_sign_file(self):
        with open(path.join(self._local_path_prefix, SIGN_FILE_NAME)) as f:
            sign_file = self._load_sign_file(f.read())

        return sign_file


class S3SignFileProvider(BaseSignFileProvider):
    def __init__(
        self,
        s3_client=None,
        s3_bucket=None,
        s3_path_prefix=None,
    ):
        self._s3_client = s3_client
        self._s3_bucket = s3_bucket
        self._s3_path_prefix = s3_path_prefix

    def provide_sign_file(self):
        sign_file_byte = self._s3_client.get_object(
            Bucket=self._s3_bucket, Key=self._s3_path_prefix + SIGN_FILE_NAME
        )["Body"].read()
        sign_file = self._load_sign_file(sign_file_byte.decode("utf-8"))

        return sign_file


class BaseExportFilesHashValidator(ABC):
    @abstractmethod
    def validate_export_files(self, sign_file):
        """Validates all the export files in the query.

        Throws a ValidationError when export file's hash value is inconsistent
        with the hash value recorded in sign file.

        :type sign_file: dict
        :param sign_file: Dict of sign file data returned when JSON
            decoding a manifest.
        """
        pass

    def _validate_hash_value(self, read_stream, file_name, expected_hash):
        rolling_hash = hashlib.sha256()
        for chunk in iter(lambda: read_stream.read(2048), b""):
            rolling_hash.update(chunk)
        computed_hash = rolling_hash.hexdigest()
        if computed_hash != expected_hash:
            raise ValidationError(
                f"File {file_name} has inconsistent hash value with hash value recorded"
                f" in sign file, hash value in sign file is {expected_hash} ,"
                f" but get {computed_hash}"
            )

    def _validate_number_of_files(self, sign_file):
        try:
            if len(sign_file["files"]) == 0:
                raise ValidationError("No export file was found in sign file.")
        except TypeError:
            raise ValidationError("Invalid sign file provided.")


class S3ExportFilesHashValidator(BaseExportFilesHashValidator):
    def __init__(
        self,
        s3_client=None,
        s3_bucket=None,
        s3_path_prefix=None,
    ):

        self._s3_client = s3_client
        self._s3_bucket = s3_bucket
        self._s3_path_prefix = s3_path_prefix

    def validate_export_files(self, sign_file):
        self._validate_number_of_files(sign_file)

        for file_info in sign_file["files"]:
            key = self._s3_path_prefix + file_info["fileName"]
            response = self._s3_client.get_object(Bucket=self._s3_bucket, Key=key)
            self._validate_hash_value(
                response["Body"], file_info["fileName"], file_info["fileHashValue"]
            )


class LocalExportFilesHashValidator(BaseExportFilesHashValidator):
    def __init__(
        self,
        local_path_prefix=None,
    ):
        self.local_path_prefix = local_path_prefix

    def validate_export_files(self, sign_file):
        self._validate_number_of_files(sign_file)

        for file_info in sign_file["files"]:
            with open(
                path.join(self.local_path_prefix, file_info["fileName"]), "rb"
            ) as export_file:
                self._validate_hash_value(
                    export_file, file_info["fileName"], file_info["fileHashValue"]
                )


class CloudTrailVerifyQueryResult(BasicCommand):
    """
    Validates export files output from a CloudTrail Lake query.
    """

    NAME = "verify-query-results"
    DESCRIPTION = """
    Validates CloudTrail Lake query's export files.

    This command uses the query export and sign file delivered to you to
    perform the validation.

    The AWS CLI allows you to detect the following types of changes:

    - Modification or deletion of CloudTrail Lake query's export files.

    To validate export files with the AWS CLI, the following preconditions must
    be met:

    - You must have online connectivity to AWS.
    - You must put the sign file and export file in the specified path prefix
    - You must not rename the delivered export file and sign file
    - For validate export files from S3: (1) You must have read access to the
      S3 bucket that contains the sign and export file. (2) The digest and log
      files must not have been moved from the original S3 location where
      CloudTrail delivered them.

    .. note::
        For verify export file from S3, this command requires that the user or 
        role executing the command has permission to call GetObject, and
        GetBucketLocation for the bucket that store the export file.
    """

    ARG_TABLE = [
        {
            "name": "local-export-path",
            "required": False,
            "cli_type_name": "string",
            "help_text": "Specifies the local directory of export and sign file,"
            " e.g. /local/path/to/export/file/ ",
        },
        {
            "name": "s3-bucket",
            "required": False,
            "cli_type_name": "string",
            "help_text": "Specifies the S3 bucket name that store the query "
            "result and sign file "
            "This parameter can not coexist with local-export-path.",
        },
        {
            "name": "s3-prefix",
            "required": False,
            "cli_type_name": "string",
            "help_text": "Specifies the S3 path of the S3 folder that contain"
            "export and sign file, e.g. bucket_name/s3/path/ . "
            "This parameter can not coexist with local-export-path. If the "
            "files located in s3 bucket root directory, then no need to "
            "provide this parameter.",
        },
    ]

    def __init__(self, session):
        super().__init__(session)
        self._local_export_path = None
        self._s3_prefix = None
        self._s3_bucket = None
        self._is_from_s3 = None
        self._return_code = 255

        self._s3_client_provider = None
        self._cloudtrail_client = None
        self._source_region = None

    def _run_main(self, args, parsed_globals):
        self._call(args, parsed_globals)
        return self._return_code

    def handle_args(self, args):
        if not args.local_export_path and not args.s3_bucket:
            raise ParamValidationError(
                "Require parameter --s3-bucket or --local-export-path."
            )
        if args.local_export_path and (args.s3_bucket or args.s3_prefix):
            raise ParamValidationError(
                "Parameter --local-export-path can not be specified with"
                " parameter --s3-bucket nor --s3-prefix."
            )

        if args.local_export_path:
            self._is_from_s3 = False
            self._local_export_path = args.local_export_path
        else:
            self._is_from_s3 = True
            self._s3_prefix = (
                "" if args.s3_prefix is None else format_prefix(args.s3_prefix)
            )
            self._s3_bucket = args.s3_bucket

    def setup_services(self, parsed_globals):
        self._source_region = parsed_globals.region
        client_args = {
            "region_name": parsed_globals.region,
            "verify": parsed_globals.verify_ssl,
        }

        if parsed_globals.endpoint_url is not None:
            client_args["endpoint_url"] = parsed_globals.endpoint_url
        self._cloudtrail_client = self._session.create_client(
            "cloudtrail", **client_args
        )

    def _call(self, args, parsed_globals):
        self.handle_args(args)
        self.setup_services(parsed_globals)
        (
            public_key_provider,
            signature_validator,
            sign_file_provider,
            hash_validator,
        ) = self._initialize_components(
            self._is_from_s3,
            self._cloudtrail_client,
            self._s3_bucket,
            self._s3_prefix,
            self._local_export_path,
        )

        sign_file = sign_file_provider.provide_sign_file()
        hash_validator.validate_export_files(sign_file)

        public_key = public_key_provider.get_public_key(
            parse_date(sign_file["queryCompleteTime"]),
            sign_file["publicKeyFingerprint"],
        )
        signature_validator.validate(public_key, sign_file)
        self._return_code = 0
        sys.stdout.write("Successfully validated sign and query result files\n")

    def _initialize_components(
        self,
        is_from_s3,
        cloudtrail_client,
        s3_bucket=None,
        s3_prefix=None,
        local_export_path=None,
    ):
        public_key_provider = PublicKeyProvider(cloudtrail_client)
        signature_validator = Sha256RsaSignatureValidator()
        if is_from_s3:
            s3_client = self._session.create_client("s3", self._source_region)
            sign_file_provider = S3SignFileProvider(
                s3_client=s3_client,
                s3_bucket=s3_bucket,
                s3_path_prefix=s3_prefix,
            )
            export_file_hash_validator = S3ExportFilesHashValidator(
                s3_client=s3_client,
                s3_bucket=s3_bucket,
                s3_path_prefix=s3_prefix,
            )
        else:
            sign_file_provider = LocalSignFileProvider(
                local_path_prefix=local_export_path
            )
            export_file_hash_validator = LocalExportFilesHashValidator(
                local_path_prefix=local_export_path
            )

        return (
            public_key_provider,
            signature_validator,
            sign_file_provider,
            export_file_hash_validator,
        )
