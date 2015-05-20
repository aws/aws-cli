# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
from awscli.customizations.s3endpoint import on_top_level_args_parsed

from botocore.utils import fix_s3_host

import mock


class TestS3EndpointURL(unittest.TestCase):
    def test_endpoint_url_unregisters_fix_s3_host(self):
        args = mock.Mock()
        args.endpoint_url = 'http://custom/'
        args.command = 's3'
        event_handler = mock.Mock()
        on_top_level_args_parsed(args, event_handler)
        event_handler.unregister.assert_called_with('before-sign.s3', fix_s3_host)

    def test_unregister_not_called_for_no_endpoint(self):
        args = mock.Mock()
        args.endpoint_url = None
        event_handler = mock.Mock()
        on_top_level_args_parsed(args, event_handler)
        self.assertFalse(event_handler.unregister.called)

    def test_endpoint_url_set_but_not_for_s3(self):
        args = mock.Mock()
        args.endpoint_url = 'http://custom/'
        args.command = 'NOTS3'
        event_handler = mock.Mock()
        on_top_level_args_parsed(args, event_handler)
        self.assertFalse(event_handler.unregister.called)
