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

import re


def validate_s3_location(params, arg_name):
    arg_name = arg_name.replace('-', '_')
    if arg_name in params:
        s3_location = getattr(params, arg_name)
        if s3_location:
            matcher = re.match('s3://(.+?)/(.+)', str(s3_location))
            if matcher:
                params.bucket = matcher.group(1)
                params.key = matcher.group(2)
            else:
                raise ValueError(
                    '--{0} must specify the Amazon S3 URL format as '
                    's3://<bucket>/<key>.'.format(
                        arg_name.replace('_', '-')
                    )
                )
