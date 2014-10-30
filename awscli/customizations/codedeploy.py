# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import logging
import re
import os
import zipfile
import tempfile
import io
import contextlib
from datetime import datetime

from awscli.customizations.commands import BasicCommand
from awscli.customizations.service import Service
from awscli.customizations import utils


LOG = logging.getLogger(__name__)
ONE_MB = 1 << 20
MULTIPART_LIMIT = 6 * ONE_MB


def initialize(cli):
    """
    The entry point for CodeDeploy high level commands.
    """
    cli.register('building-command-table.main', change_name)
    cli.register('building-command-table.deploy', inject_commands)


def change_name(command_table, session, **kwargs):
    """
    Change all existing 'aws codedeploy' commands to 'aws deploy' commands.
    """
    utils.rename_command(command_table, 'codedeploy', 'deploy')


def inject_commands(command_table, session, **kwargs):
    """
    Inject custom 'aws deploy' commands.
    """
    command_table['push'] = CodeDeployPush(session)


class S3Client:
    """
    S3 helper class.
    """

    def __init__(self, endpoint_args, session):
        self.s3 = Service(
            's3',
            endpoint_args['region_name'],
            session=session
        )

    @staticmethod
    def _bundle_size(bundle):
        bundle.seek(0, 2)
        size = bundle.tell()
        bundle.seek(0)
        return size

    def upload_to_s3(self, parsed_args, bundle):
        size_remaining = self._bundle_size(bundle)
        if size_remaining < MULTIPART_LIMIT:
            return self.s3.PutObject(
                bucket=parsed_args.bucket,
                key=parsed_args.key,
                body=bundle
            )
        else:
            return self._multipart_upload_to_s3(
                parsed_args,
                bundle,
                size_remaining
            )

    def _multipart_upload_to_s3(self, parsed_args, bundle, size_remaining):
        create_response = self.s3.CreateMultipartUpload(
            bucket=parsed_args.bucket,
            key=parsed_args.key
        )
        upload_id = create_response['UploadId']
        try:
            part_num = 1
            multipart_list = []
            bundle.seek(0)
            while size_remaining > 0:
                data = bundle.read(MULTIPART_LIMIT)
                upload_response = self.s3.UploadPart(
                    bucket=parsed_args.bucket,
                    key=parsed_args.key,
                    uploadId=upload_id,
                    partNumber=part_num,
                    body=io.BytesIO(data)
                )
                multipart_list.append({
                    'PartNumber': part_num,
                    'ETag': upload_response['ETag']
                })
                part_num += 1
                size_remaining -= len(data)
            return self.s3.CompleteMultipartUpload(
                bucket=parsed_args.bucket,
                key=parsed_args.key,
                uploadId=upload_id,
                multipartUpload={'Parts': multipart_list}
            )
        except Exception as e:
            self.s3.AbortMultipartUpload(
                bucket=parsed_args.bucket,
                key=parsed_args.key,
                uploadId=upload_id
            )
            raise e


class CodeDeployClient:
    """
    CodeDeploy helper class for defined commands.
    """

    def __init__(self, endpoint_args, session):
        self.codedeploy = Service(
            'codedeploy',
            endpoint_args=endpoint_args,
            session=session
        )

    @staticmethod
    def _get_revision(parsed_args):
        revision = {
            'revisionType' : 'S3',
            's3Location' : {
                'bucket': parsed_args.bucket,
                'key': parsed_args.key,
                'bundleType': 'zip',
                'eTag': parsed_args.eTag
            }
        }
        if 'version' in parsed_args:
            revision['s3Location']['version'] = parsed_args.version
        return revision

    def register_revision(self, parsed_args):
        self.codedeploy.RegisterApplicationRevision(
            applicationName=parsed_args.application_name,
            revision=self._get_revision(parsed_args),
            description=parsed_args.description
        )


class CodeDeployBase(BasicCommand):
    """
    CodeDeployBase Class for all CodeDeploy commands.
    """

    def _run_main(self, parsed_args, parsed_globals):
        endpoint_args = {
            'region_name': parsed_globals.region,
            'endpoint_url': parsed_globals.endpoint_url,
            'verify': parsed_globals.verify_ssl
        }
        self.s3 = S3Client(
            endpoint_args=endpoint_args,
            session=self._session
        )
        self.codedeploy = CodeDeployClient(
            endpoint_args=endpoint_args,
            session=self._session
        )
        self._flatten_args(parsed_args)
        self._call(parsed_args, parsed_globals)

    def _flatten_args(self, parsed_args):
        """
        Subclass command may flatten custom arguments.
        """
        pass

    def _call(self, parsed_args, parsed_globals):
        """
        Subclass command must implement this method.
        """
        raise NotImplementedError("_call")


