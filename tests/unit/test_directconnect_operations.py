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
import unittest
import botocore.session


class TestDirectconnectOperations(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.dc = self.session.get_service('directconnect')

    def test_create_connection(self):
        op = self.dc.get_operation('CreateConnection')
        params = op.build_parameters(connection_name='foobarconn',
                                     offering_id='foobaroffer')
        result = {'offeringId': 'foobaroffer',
                  'connectionName': 'foobarconn'}
        self.assertEqual(params, result)

    def test_describe_virtual_gateways(self):
        new_int = {'amazon_address': 'amzaddress',
                   'customer_address': 'custaddress',
                   'asn': 42,
                   'vlan': 43,
                   'auth_key': 'my_auth_key',
                   'virtual_interface_name': 'viname',
                   'route_filter_prefixes': [{'cidr': '1.2.3.4/5'},
                                             {'cidr': '6.7.8.9/10'}]}
        op = self.dc.get_operation('CreatePublicVirtualInterface')
        params = op.build_parameters(connection_id='dxcon-fg5678gh',
                                     new_public_virtual_interface=new_int)
        result = {'connectionId': 'dxcon-fg5678gh',
                  'newPublicVirtualInterface': {
                      'amazonAddress': 'amzaddress',
                      'customerAddress': 'custaddress',
                      'asn': 42,
                      'vlan': 43,
                      'authKey': 'my_auth_key',
                      'virtualInterfaceName': 'viname',
                      'routeFilterPrefixes': [{'cidr': '1.2.3.4/5'},
                                              {'cidr': '6.7.8.9/10'}]}}
        self.maxDiff = None
        self.assertEqual(params, result)



if __name__ == "__main__":
    unittest.main()
