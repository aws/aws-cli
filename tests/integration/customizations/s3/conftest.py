# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

import botocore.session
from awscli.testutils import random_chars, FileCreator
from tests import S3Utils


@pytest.fixture(scope='package')
def region():
    return 'us-west-2'


@pytest.fixture(scope='package')
def session():
    return botocore.session.Session()


@pytest.fixture(scope='package')
def s3_utils(session, region):
    return S3Utils(session, region)


@pytest.fixture(scope='package')
def shared_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket()
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


# Bucket for cross-S3 copies
@pytest.fixture(scope='package')
def shared_copy_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket()
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


# Bucket for cross-region, cross-S3 copies
@pytest.fixture(scope='package')
def shared_cross_region_bucket(s3_utils):
    bucket_name = s3_utils.create_bucket(region='eu-central-1')
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture(scope='package')
def shared_non_dns_compatible_bucket(s3_utils):
    bucket_name = _generate_non_dns_compatible_bucket_name()
    s3_utils.create_bucket(name=bucket_name)
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture(scope='package')
def shared_non_dns_compatible_us_east_1_bucket(s3_utils):
    bucket_name = _generate_non_dns_compatible_bucket_name()
    s3_utils.create_bucket(name=bucket_name, region='us-east-1')
    yield bucket_name
    s3_utils.delete_bucket(bucket_name)


@pytest.fixture
def clean_shared_buckets(s3_utils, shared_bucket, shared_copy_bucket,
                         shared_cross_region_bucket,
                         shared_non_dns_compatible_bucket,
                         shared_non_dns_compatible_us_east_1_bucket):
    s3_utils.remove_all_objects(shared_bucket)
    s3_utils.remove_all_objects(shared_copy_bucket)
    s3_utils.remove_all_objects(shared_cross_region_bucket)
    s3_utils.remove_all_objects(shared_non_dns_compatible_bucket)
    s3_utils.remove_all_objects(shared_non_dns_compatible_us_east_1_bucket)


@pytest.fixture
def files():
    files = FileCreator()
    yield files
    files.remove_all()


def _generate_non_dns_compatible_bucket_name():
    name_comp = []
    # This creates a non DNS compatible bucket name by making two random
    # sequences of characters and joining them with a period and
    # adding a .com at the end.
    for i in range(2):
        name_comp.append(random_chars(10))
    return '.'.join(name_comp + ['com'])
