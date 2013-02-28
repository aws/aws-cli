
====================
A Simple EC2 Example
====================

First, let's look at how we could call the ``DescribeInstances`` operation
of the ``EC2`` service in an interactive Python session::

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
    >>> http_response, response_data = operation.call(endpoint)
    >>> http_response
    <Response [200]>
    >>> response_data
    {u'Reservations': [{u'Groups': [{u'GroupId': u'sg-4e970e7e',
       u'GroupName': u'notebook'}],
     u'Instances': [{u'AmiLaunchIndex': 0,
       u'Architecture': u'x86_64',
       u'BlockDeviceMappings': [{u'DeviceName': u'/dev/sda1',
         u'Ebs': {u'AttachTime': u'2012-10-16T20:00:21.000Z',
          u'DeleteOnTermination': True,
          u'Status': u'attached',
          u'VolumeId': u'vol-bc71579a'}}],
       u'ClientToken': '',
       u'EbsOptimized': False,
       u'Hypervisor': u'xen',
       u'ImageId': u'ami-30fe7300',
       u'InstanceId': u'i-fde9cece',
       u'InstanceType': u'm1.small',
       u'KernelId': u'aki-98e26fa8',
       u'KeyName': u'aws_mitch',
       u'LaunchTime': u'2012-10-16T20:00:13.000Z',
       u'Monitoring': {u'State': u'disabled'},
       u'NetworkInterfaces': [],
       u'Placement': {u'AvailabilityZone': u'us-west-2a',
         u'GroupName': '',
         u'Tenancy': u'default'},
       u'PrivateDnsName': u'ip-10-248-19-167.us-west-2.compute.internal',
       u'PrivateIpAddress': u'10.248.19.167',
       u'ProductCodes': [],
       u'PublicDnsName': u'ec2-54-245-81-77.us-west-2.compute.amazonaws.com',
       u'PublicIpAddress': u'54.245.81.77',
       u'RootDeviceName': u'/dev/sda1',
       u'RootDeviceType': u'ebs',
       u'SecurityGroups': [{u'GroupId': u'sg-4e970e7e',
         u'GroupName': u'notebook'}],
       u'State': {u'Code': 16, u'Name': u'running'},
       u'StateTransitionReason': '',
       u'Tags': [{u'Key': u'notebook', u'Value': ''}],
       u'VirtualizationType': u'paravirtual'}],
     u'OwnerId': u'419278470775',
     u'ReservationId': u'r-9b4f3ca8'}],
    u'requestId': u'4b056261-922b-4ce1-a739-1af345ada6f7'}
    >>>

The first thing we do is import the :py:mod:`botocore.session` module and then
create a :py:class:`botocore.session.Session` object.  The ``Session`` object
provides the main interface into the :py:mod:`botocore` module.

Once we have a :py:class:`botocore.session.Session` object we use it to
find the :py:class:`botocore.service.Service` object which represents
the ``EC2`` service.

Then, we use the service object to lookup the
:py:class:`botocore.operation.Operation` object for ``DescribeInstances``.  We
also look up the :py:class:`botocore.endpoint.Endpoint` object that
represents the HTTP endpoint we use for this service in the desired region.

Finally, we call the operation using the
:py:meth:`botocore.operation.Operation.call` method.  This method takes the
:py:class:`botocore.endpoint.Endpoint` object as the first parameter and
then accepts any number of keyword arguments that will be passed on to the
service as parameters of this operation.

The ``call`` method returns a tuple.  The first element of the tuple is
the ``http_response`` object.  The ``botocore`` module uses the
`requests <http://docs.python-requests.org/en/latest/>`_ package to
handle the HTTP layer so this will be a normal
`Response object from requests <http://docs.python-requests.org/en/latest/api/#requests.Response>`_.  The second element is the data from the
service request in the form of standard Python data structures.

If we wanted to pass in some parameters to ``DescribeInstances``, say a
``filter``, it would look like this::

    >>> http_response, response_data = operation.call(endpoint, filters=[{'name': 'instance-state-name', 'values':['pending']}])
    >>> response_data
    {u'Reservations': [], u'requestId': u'41d17b1d-e0c7-4d44-b856-eab8e706389e'}
    >>>

In this case, there are no instances in the ``pending`` state so no results
are returned.
