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
from mock import Mock

from awscli.customizations.s3.syncstrategy.register import \
    register_sync_strategy
from awscli.testutils import unittest


class TestRegisterSyncStrategy(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.strategy_cls = Mock()
        self.strategy_object = Mock()
        self.strategy_cls.return_value = self.strategy_object

    def test_register_sync_strategy(self):
        """
        Ensure that registering a single strategy class works as expected
        when ``sync_type`` is specified.
        """
        register_sync_strategy(self.session, self.strategy_cls, 'sync_type')
        # Ensure sync strategy class is instantiated
        self.strategy_cls.assert_called_with('sync_type')
        # Ensure the sync strategy's ``register_strategy`` method is
        # called correctly.
        self.strategy_object.register_strategy.assert_called_with(self.session)

    def test_register_sync_strategy_default_sync_type(self):
        """
        Ensure that registering a single strategy class works as expected
        when the ``sync_type`` is not specified.
        """
        register_sync_strategy(self.session, self.strategy_cls)
        # Ensure sync strategy class is instantiated
        self.strategy_cls.assert_called_with('file_at_src_and_dest')
        # Ensure the sync strategy's ``register_strategy`` method is
        # called correctly.
        self.strategy_object.register_strategy.assert_called_with(self.session)


if __name__ == "__main__":
    unittest.main()
