# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import itertools

import botocore.session
from tests import unittest


class TestRDSPagination(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('rds', 'us-west-2')

    def test_can_paginate_reserved_instances(self):
        # Using an operation that we know will paginate.
        paginator = self.client.get_paginator(
            'describe_reserved_db_instances_offerings'
        )
        generator = paginator.paginate()
        results = list(itertools.islice(generator, 0, 3))
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['Marker'] != results[1]['Marker'])

    def test_can_paginate_orderable_db(self):
        paginator = self.client.get_paginator(
            'describe_orderable_db_instance_options'
        )
        generator = paginator.paginate(Engine='mysql')
        results = list(itertools.islice(generator, 0, 2))
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].get('Marker') != results[1].get('Marker'))


if __name__ == '__main__':
    unittest.main()
