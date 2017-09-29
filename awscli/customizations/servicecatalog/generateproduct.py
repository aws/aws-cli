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


class GenerateProductCommand(GenerateBaseCommand):
    NAME = "product"
    DESCRIPTION = helptext.PRODUCT_COMMAND_DESCRIPTION
    ARG_TABLE = [
        {
            'name': 'product-name',
            'required': True,
            'help_text': helptext.PRODUCT_NAME
        },
        {
            'name': 'product-owner',
            'required': True,
            'help_text': helptext.OWNER
        },
        {
            'name': 'product-type',
            'required': True,
            'help_text': helptext.PRODUCT_TYPE,
            'choices': ['CLOUD_FORMATION_TEMPLATE', 'MARKETPLACE']
        },
        {
            'name': 'product-description',
            'required': False,
            'help_text': helptext.PRODUCT_DESCRIPTION
        },
        {
            'name': 'product-distributor',
            'required': False,
            'help_text': helptext.DISTRIBUTOR
        },
        {
            'name': 'tags',
            'required': False,
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            },
            'default': [],
            'synopsis': '--tags Key=key1,Value=value1 Key=key2,Value=value2',
            'help_text': helptext.TAGS
        },
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
            'name': 'support-description',
            'required': False,
            'help_text': helptext.SUPPORT_DESCRIPTION
        },
        {
            'name': 'support-email',
            'required': False,
            'help_text': helptext.SUPPORT_EMAIL
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
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        super(GenerateProductCommand, self)._run_main(parsed_args,
                                                      parsed_globals)
        self.region = self.get_and_validate_region(parsed_globals)

        self.s3_url = self.create_s3_url(parsed_args.bucket_name,
                                         parsed_args.file_path)
        self.scs_client = self._session.create_client(
            'servicecatalog', region_name=self.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )

        response = self.create_product(self.build_args(parsed_args,
                                                       self.s3_url),
                                       parsed_globals)
        sys.stdout.write(json.dumps(response, indent=2, ensure_ascii=False))

        return 0

    def create_product(self, args, parsed_globals):
        response = self.scs_client.create_product(**args)
        if 'ResponseMetadata' in response:
            del response['ResponseMetadata']
        return response

    def _extract_tags(self, args_tags):
        tags = []
        for tag in args_tags:
            tags.append(dict(t.split('=') for t in tag.split(',')))
        return tags

    def build_args(self, parsed_args, s3_url):
        args = {
            "Name": parsed_args.product_name,
            "Owner": parsed_args.product_owner,
            "ProductType": parsed_args.product_type,
            "Tags": self._extract_tags(parsed_args.tags),
            "ProvisioningArtifactParameters": {
                'Name': parsed_args.provisioning_artifact_name,
                'Description': parsed_args.provisioning_artifact_description,
                'Info': {
                    'LoadTemplateFromURL': s3_url
                },
                'Type': parsed_args.provisioning_artifact_type
            }
        }

        # Non-required args
        if parsed_args.support_description:
            args["SupportDescription"] = parsed_args.support_description
        if parsed_args.product_description:
            args["Description"] = parsed_args.product_description
        if parsed_args.support_email:
            args["SupportEmail"] = parsed_args.support_email
        if parsed_args.product_distributor:
            args["Distributor"] = parsed_args.product_distributor

        return args
