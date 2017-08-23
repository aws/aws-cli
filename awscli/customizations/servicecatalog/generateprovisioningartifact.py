# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import sys

from awscli.customizations.servicecatalog import helptext
from awscli.customizations.servicecatalog.generatebase \
    import GenerateBaseCommand
from botocore.compat import json


class GenerateProvisioningArtifactCommand(GenerateBaseCommand):
    NAME = 'provisioning-artifact'
    DESCRIPTION = helptext.PA_COMMAND_DESCRIPTION
    ARG_TABLE = [
        {
            'name': 'file-path',
            'required': True,
            'help_text': helptext.FILE_PATH
        },
        {
            'name': 'bucket-name',
            'required': True,
            'help_text': helptext.BUCKET_NAME
        },
        {
            'name': 'provisioning-artifact-name',
            'required': True,
            'help_text': helptext.PA_NAME
        },
        {
            'name': 'provisioning-artifact-description',
            'required': True,
            'help_text': helptext.PA_DESCRIPTION
        },
        {
            'name': 'provisioning-artifact-type',
            'required': True,
            'help_text': helptext.PA_TYPE,
            'choices': [
                'CLOUD_FORMATION_TEMPLATE',
                'MARKETPLACE_AMI',
                'MARKETPLACE_CAR'
            ]
        },
        {
            'name': 'product-id',
            'required': True,
            'help_text': helptext.PRODUCT_ID
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        super(GenerateProvisioningArtifactCommand, self)._run_main(
            parsed_args, parsed_globals)
        self.region = self.get_and_validate_region(parsed_globals)

        self.s3_url = self.create_s3_url(parsed_args.bucket_name,
                                         parsed_args.file_path)
        self.scs_client = self._session.create_client(
            'servicecatalog', region_name=self.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )

        response = self.create_provisioning_artifact(parsed_args,
                                                     self.s3_url)

        sys.stdout.write(json.dumps(response, indent=2, ensure_ascii=False))

        return 0

    def create_provisioning_artifact(self, parsed_args, s3_url):
        response = self.scs_client.create_provisioning_artifact(
            ProductId=parsed_args.product_id,
            Parameters={
                'Name': parsed_args.provisioning_artifact_name,
                'Description': parsed_args.provisioning_artifact_description,
                'Info': {
                    'LoadTemplateFromURL': s3_url
                },
                'Type': parsed_args.provisioning_artifact_type
            }
        )

        if 'ResponseMetadata' in response:
            del response['ResponseMetadata']
        return response
