# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy

import six, unittest
import ruamel.yaml as yaml

if six.PY3:
    unittest.TestCase.assertItemsEqual = unittest.TestCase.assertCountEqual


class BaseYAMLTest(unittest.TestCase):
    """Base class for preserving ruamel defaults

    Because ruamel mutates module and class state when custom components
    are added to a loader or a dumper, it will force downstream tests to pick
    up these customizations and cause unexpected failures. This class is meant
    to preserve any ruamel defaults to prevent downstream test failures. Note
    that mutating module and class state is not really a problem though when a
    CLI command runs because we do not run multiple commands that differ
    in YAML loading logic in a single process.
    """
    def setUp(self):
        super(BaseYAMLTest, self).setUp()
        self.original_implicit_resolvers = copy.deepcopy(
            yaml.resolver.implicit_resolvers)

    def tearDown(self):
        super(BaseYAMLTest, self).tearDown()
        yaml.resolver.implicit_resolvers = self.original_implicit_resolvers
