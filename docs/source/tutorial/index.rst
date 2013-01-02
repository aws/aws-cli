Using botocore
**************

The intent is for people to build higher-level interfaces on top of
botocore.  Here is a simple example of how you can take advantage
of the low-level interface provided by botocore.

A quick example:

    >>> import botocore.session
    >>> session = botocore.session.get_session()
    >>> ec2 = session.get_service('ec2')
    >>> operation = ec2.get_operation('DescribeInstances')
    >>> ec2.region_names
    [u'us-east-1',
     u'ap-northeast-1',
     u'eu-west-1',
     u'ap-southeast-1',
     u'us-west-2',
     u'us-west-1',
     u'sa-east-1']
    >>> endpoint = ec2.get_endpoint('us-east-1')
    >>> response = operation.call(endpoint)
    >>> response
    (<Response [200]>,
     {u'requestId': u'd80ba703-71b6-4e9f-85d8-1ad5a5b5de19',
     ...}
    >>> http_response, data = operation.call(endpoint, instance_ids=['i-c4bb5fba'])
    >>> http_response
    <Response [200]>
    >>> data
    {u'reservationSet':
      [{u'ownerId': u'444444444444',
        u'groupSet': [{u'groupName': u'aws_mitch', u'groupId': u'sg-069e756e'}],
	u'reservationId': u'r-dd7d7fa4',
	u'instancesSet': [{u'productCodes': [],
	u'instanceId': u'i-c4bb5fba',
	u'imageId': u'ami-1b814f72',
	u'keyName': u'aws_mitch',
	u'clientToken': '',
	u'amiLaunchIndex': 0,
	u'instanceType': u't1.micro',
	...
	u'rootDeviceName': u'/dev/sda1'}]}],
      u'requestId': u'61850c11-5441-4e46-9a5b-16ec5ef7a4e0'}
    >>>
