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
from tests import unittest

import botocore.session
from botocore.exceptions import ClientError


class TestRoute53Pagination(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('route53', 'us-west-2')

    def test_paginate_with_max_items(self):
        # Route53 has a string type for MaxItems.  We need to ensure that this
        # still works without any issues.
        paginator = self.client.get_paginator('list_hosted_zones')
        results = list(paginator.paginate(PaginationConfig={'MaxItems': '1'}))
        self.assertTrue(len(results) >= 0)

    def test_paginate_with_deprecated_paginator_and_limited_input_tokens(self):
        paginator = self.client.get_paginator('list_resource_record_sets')

        # We're making sure the paginator gets set without failing locally, so
        # a ClientError is acceptable. In this case, the Hosted Zone specified
        # does not exist.
        with self.assertRaises(ClientError):
            results = list(paginator.paginate(
                PaginationConfig={
                    'MaxItems': '1',
                    'StartingToken': 'my.domain.name.'
                },
                HostedZoneId="foo"
            ))
            self.assertTrue(len(results) >= 0)


if __name__ == '__main__':
    unittest.main()
