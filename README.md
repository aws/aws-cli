botocore
========

The low-level, core functionality of boto 3.

A quick example:

    >>> import botocore.service
    >>> ec2 = botocore.service.get_service('ec2')
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
    >>> response = operation.call(endpoint, instance_ids=['i-c4bb5fba'])
    >>> response
    (<Response [200]>,
    {u'reservationSet':
      [{u'ownerId': u'419278470775',
        u'groupSet': [{u'groupName': u'aws_mitch', u'groupId': u'sg-069e756e'}],
	u'reservationId': u'r-dd7d7fa4',
	u'instancesSet': [{u'productCodes': [],
	u'instanceId': u'i-c4bb5fba',
	u'imageId': u'ami-1b814f72',
	u'keyName': u'aws_mitch',
	u'clientToken': '',
	u'amiLaunchIndex': 0,
	u'instanceType': u't1.micro',
	u'groupSet': [{u'groupName': u'aws_mitch', u'groupId': u'sg-069e756e'}],
	u'monitoring': {u'state': u'disabled'},
	u'dnsName': u'ec2-107-22-36-64.compute-1.amazonaws.com',
	u'kernelId': u'aki-825ea7eb',
	u'privateIpAddress': u'10.210.253.113',
	u'virtualizationType': u'paravirtual',
	u'privateDnsName': u'domU-12-31-39-09-FA-87.compute-1.internal',
	u'reason': '',
	u'tagSet': [{u'value': '', u'key': u'moarservers'}],
	u'blockDeviceMapping': [{u'deviceName': u'/dev/sda1', u'ebs': {u'status': u'attached', u'deleteOnTermination': True, u'volumeId': u'vol-2ac62055', u'attachTime': u'2012-12-03T14:37:47.000Z'}}],
	u'placement': {u'groupName': '', u'tenancy': u'default', u'availabilityZone': u'us-east-1d'},
	u'instanceState': {u'code': 16, u'name': u'running'},
	u'launchTime': u'2012-12-03T14:37:43.000Z',
	u'architecture': u'x86_64',
	u'hypervisor': u'xen',
	u'rootDeviceType': u'ebs',
	u'ipAddress': u'107.22.36.64',
	u'rootDeviceName': u'/dev/sda1'}]}],
      u'requestId': u'61850c11-5441-4e46-9a5b-16ec5ef7a4e0'})
    >>>