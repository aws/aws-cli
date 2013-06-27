#!/usr/bin/env python
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
from tests import BaseEnvVar
import botocore.session
from botocore.awsrequest import AWSRequest
from botocore.endpoint import RestEndpoint


class TestS3Addressing(BaseEnvVar):

    def setUp(self):
        super(TestS3Addressing, self).setUp()
        self.session = botocore.session.get_session()
        self.s3 = self.session.get_service('s3')

    def test_list_objects_dns_name(self):
        self.endpoint = self.s3.get_endpoint('us-east-1')
        op = self.s3.get_operation('ListObjects')
        params = op.build_parameters(bucket='safename')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://safename.s3.amazonaws.com/')

    def test_list_objects_non_dns_name(self):
        self.endpoint = self.s3.get_endpoint('us-east-1')
        op = self.s3.get_operation('ListObjects')
        params = op.build_parameters(bucket='un_safe_name')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://s3.amazonaws.com/un_safe_name')

    def test_list_objects_dns_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-2')
        op = self.s3.get_operation('ListObjects')
        params = op.build_parameters(bucket='safename')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://safename.s3.amazonaws.com/')

    def test_list_objects_non_dns_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-2')
        op = self.s3.get_operation('ListObjects')
        params = op.build_parameters(bucket='un_safe_name')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://s3-us-west-2.amazonaws.com/un_safe_name')

    def test_put_object_dns_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-2')
        op = self.s3.get_operation('PutObject')
        file_path = os.path.join(os.path.dirname(__file__),
                                 'put_object_data')
        fp = open(file_path, 'rb')
        params = op.build_parameters(bucket='my.valid.name',
                                     key='mykeyname',
                                     body=fp,
                                     acl='public-read',
                                     content_language='piglatin',
                                     content_type='text/plain')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://my.valid.name.s3.amazonaws.com/mykeyname')
        fp.close()

    def test_put_object_dns_name_classic(self):
        self.endpoint = self.s3.get_endpoint('us-east-1')
        op = self.s3.get_operation('PutObject')
        file_path = os.path.join(os.path.dirname(__file__),
                                 'put_object_data')
        fp = open(file_path, 'rb')
        params = op.build_parameters(bucket='my.valid.name',
                                     key='mykeyname',
                                     body=fp,
                                     acl='public-read',
                                     content_language='piglatin',
                                     content_type='text/plain')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://my.valid.name.s3.amazonaws.com/mykeyname')
        fp.close()
        
    def test_put_object_dns_name_single_letter_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-2')
        op = self.s3.get_operation('PutObject')
        file_path = os.path.join(os.path.dirname(__file__),
                                 'put_object_data')
        fp = open(file_path, 'rb')
        params = op.build_parameters(bucket='a.valid.name',
                                     key='mykeyname',
                                     body=fp,
                                     acl='public-read',
                                     content_language='piglatin',
                                     content_type='text/plain')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://a.valid.name.s3.amazonaws.com/mykeyname')
        fp.close()

    def test_get_object_non_dns_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-2')
        op = self.s3.get_operation('GetObject')
        params = op.build_parameters(bucket='AnInvalidName',
                                     key='mykeyname')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://s3-us-west-2.amazonaws.com/AnInvalidName/mykeyname')

    def test_get_object_non_dns_name_classic(self):
        self.endpoint = self.s3.get_endpoint('us-east-1')
        op = self.s3.get_operation('GetObject')
        params = op.build_parameters(bucket='AnInvalidName',
                                     key='mykeyname')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://s3.amazonaws.com/AnInvalidName/mykeyname')

    def test_get_object_ip_address_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-s')
        op = self.s3.get_operation('GetObject')
        params = op.build_parameters(bucket='192.168.5.4',
                                     key='mykeyname')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://s3.amazonaws.com/192.168.5.4/mykeyname')


    def test_get_object_almost_an_ip_address_name_non_classic(self):
        self.endpoint = self.s3.get_endpoint('us-west-s')
        op = self.s3.get_operation('GetObject')
        params = op.build_parameters(bucket='192.168.5.256',
                                     key='mykeyname')
        prepared_request = self.endpoint.make_request(op, params, no_op=True)
        self.assertEqual(prepared_request.url,
                         'https://192.168.5.256.s3.amazonaws.com/mykeyname')



if __name__ == "__main__":
    unittest.main()
