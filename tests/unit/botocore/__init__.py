# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
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
import copy

from tests import unittest


class BaseResponseTest(unittest.TestCase):
    def assert_response_with_subset_metadata(
        self, actual_response, expected_response
    ):
        """
        Compares two parsed service responses. For ResponseMetadata, it will
        only assert that the expected is a proper subset of the actual. This
        is useful so that when new keys are added to the metadata, tests don't
        break.
        """
        actual = copy.copy(actual_response)
        expected = copy.copy(expected_response)

        actual_metadata = actual.pop('ResponseMetadata', {})
        expected_metadata = expected.pop('ResponseMetadata', {})

        self.assertEqual(actual, expected)
        self.assert_dict_is_proper_subset(actual_metadata, expected_metadata)

    def assert_dict_is_proper_subset(self, superset, subset):
        """
        Asserts that a dictionary is a proper subset of another.
        """
        self.assertTrue(
            all(
                (k in superset and superset[k] == v) for k, v in subset.items()
            )
        )
