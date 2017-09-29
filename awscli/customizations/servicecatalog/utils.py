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

import os


def make_url(region, bucket_name, obj_path, version=None):
    """
        This link describes the format of Path Style URLs
        http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html#access-bucket-intro
    """
    base = "https://s3.amazonaws.com"
    if region and region != "us-east-1":
        base = "https://s3-{0}.amazonaws.com".format(region)

    result = "{0}/{1}/{2}".format(base, bucket_name, obj_path)
    if version:
        result = "{0}?versionId={1}".format(result, version)

    return result


def get_s3_path(file_path):
    return os.path.basename(file_path)
