# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.session

from awscli.testutils import unittest, aws


class TestDescribeInstances(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an instance in the scope of a class so that only one needs to
        # be created during the full test run.
        cls.session = botocore.session.get_session()
        cls.region = 'us-west-2'
        cls.client = cls.session.create_client('ec2', cls.region)
        response = cls.client.run_instances(
            ImageId='ami-7172b611', MinCount=1, MaxCount=1,
            InstanceType='t2.micro'
        )
        cls.instance = response['Instances'][0]
        cls.instance_id = cls.instance['InstanceId']

        # Wait for the instance to 'exist' so it can be used in tests.
        cls.client.get_waiter('instance_exists').wait(
            InstanceIds=[cls.instance_id]
        )

    @classmethod
    def tearDownClass(cls):
        cls.client.terminate_instances(InstanceIds=[cls.instance_id])

    def assert_instance_in_response(self, response):
        reservations = response['Reservations']
        self.assertEqual(len(reservations), 1)

        instances = reservations[0]['Instances']
        self.assertEqual(len(instances), 1)

        instance_id = instances[0]['InstanceId']
        self.assertEqual(instance_id, self.instance_id)

    def test_describe_instances_with_id(self):
        command = 'ec2 describe-instances --region %s' % self.region
        command += ' --instance-ids %s' % self.instance_id
        result = aws(command)
        self.assertEqual(result.rc, 0)
        self.assert_instance_in_response(result.json)

    def test_describe_instances_with_filter(self):
        command = 'ec2 describe-instances --region %s' % self.region
        command += ' --filters Name=private-dns-name,Values='
        command += self.instance['PrivateDnsName']
        result = aws(command)
        self.assertEqual(result.rc, 0)
        self.assert_instance_in_response(result.json)
