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

import contextlib
import os
import sys
import tempfile
import zipfile
from datetime import datetime

from awscli.compat import ZIP_COMPRESSION_MODE, BytesIO
from awscli.customizations.codedeploy.utils import validate_s3_location
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError
from botocore.exceptions import ClientError

ONE_MB = 1 << 20
MULTIPART_LIMIT = 6 * ONE_MB


class Push(BasicCommand):
    NAME = 'push'

    DESCRIPTION = (
        'Bundles and uploads to Amazon Simple Storage Service (Amazon S3) an '
        'application revision, which is a zip archive file that contains '
        'deployable content and an accompanying Application Specification '
        'file (AppSpec file). If the upload is successful, a message is '
        'returned that describes how to call the create-deployment command to '
        'deploy the application revision from Amazon S3 to target Amazon '
        'Elastic Compute Cloud (Amazon EC2) instances.'
    )

    ARG_TABLE = [
        {
            'name': 'application-name',
            'synopsis': '--application-name <app-name>',
            'required': True,
            'help_text': (
                'Required. The name of the AWS CodeDeploy application to be '
                'associated with the application revision.'
            ),
        },
        {
            'name': 's3-location',
            'synopsis': '--s3-location s3://<bucket>/<key>',
            'required': True,
            'help_text': (
                r'Required. Information about the location of the application '
                r'revision to be uploaded to Amazon S3. You must specify both '
                r'a bucket and a key that represent the Amazon S3 bucket name '
                r'and the object key name. Content will be zipped before '
                r'uploading. Use the format s3://\<bucket\>/\<key\>'
            ),
        },
        {
            'name': 'ignore-hidden-files',
            'action': 'store_true',
            'default': False,
            'group_name': 'ignore-hidden-files',
            'help_text': (
                'Optional. Set the --ignore-hidden-files flag to not bundle '
                'and upload hidden files to Amazon S3; otherwise, set the '
                '--no-ignore-hidden-files flag (the default) to bundle and '
                'upload hidden files to Amazon S3.'
            ),
        },
        {
            'name': 'no-ignore-hidden-files',
            'action': 'store_true',
            'default': False,
            'group_name': 'ignore-hidden-files',
        },
        {
            'name': 'source',
            'synopsis': '--source <path>',
            'default': '.',
            'help_text': (
                'Optional. The location of the deployable content and the '
                'accompanying AppSpec file on the development machine to be '
                'zipped and uploaded to Amazon S3. If not specified, the '
                'current directory is used.'
            ),
        },
        {
            'name': 'description',
            'synopsis': '--description <description>',
            'help_text': (
                'Optional. A comment that summarizes the application '
                'revision. If not specified, the default string "Uploaded by '
                'AWS CLI \'time\' UTC" is used, where \'time\' is the current '
                'system time in Coordinated Universal Time (UTC).'
            ),
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        self._validate_args(parsed_args)
        self.codedeploy = self._session.create_client(
            'codedeploy',
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )
        self.s3 = self._session.create_client(
            's3', region_name=parsed_globals.region
        )
        self._push(parsed_args)
        return 0

    def _validate_args(self, parsed_args):
        validate_s3_location(parsed_args, 's3_location')
        if (
            parsed_args.ignore_hidden_files
            and parsed_args.no_ignore_hidden_files
        ):
            raise ParamValidationError(
                'You cannot specify both --ignore-hidden-files and '
                '--no-ignore-hidden-files.'
            )
        if not parsed_args.description:
            parsed_args.description = f'Uploaded by AWS CLI {datetime.utcnow().isoformat()} UTC'

    def _push(self, params):
        with self._compress(
            params.source, params.ignore_hidden_files
        ) as bundle:
            try:
                upload_response = self._upload_to_s3(params, bundle)
                params.eTag = upload_response['ETag'].replace('"', "")
                if 'VersionId' in upload_response:
                    params.version = upload_response['VersionId']
            except Exception as e:
                raise RuntimeError(
                    f'Failed to upload \'{params.source}\' to \'{params.s3_location}\': {str(e)}'
                )
        self._register_revision(params)

        if 'version' in params:
            version_string = f',version={params.version}'
        else:
            version_string = ''
        s3location_string = (
            f'--s3-location bucket={params.bucket},key={params.key},'
            f'bundleType=zip,eTag={params.eTag}{version_string}'
        )
        sys.stdout.write(
            'To deploy with this revision, run:\n'
            'aws deploy create-deployment '
            f'--application-name {params.application_name} {s3location_string} '
            '--deployment-group-name <deployment-group-name> '
            '--deployment-config-name <deployment-config-name> '
            '--description <description>\n'
        )

    @contextlib.contextmanager
    def _compress(self, source, ignore_hidden_files=False):
        source_path = os.path.abspath(source)
        appspec_path = os.path.sep.join([source_path, 'appspec.yml'])
        with tempfile.TemporaryFile('w+b') as tf:
            zf = zipfile.ZipFile(tf, 'w', allowZip64=True)
            # Using 'try'/'finally' instead of 'with' statement since ZipFile
            # does not have support context manager in Python 2.6.
            try:
                contains_appspec = False
                for root, dirs, files in os.walk(source, topdown=True):
                    if ignore_hidden_files:
                        files = [fn for fn in files if not fn.startswith('.')]
                        dirs[:] = [dn for dn in dirs if not dn.startswith('.')]
                    for fn in files:
                        filename = os.path.join(root, fn)
                        filename = os.path.abspath(filename)
                        arcname = filename[len(source_path) + 1 :]
                        if filename == appspec_path:
                            contains_appspec = True
                        zf.write(filename, arcname, ZIP_COMPRESSION_MODE)
                if not contains_appspec:
                    raise RuntimeError(
                        f'{appspec_path} was not found'
                    )
            finally:
                zf.close()
            yield tf

    def _upload_to_s3(self, params, bundle):
        size_remaining = self._bundle_size(bundle)
        if size_remaining < MULTIPART_LIMIT:
            return self.s3.put_object(
                Bucket=params.bucket, Key=params.key, Body=bundle
            )
        else:
            return self._multipart_upload_to_s3(params, bundle, size_remaining)

    def _bundle_size(self, bundle):
        bundle.seek(0, 2)
        size = bundle.tell()
        bundle.seek(0)
        return size

    def _multipart_upload_to_s3(self, params, bundle, size_remaining):
        create_response = self.s3.create_multipart_upload(
            Bucket=params.bucket, Key=params.key
        )
        upload_id = create_response['UploadId']
        try:
            part_num = 1
            multipart_list = []
            bundle.seek(0)
            while size_remaining > 0:
                data = bundle.read(MULTIPART_LIMIT)
                upload_response = self.s3.upload_part(
                    Bucket=params.bucket,
                    Key=params.key,
                    UploadId=upload_id,
                    PartNumber=part_num,
                    Body=BytesIO(data),
                )
                multipart_list.append(
                    {'PartNumber': part_num, 'ETag': upload_response['ETag']}
                )
                part_num += 1
                size_remaining -= len(data)
            return self.s3.complete_multipart_upload(
                Bucket=params.bucket,
                Key=params.key,
                UploadId=upload_id,
                MultipartUpload={'Parts': multipart_list},
            )
        except ClientError as e:
            self.s3.abort_multipart_upload(
                Bucket=params.bucket, Key=params.key, UploadId=upload_id
            )
            raise e

    def _register_revision(self, params):
        revision = {
            'revisionType': 'S3',
            's3Location': {
                'bucket': params.bucket,
                'key': params.key,
                'bundleType': 'zip',
                'eTag': params.eTag,
            },
        }
        if 'version' in params:
            revision['s3Location']['version'] = params.version
        self.codedeploy.register_application_revision(
            applicationName=params.application_name,
            revision=revision,
            description=params.description,
        )
