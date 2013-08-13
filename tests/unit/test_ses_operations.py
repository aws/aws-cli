#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from tests import BaseEnvVar

from mock import Mock, sentinel

import botocore.session
from botocore.exceptions import MissingParametersError, ValidationError
from botocore.exceptions import UnknownParameterError
from botocore.exceptions import UnknownKeyError


class TestSESOperations(BaseEnvVar):

    def setUp(self):
        super(TestSESOperations, self).setUp()
        self.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'
        self.session = botocore.session.get_session()
        self.ses = self.session.get_service('ses')
        self.op = self.ses.get_operation('SendEmail')

    def test_send_email_missing_required_parameters(self):
        with self.assertRaisesRegexp(
                MissingParametersError,
                ('The following required parameters are missing '
                 'for Operation:SendEmail: source, destination, message')):
            self.op.build_parameters()

    def test_send_email_validates_structure(self):
        with self.assertRaises(ValidationError):
            self.op.build_parameters(
                source='foo@example.com',
                destination={'ToAddresses': ['bar@examplecom']},
                message='bar')

    def test_send_email_with_required_inner_member(self):
        with self.assertRaises(MissingParametersError):
            self.op.build_parameters(
                source='foo@example.com',
                destination={'ToAddresses': ['bar@examplecom']},
                message={})

    def test_send_email_with_unknown_params(self):
        with self.assertRaises(UnknownParameterError):
            self.op.build_parameters(
                source='foo@example.com',
                to={'ToAddresses': ['bar@examplecom']},
                message={})


    def test_send_email_with_missing_inner_member(self):
        with self.assertRaises(MissingParametersError):
            self.op.build_parameters(source='foo@example.com',
                                     destination={'ToAddresses': ['bar@examplecom']},
                                     message={'Subject': {'Data': 'foo'},
                                              # 'Text' is missing the 'Data'
                                              # param.
                                              'Body': {'Text': {}}})

    def test_send_email_with_unknown_inner_member(self):
        with self.assertRaises(UnknownKeyError):
            self.op.build_parameters(
                source='foo@example.com',
                destination={'ToAddresses': ['bar@examplecom']},
                message={'Subject': {'Data': 'foo'},
                         'Body': {'Text': {'BADKEY': 'foo'}}})


if __name__ == "__main__":
    unittest.main()
