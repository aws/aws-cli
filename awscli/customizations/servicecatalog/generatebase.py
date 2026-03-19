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

from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3uploader import S3Uploader
from awscli.customizations.servicecatalog import exceptions
from awscli.customizations.servicecatalog.utils import get_s3_path, make_url


class GenerateBaseCommand(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        self.region = self.get_and_validate_region(parsed_globals)
        self.s3_client = self._session.create_client(
            's3',
            region_name=self.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )
        self.s3_uploader = S3Uploader(
            self.s3_client, parsed_args.bucket_name, force_upload=True
        )
        try:
            self.s3_uploader.upload(
                parsed_args.file_path, get_s3_path(parsed_args.file_path)
            )
        except OSError:
            raise RuntimeError("%s cannot be found" % parsed_args.file_path)

    def get_and_validate_region(self, parsed_globals):
        region = parsed_globals.region
        if region is None:
            region = self._session.get_config_variable('region')
        if region not in self._session.get_available_regions('servicecatalog'):
            raise exceptions.InvalidParametersException(
                message=f"Region {parsed_globals.region} is not supported"
            )
        return region

    def create_s3_url(self, bucket_name, file_path):
        return make_url(self.region, bucket_name, get_s3_path(file_path))
