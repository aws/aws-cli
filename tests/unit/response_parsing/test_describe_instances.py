#!/usr/bin/env python
import unittest
import botocore.session
import botocore.response

xml = """<DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2011-07-15/">
    <requestId>931a86ce-1415-4105-a851-79520622d582</requestId>
    <reservationSet>
        <item>
            <reservationId>r-765eaa10</reservationId>
            <ownerId>419278470775</ownerId>
            <groupSet>
                <item>
                    <groupId>sg-2c9e7544</groupId>
                    <groupName>default</groupName>
                </item>
            </groupSet>
            <instancesSet>
                <item>
                    <instanceId>i-5578ec28</instanceId>
                    <imageId>ami-e565ba8c</imageId>
                    <instanceState>
                        <code>16</code>
                        <name>running</name>
                    </instanceState>
                    <privateDnsName>domU-12-31-39-06-2A-8D.compute-1.internal</privateDnsName>
                    <dnsName>ec2-107-21-77-162.compute-1.amazonaws.com</dnsName>
                    <reason/>
                    <amiLaunchIndex>0</amiLaunchIndex>
                    <productCodes/>
                    <instanceType>m1.small</instanceType>
                    <launchTime>2012-10-04T15:32:50.000Z</launchTime>
                    <placement>
                        <availabilityZone>us-east-1d</availabilityZone>
                        <groupName/>
                        <tenancy>default</tenancy>
                    </placement>
                    <kernelId>aki-88aa75e1</kernelId>
                    <monitoring>
                        <state>disabled</state>
                    </monitoring>
                    <privateIpAddress>10.208.45.119</privateIpAddress>
                    <ipAddress>107.21.77.162</ipAddress>
                    <groupSet>
                        <item>
                            <groupId>sg-2c9e7544</groupId>
                            <groupName>default</groupName>
                        </item>
                    </groupSet>
                    <architecture>x86_64</architecture>
                    <rootDeviceType>ebs</rootDeviceType>
                    <rootDeviceName>/dev/sda1</rootDeviceName>
                    <blockDeviceMapping>
                        <item>
                            <deviceName>/dev/sda1</deviceName>
                            <ebs>
                                <volumeId>vol-c94909b3</volumeId>
                                <status>attached</status>
                                <attachTime>2012-10-04T15:32:54.000Z</attachTime>
                                <deleteOnTermination>true</deleteOnTermination>
                            </ebs>
                        </item>
                    </blockDeviceMapping>
                    <virtualizationType>paravirtual</virtualizationType>
                    <clientToken/>
                    <hypervisor>xen</hypervisor>
                </item>
            </instancesSet>
        </item>
    </reservationSet>
</DescribeInstancesResponse>"""

data = {u'reservationSet': [{u'ownerId': u'419278470775', u'groupSet': [{u'groupName': u'default', u'groupId': u'sg-2c9e7544'}], u'reservationId': u'r-765eaa10', u'instancesSet': [{u'productCodes': [], u'instanceId': u'i-5578ec28', u'imageId': u'ami-e565ba8c', u'clientToken': '', u'amiLaunchIndex': 0, u'instanceType': u'm1.small', u'groupSet': [{u'groupName': u'default', u'groupId': u'sg-2c9e7544'}], u'monitoring': {u'state': u'disabled'}, u'dnsName': u'ec2-107-21-77-162.compute-1.amazonaws.com', u'kernelId': u'aki-88aa75e1', u'privateIpAddress': u'10.208.45.119', u'virtualizationType': u'paravirtual', u'privateDnsName': u'domU-12-31-39-06-2A-8D.compute-1.internal', u'reason': '', u'blockDeviceMapping': [{u'deviceName': u'/dev/sda1', u'ebs': {u'status': u'attached', u'deleteOnTermination': True, u'volumeId': u'vol-c94909b3', u'attachTime': u'2012-10-04T15:32:54.000Z'}}], u'placement': {u'groupName': '', u'tenancy': u'default', u'availabilityZone': u'us-east-1d'}, u'instanceState': {u'code': 16, u'name': u'running'}, u'launchTime': u'2012-10-04T15:32:50.000Z', u'architecture': u'x86_64', u'hypervisor': u'xen', u'rootDeviceType': u'ebs', u'ipAddress': u'107.21.77.162', u'rootDeviceName': u'/dev/sda1'}]}], u'requestId': u'931a86ce-1415-4105-a851-79520622d582'}

class TestDescribeInstances(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('ec2', 'aws')

    def test_describe_instances(self):
        op = self.service.get_operation('DescribeInstances')
        r = botocore.response.Response(op)
        r.parse(xml)
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
