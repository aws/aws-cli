# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import threading
import contextlib
import os
import tempfile
import sys
import zipfile

from s3transfer import S3Transfer

from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3.utils import human_readable_size


class UploadBuildCommand(BasicCommand):
    NAME = 'upload-build'
    DESCRIPTION = 'Upload a new build to AWS GameLift.'
    ARG_TABLE = [
        {'name': 'name', 'required': True,
         'help_text': 'The name of the build'},
        {'name': 'build-version', 'required': True,
         'help_text': 'The version of the build'},
        {'name': 'build-root', 'required': True,
         'help_text':
         'The path to the directory containing the build to upload'},
        {'name': 'operating-system', 'required': False,
         'help_text': 'The operating system the build runs on'}
    ]

    def _run_main(self, args, parsed_globals):
        gamelift_client = self._session.create_client(
            'gamelift', region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        # Validate a build directory
        if not validate_directory(args.build_root):
            sys.stderr.write(
                'Fail to upload %s. '
                'The build root directory is empty or does not exist.\n'
                % (args.build_root)
            )

            return 255
        # Create a build based on the operating system given.
        create_build_kwargs = {
            'Name': args.name,
            'Version': args.build_version
        }
        if args.operating_system:
            create_build_kwargs['OperatingSystem'] = args.operating_system

        response = gamelift_client.create_build(**create_build_kwargs)
        build_id = response['Build']['BuildId']

        # Retrieve a set of credentials and the s3 bucket and key.
        response = gamelift_client.request_upload_credentials(
            BuildId=build_id)
        upload_credentials = response['UploadCredentials']
        bucket = response['StorageLocation']['Bucket']
        key = response['StorageLocation']['Key']

        # Create the S3 Client for uploading the build based on the
        # credentials returned from creating the build.
        access_key = upload_credentials['AccessKeyId']
        secret_key = upload_credentials['SecretAccessKey']
        session_token = upload_credentials['SessionToken']
        s3_client = self._session.create_client(
            's3', aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl
        )

        s3_transfer_mgr = S3Transfer(s3_client)

        try:
            fd, temporary_zipfile = tempfile.mkstemp('%s.zip' % build_id)
            zip_directory(temporary_zipfile, args.build_root)
            s3_transfer_mgr.upload_file(
                temporary_zipfile, bucket, key,
                callback=ProgressPercentage(
                    temporary_zipfile,
                    label='Uploading ' + args.build_root + ':'
                )
            )
        finally:
            os.close(fd)
            os.remove(temporary_zipfile)

        sys.stdout.write(
            'Successfully uploaded %s to AWS GameLift\n'
            'Build ID: %s\n' % (args.build_root, build_id))

        return 0


def zip_directory(zipfile_name, source_root):
    source_root = os.path.abspath(source_root)
    with open(zipfile_name, 'wb') as f:
        zip_file = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED, True)
        with contextlib.closing(zip_file) as zf:
            for root, dirs, files in os.walk(source_root):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(
                        full_path, source_root)
                    zf.write(full_path, relative_path)


def validate_directory(source_root):
    # For Python26 on Windows, passing an empty string equates to the
    # current directory, which is not intended behavior.
    if not source_root:
        return False
    # We walk the root because we want to validate there's at least one file
    # that exists recursively from the root directory
    for path, dirs, files in os.walk(source_root):
        if files:
            return True
    return False


# TODO: Remove this class once available to CLI from s3transfer
# docstring.
class ProgressPercentage(object):
    def __init__(self, filename, label=None):
        self._filename = filename
        self._label = label
        if self._label is None:
            self._label = self._filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            if self._size > 0:
                percentage = (self._seen_so_far / self._size) * 100
                sys.stdout.write(
                    "\r%s  %s / %s  (%.2f%%)" % (
                        self._label, human_readable_size(self._seen_so_far),
                        human_readable_size(self._size), percentage
                    )
                )
                sys.stdout.flush()
