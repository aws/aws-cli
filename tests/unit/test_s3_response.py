#!/bin/env python
import botocore.session
import botocore.response

xml = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>test-1357854246</Name>
  <Prefix></Prefix>
  <Marker></Marker>
  <MaxKeys>1000</MaxKeys>
  <IsTruncated>false</IsTruncated>
  <Contents>
    <Key>foobar</Key>
    <LastModified>2013-01-10T21:45:09.000Z</LastModified>
    <ETag>&quot;1d921b22129502cbbe5cbaf2c8bac682&quot;</ETag>
    <Size>10000</Size>
    <Owner>
      <ID>1936a5d8a2b189cda450d1d1d514f3861b3adc2df5152d2a294487b9445d1e7f</ID>
      <DisplayName>mitchaws</DisplayName>
    </Owner>
    <StorageClass>STANDARD</StorageClass>
  </Contents>
  <Contents>
    <Key>fiebaz</Key>
    <LastModified>2013-01-11T21:45:09.000Z</LastModified>
    <ETag>&quot;1d921b22129502cbbe5cbaf2c8bac682&quot;</ETag>
    <Size>10000</Size>
    <Owner>
      <ID>1936a5d8a2b189cda450d1d1d514f3861b3adc2df5152d2a294487b9445d1e7f</ID>
      <DisplayName>mitchaws</DisplayName>
    </Owner>
    <StorageClass>STANDARD</StorageClass>
  </Contents>
</ListBucketResult>"""

response = {u'ListBucketResult':
            {u'Name': u'test-1357854246',
             u'MaxKeys': u'1000',
             u'Prefix': '',
             u'Marker': '',
             u'IsTruncated': u'false',
             u'Contents': [
                 {u'LastModified': u'2013-01-10T21:45:09.000Z',
                  u'ETag': u'"1d921b22129502cbbe5cbaf2c8bac682"',
                  u'StorageClass': u'STANDARD',
                  u'Key': u'foobar',
                  u'Owner': {u'DisplayName': u'mitchaws',
                             u'ID': u'1936a5d8a2b189cda450d1d1d514f3861b3adc2df5152d2a294487b9445d1e7f'},
                  u'Size': 10000},
                 {u'LastModified': u'2013-01-11T21:45:09.000Z',
                  u'ETag': u'"1d921b22129502cbbe5cbaf2c8bac682"',
                  u'StorageClass': u'STANDARD',
                  u'Key': u'fiebaz',
                  u'Owner': {u'DisplayName': u'mitchaws',
                             u'ID': u'1936a5d8a2b189cda450d1d1d514f3861b3adc2df5152d2a294487b9445d1e7f'},
                  u'Size': 10000}]}}


def main():
    session = botocore.session.get_session()
    session.set_debug_logger()
    s3 = session.get_service('s3')
    op = s3.get_operation('ListObjects')
    response = botocore.response.Response(op)
    response.parse(xml)
    assert response.get_value() == result


if __name__ == '__main__':
    main()
