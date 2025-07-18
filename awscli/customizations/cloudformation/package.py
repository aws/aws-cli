# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import os
import logging
import sys

import json

from botocore.client import Config

from awscli.customizations.cloudformation.artifact_exporter import Template
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3uploader import S3Uploader
from awscli.utils import create_nested_client

LOG = logging.getLogger(__name__)


class PackageCommand(BasicCommand):

    MSG_PACKAGED_TEMPLATE_WRITTEN = (
        "Successfully packaged artifacts and wrote output template "
        "to file {output_file_name}."
        "\n"
        "Execute the following command to deploy the packaged template"
        "\n"
        "aws cloudformation deploy --template-file {output_file_path} "
        "--stack-name <YOUR STACK NAME>"
        "\n")

    NAME = "package"

    DESCRIPTION = BasicCommand.FROM_FILE("cloudformation",
                                         "_package_description.rst")

    ARG_TABLE = [
        {
            'name': 'template-file',
            'required': True,
            'help_text': (
                'The path where your AWS CloudFormation'
                ' template is located.'
            )
        },

        {
            'name': 's3-bucket',
            'required': True,
            'help_text': (
                'The name of the S3 bucket where this command uploads'
                ' the artifacts that are referenced in your template.'
            )
        },

        {
            'name': 's3-prefix',
            'help_text': (
                'A prefix name that the command adds to the'
                ' artifacts\' name when it uploads them to the S3 bucket.'
                ' The prefix name is a path name (folder name) for'
                ' the S3 bucket.'
            )
        },

        {
            'name': 'kms-key-id',
            'help_text': (
                'The ID of an AWS KMS key that the command uses'
                ' to encrypt artifacts that are at rest in the S3 bucket.'
            )
        },

        {
            "name": "output-template-file",
            "help_text": (
                "The path to the file where the command writes the"
                " output AWS CloudFormation template. If you don't specify"
                " a path, the command writes the template to the standard"
                " output."
            )
        },

        {
            "name": "use-json",
            "action": "store_true",
            "help_text": (
                "Indicates whether to use JSON as the format for the output AWS"
                " CloudFormation template. YAML is used by default."
            )
        },

        {
            "name": "force-upload",
            "action": "store_true",
            "help_text": (
                'Indicates whether to override existing files in the S3 bucket.'
                ' Specify this flag to upload artifacts even if they '
                ' match existing artifacts in the S3 bucket.'
            )
        },
        {
            "name": "metadata",
            "cli_type_name": "map",
            "schema": {
                "type": "map",
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            "help_text": "A map of metadata to attach to *ALL* the artifacts that"
            " are referenced in your template."
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        s3_client = create_nested_client(
            self._session, "s3",
            config=Config(signature_version='s3v4'),
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl)

        template_path = parsed_args.template_file
        if not os.path.isfile(template_path):
            raise exceptions.InvalidTemplatePathError(
                    template_path=template_path)

        bucket = parsed_args.s3_bucket

        self.s3_uploader = S3Uploader(s3_client,
                                      bucket,
                                      parsed_args.s3_prefix,
                                      parsed_args.kms_key_id,
                                      parsed_args.force_upload)
        # attach the given metadata to the artifacts to be uploaded
        self.s3_uploader.artifact_metadata = parsed_args.metadata

        output_file = parsed_args.output_template_file
        use_json = parsed_args.use_json
        exported_str = self._export(template_path, use_json)

        sys.stdout.write("\n")
        self.write_output(output_file, exported_str)

        if output_file:
            msg = self.MSG_PACKAGED_TEMPLATE_WRITTEN.format(
                    output_file_name=output_file,
                    output_file_path=os.path.abspath(output_file))
            sys.stdout.write(msg)

        sys.stdout.flush()
        return 0

    def _export(self, template_path, use_json):
        template = Template(template_path, os.getcwd(), self.s3_uploader)
        exported_template = template.export()

        if use_json:
            exported_str = json.dumps(exported_template, indent=4, ensure_ascii=False)
        else:
            exported_str = yaml_dump(exported_template)

        return exported_str

    def write_output(self, output_file_name, data):
        if output_file_name is None:
            sys.stdout.write(data)
            return

        with open(output_file_name, "w") as fp:
            fp.write(data)
