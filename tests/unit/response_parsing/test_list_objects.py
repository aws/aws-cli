#!/bin/env python
import unittest
import six
import botocore.session
import botocore.response

xml = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>test-1357854246</Name><Prefix></Prefix><Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated><Contents><Key>015d5379-1751-4701-aece-a5fb9e6f3b30</Key><LastModified>2013-01-10T21:45:09.000Z</LastModified><ETag>&quot;1d921b22129502cbbe5cbaf2c8bac682&quot;</ETag><Size>10000</Size><Owner><ID>1936a5d8a2b189cda450d1d1d514f3861b3adc2df515</ID><DisplayName>mitchaws</DisplayName></Owner><StorageClass>STANDARD</StorageClass></Contents></ListBucketResult>"""

data = {'ListBucketResult':
        {'Contents':
         [{'ETag': '"1d921b22129502cbbe5cbaf2c8bac682"',
           'Key': '015d5379-1751-4701-aece-a5fb9e6f3b30',
           'LastModified': '2013-01-10T21:45:09.000Z',
           'Owner': {'DisplayName': 'mitchaws',
                      'ID': '1936a5d8a2b189cda450d1d1d514f3861b3adc2df515'},
           'Size': 10000,
           'StorageClass': 'STANDARD'}],
         'IsTruncated': False,
         'Marker': '',
         'MaxKeys': 1000,
         'Name': 'test-1357854246',
         'Prefix': ''}}


class TestListObjects(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('s3', 'aws')

    def test_list_objects(self):
        op = self.service.get_operation('ListObjects')
        response = botocore.response.XmlResponse(op)
        response.parse(six.b(xml))
        self.maxDiff = None
        self.assertEqual(response.get_value(), data)


if __name__ == '__main__':
    unittest.main()