class CodeDeployPush(CodeDeployBase):
    """
    Compresses the given directory into an archive, and pushes it
    to the specified location in S3 where CodeDeploy would deploy.
    """
    NAME = 'push'

    DESCRIPTION = (
        'Bundles and uploads to Amazon Simple Storage Service (Amazon S3) an '
        'application revision, which is an archive file that contains '
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
            )
        },
        {
            'name': 's3-location',
            'synopsis': '--s3-location s3://<bucket>/<key>',
            'required': True,
            'help_text': (
                'Required. Information about the location of the application '
                'revision to be uploaded to Amazon S3. You must specify both '
                'a bucket and a key that represent the Amazon S3 bucket name '
                'and the object key name. Use the format '
                's3://\<bucket\>/\<key\>'
            )
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
            )
        },
        {
            'name': 'no-ignore-hidden-files',
            'action': 'store_true',
            'default': False,
            'group_name': 'ignore-hidden-files'
        },
        {
            'name': 'source',
            'synopsis': '--source <path>',
            'default': '.',
            'help_text': (
                'Optional. The location of the deployable content and the '
                'accompanying AppSpec file on the development machine to be '
                'bundled and uploaded to Amazon S3. If not specified, the '
                'current directory is used.'
            )
        },
        {
            'name': 'description',
            'synopsis': '--description <description>',
            'help_text': (
                'Optional. A comment that summarizes the application '
                'revision. If not specified, the default string "Uploaded by '
                'AWS CLI \'time\' UTC" is used, where \'time\' is the current '
                'system time in Coordinated Universal Time (UTC).'
            )
        }
    ]

    def _flatten_args(self, parsed_args):
        matcher = re.match(r's3://(.+?)/(.+)', parsed_args.s3_location)
        if matcher:
            parsed_args.bucket = matcher.group(1)
            parsed_args.key = matcher.group(2)
        else:
            raise RuntimeError(
                '--s3-location must specify the Amazon S3 URL format as '
                's3://<bucket>/<key>'
            )
        if parsed_args.ignore_hidden_files \
                and parsed_args.no_ignore_hidden_files:
            raise RuntimeError(
                'You cannot specify both --ignore-hidden-files and '
                '--no-ignore-hidden-files'
            )
        if not parsed_args.description:
            parsed_args.description = (
                'Uploaded by AWS CLI {0} UTC'.format(
                    datetime.utcnow().isoformat()
                )
            )

    def _call(self, parsed_args, parsed_globals):
        with self._compress(
                parsed_args.source,
                parsed_args.ignore_hidden_files
        ) as bundle:
            try:
                upload_response = self.s3.upload_to_s3(parsed_args, bundle)
                parsed_args.eTag = upload_response['ETag']
                if 'VersionId' in upload_response:
                    parsed_args.version = upload_response['VersionId']
            except Exception as e:
                raise RuntimeError(
                    'Failed to upload \'{0}\' to \'{1}\': {2}'.format(
                        parsed_args.source,
                        parsed_args.s3_location,
                        e.message
                    )
                )
        self.codedeploy.register_revision(parsed_args)

        if 'version' in parsed_args:
            version_string = ',"version":"{0}"'.format(parsed_args.version)
        else:
            version_string = ''
        s3location_string = (
            '--revision'
            '{{'
                '"revisionType":"S3",'
                '"s3Location":{{'
                    '"bucket":"{0}",'
                    '"key":"{1}",'
                    '"bundleType":"zip",'
                    '"eTag":{2}{3}'
                '}}'
            '}}'.format(
                parsed_args.bucket,
                parsed_args.key,
                parsed_args.eTag,
                version_string
            )
        )
        output = (
            'To deploy with this revision, run:\n'
            'aws deploy create-deployment '
            '--application-name {0} {1} '
            '--deployment-group-name <deployment-group-name> '
            '--deployment-config-name <deployment-config-name> '
            '--description <description>'.format(
                parsed_args.application_name,
                s3location_string
            )
        )
        print(output)

    @contextlib.contextmanager
    def _compress(self, source, ignore_hidden_files=False):
        source_path = os.path.abspath(source)
        appspec_path = os.path.sep.join([source_path, 'appspec.yml'])
        with tempfile.TemporaryFile() as tf:
            zf = zipfile.ZipFile(tf, 'w')
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
                        arcname = filename[len(source_path) + 1:]
                        if filename == appspec_path:
                            contains_appspec = True
                        zf.write(filename, arcname)
                if not contains_appspec:
                    raise RuntimeError(
                        '{0} was not found'.format(appspec_path)
                    )
            finally:
                zf.close()
            yield tf
