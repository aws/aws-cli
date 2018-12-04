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
from awscli.testutils import unittest, aws


class TestDescribeInstances(unittest.TestCase):
    def setUp(self):
        self.prefix = 'ec2 describe-instances --region us-west-2'

    def test_describe_instances_with_id(self):
        command = self.prefix + ' --instance-ids malformed-id'
        result = aws(command)
        self.assertIn('InvalidInstanceID.Malformed', result.stderr)

    def test_describe_instances_with_filter(self):
        command = self.prefix + ' --filters Name=instance-id,Values='
        command += 'malformed-id'
        result = aws(command)
        reservations = result.json["Reservations"]
        self.assertEqual(len(reservations), 0)


class TestDescribeSnapshots(unittest.TestCase):
    def setUp(self):
        self.prefix = 'ec2 describe-snapshots --region us-west-2'

    def test_describe_snapshot_with_snapshot_id(self):
        command = self.prefix + ' --snapshot-ids malformed-id'
        result = aws(command)
        self.assertIn('InvalidParameterValue', result.stderr)

    def test_describe_snapshots_with_filter(self):
        command = self.prefix
        command += ' --filters Name=snapshot-id,Values=malformed-id'
        result = aws(command)
        snapshots = result.json['Snapshots']
        self.assertEqual(len(snapshots), 0)


class TestDescribeVolumes(unittest.TestCase):
    def setUp(self):
        self.prefix = 'ec2 describe-volumes --region us-west-2'

    def test_describe_volumes_with_volume_id(self):
        command = self.prefix + ' --volume-ids malformed-id'
        result = aws(command)
        self.assertIn('InvalidParameterValue', result.stderr)

    def test_describe_volumes_with_filter(self):
        command = self.prefix
        command += ' --filters Name=volume-id,Values=malformed-id'
        result = aws(command)
        volumes = result.json['Volumes']
        self.assertEqual(len(volumes), 0)
