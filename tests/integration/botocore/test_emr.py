# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from tests import unittest

import botocore.session
from botocore.paginate import PageIterator
from botocore.exceptions import OperationNotPageableError


@pytest.fixture()
def botocore_session():
    return botocore.session.get_session()

@pytest.mark.parametrize(
    "region",
    [
        'us-east-1',
        'us-west-2',
        'us-west-2',
        'ap-northeast-1',
        'ap-southeast-1',
        'ap-southeast-2',
        'sa-east-1',
        'eu-west-1',
        'eu-central-1'
    ]
)
def test_emr_endpoints_work_with_py26(botocore_session, region):
    # Verify that we can talk to all currently supported EMR endpoints.
    # Python2.6 has an SSL cert bug where it can't read the SAN of
    # certain SSL certs.  We therefore need to always use the CN
    # as the hostname.
    client = botocore_session.create_client('emr', region_name=region)
    response = client.list_clusters()
    assert 'Clusters' in response


# I consider these integration tests because they're
# testing more than a single unit, we're ensuring everything
# accessible from the session works as expected.
class TestEMRGetExtraResources(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('emr', 'us-west-2')

    def test_can_access_pagination_configs(self):
        # Using an operation that we know will paginate.
        paginator = self.client.get_paginator('list_clusters')
        page_iterator = paginator.paginate()
        self.assertIsInstance(page_iterator, PageIterator)

    def test_operation_cant_be_paginated(self):
        with self.assertRaises(OperationNotPageableError):
            self.client.get_paginator('add_instance_groups')

    def test_can_get_waiters(self):
        waiter = self.client.get_waiter('cluster_running')
        self.assertTrue(hasattr(waiter, 'wait'))

    def test_waiter_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.client.get_waiter('does_not_exist')


if __name__ == '__main__':
    unittest.main()
