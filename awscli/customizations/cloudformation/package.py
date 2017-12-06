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

#import random
#import string
import uuid

import json

from botocore.client import Config
from botocore.exceptions import ClientError

from awscli.customizations.cloudformation.artifact_exporter import Template
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3uploader import S3Uploader

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
            'required': False,
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
        }
    ]

    def _does_bucket_exist(self, bucket, s3_client):
        try:
            s3_client.head_bucket(Bucket=bucket)
        except ClientError as e:
            if e.response['Error']['Code'] == 404:
                return False
        
        return True

    def _does_deploy_region_match(self, deploy_region, s3_client):
        # pass
        s3_loc = s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
        return s3_loc == deploy_region

    # ***REMOVED***


    def _run_main(self, parsed_args, parsed_globals):
        region = parsed_globals.region if parsed_globals.region else "us-east-1"
        s3_client = self._session.create_client(
            "s3",
            config=Config(signature_version='s3v4'),
            region_name=region,
            verify=parsed_globals.verify_ssl)

        template_path = parsed_args.template_file
        if not os.path.isfile(template_path):
            raise exceptions.InvalidTemplatePathError(
                template_path=template_path)

        if(parsed_args.s3_bucket is not None):
            bucket = parsed_args.s3_bucket
            if parsed_globals.region == s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]:
                print(
                    "Bucket specified it's on the same region as the deployment. Nothing to do here.")
            else:
                print("Not cool. Bucket it's on a different region")
        else:
            print("Bucket not specified.")
            sts_client = self._session.create_client(
                "sts",
                config=Config(signature_version='s3v4'),
                verify=parsed_globals.verify_ssl
            )
            bucket = "sam-{region}{account}".format(
                account=str(sts_client.get_caller_identity()["Account"]),
                region=region
            )
            #If they have already created the bucket, we need to find it out.
            try:
                print("Checking bucket -> ", bucket)
                s3_client.head_bucket(Bucket=bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    print("Bucket doesn't exist")
                    # print("Unexpected error:", sys.exc_info())
                    #region = parsed_globals.region if parsed_globals.region else "EU"
                    #print(region)
                    if parsed_globals.region:
                        s3_client.create_bucket(
                            Bucket=str(bucket),
                            CreateBucketConfiguration={
                                'LocationConstraint': str(region)}
                        )
                    else:
                        s3_client.create_bucket(
                            Bucket=str(bucket)
                        )
                    # continue
        # region = parsed_globals.region if parsed_globals.region else "us-east-1"
        # s3_client = self._session.create_client(
        #     "s3",
        #     config=Config(signature_version='s3v4'),
        #     region_name=region,
        #     verify=parsed_globals.verify_ssl)

        # template_path = parsed_args.template_file
        # if not os.path.isfile(template_path):
        #     raise exceptions.InvalidTemplatePathError(
        #             template_path=template_path)
 
        # if(parsed_args.s3_bucket is not None):
        #     bucket = parsed_args.s3_bucket
        #     if not self._does_bucket_exist(bucket, s3_client):
        #         raise exceptions.PackageFailedInvalidBucketError(
        #             bucket_region=s3_loc
        #         )

        #     if not _does_deploy_region_match(region, s3_client):
        #         raise exceptions.PackageFailedRegionMismatchError(
        #             bucket_region=s3_loc,
        #             deploy_region=deploy_region
        #         )

        #     raise Exception("Tested ;)")
        # else:
        #     print("Bucket not specified.")
        #     sts_client = self._session.create_client(
        #         "sts",
        #         config=Config(signature_version='s3v4'),
        #         verify=parsed_globals.verify_ssl
        #     )
        #     bucket="sam-{region}{hash}".format(
        #         hash=str(hash((sts_client.get_caller_identity()['UserId'].split(':')[0]))),
        #         region=region
        #     )


        #     print("Name of the bucket to be created: ", bucket)            
        #     #region = parsed_globals.region if parsed_globals.region else "EU"
        #     #print(region)
        #     if parsed_globals.region:     
        #         response = s3_client.create_bucket(
        #             Bucket=str(bucket),
        #             CreateBucketConfiguration={'LocationConstraint':str(region)}
        #         )
        #     else:
        #         print("we didn't add region")
        #         response = s3_client.create_bucket(
        #             Bucket=str(bucket)
        #         )        

        #     print(response)


        self.s3_uploader = S3Uploader(s3_client,
                                      bucket,
                                      parsed_globals.region,
                                      parsed_args.s3_prefix,
                                      parsed_args.kms_key_id,
                                      parsed_args.force_upload)

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
