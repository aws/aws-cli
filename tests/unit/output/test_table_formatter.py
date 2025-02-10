# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import unittest

from awscli.formatter import TableFormatter
from awscli.table import MultiTable, Styler
from awscli.compat import StringIO

SIMPLE_LIST = {
    "QueueUrls": [
        "https://us-west-2.queue.amazonaws.com/1/queue1",
        "https://us-west-2.queue.amazonaws.com/1/queue2",
        "https://us-west-2.queue.amazonaws.com/1/queue3",
        "https://us-west-2.queue.amazonaws.com/1/queue4"
    ]
}



SIMPLE_LIST_TABLE = """\
------------------------------------------------------
|                    OperationName                   |
+----------------------------------------------------+
||                     QueueUrls                    ||
|+--------------------------------------------------+|
||  https://us-west-2.queue.amazonaws.com/1/queue1  ||
||  https://us-west-2.queue.amazonaws.com/1/queue2  ||
||  https://us-west-2.queue.amazonaws.com/1/queue3  ||
||  https://us-west-2.queue.amazonaws.com/1/queue4  ||
|+--------------------------------------------------+|
"""

SIMPLE_DICT = {"Attributes":
  {"a": "0",
   "b": "345600",
   "c": "0",
   "d": "65536",
   "e": "1351044153",
   "f": "0"}
}


SIMPLE_DICT_TABLE = """\
----------------------------------------------------
|                   OperationName                  |
+--------------------------------------------------+
||                   Attributes                   ||
|+---+---------+----+--------+--------------+-----+|
|| a |    b    | c  |   d    |      e       |  f  ||
|+---+---------+----+--------+--------------+-----+|
||  0|  345600 |  0 |  65536 |  1351044153  |  0  ||
|+---+---------+----+--------+--------------+-----+|
"""


LIST_OF_DICTS = {
    "OrderableDBInstanceOptions": [
        {
            "AvailabilityZones": [
                {
                    "Name": "us-east-1a",
                    "ProvisionedIopsCapable": False
                },
                {
                    "Name": "us-east-1d",
                    "ProvisionedIopsCapable": True
                }
            ],
            "DBInstanceClass": "db.m1.large",
            "Engine": "mysql",
            "EngineVersion": "5.1.45",
            "LicenseModel": "general-public-license",
            "MultiAZCapable": True,
            "ReadReplicaCapable": True,
            "Vpc": False
        },
        {
            "AvailabilityZones": [
                {
                    "Name": "us-west-2a",
                    "ProvisionedIopsCapable": True
                },
                {
                    "Name": "us-west-2b",
                    "ProvisionedIopsCapable": True
                }
            ],
            "DBInstanceClass": "db.m1.xlarge",
            "Engine": "mysql",
            "EngineVersion": "5.1.57",
            "LicenseModel": "general-public-license",
            "MultiAZCapable": True,
            "ReadReplicaCapable": True,
            "Vpc": False
        },
        {
            "AvailabilityZones": [
                {
                    "Name": "us-west-2a",
                    "ProvisionedIopsCapable": True
                },
            ],
            "DBInstanceClass": "db.m1.xlarge",
            "Engine": "mysql",
            "EngineVersion": "5.1.57",
            "LicenseModel": "general-public-license",
            "MultiAZCapable": True,
            "ReadReplicaCapable": True,
            "Vpc": True
        }
    ]
}

LIST_OF_DICTS_TABLE = """\
-----------------------------------------------------------------------------------------------------------------------------
|                                                       OperationName                                                       |
+---------------------------------------------------------------------------------------------------------------------------+
||                                               OrderableDBInstanceOptions                                                ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
|| DBInstanceClass | Engine  | EngineVersion  |      LicenseModel       | MultiAZCapable  | ReadReplicaCapable   |   Vpc   ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
||  db.m1.large    |  mysql  |  5.1.45        |  general-public-license |  True           |  True                |  False  ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
|||                                                   AvailabilityZones                                                   |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||                  Name                  |                           ProvisionedIopsCapable                             |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||  us-east-1a                            |  False                                                                       |||
|||  us-east-1d                            |  True                                                                        |||
||+----------------------------------------+------------------------------------------------------------------------------+||
||                                               OrderableDBInstanceOptions                                                ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
|| DBInstanceClass | Engine  | EngineVersion  |      LicenseModel       | MultiAZCapable  | ReadReplicaCapable   |   Vpc   ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
||  db.m1.xlarge   |  mysql  |  5.1.57        |  general-public-license |  True           |  True                |  False  ||
|+-----------------+---------+----------------+-------------------------+-----------------+----------------------+---------+|
|||                                                   AvailabilityZones                                                   |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||                  Name                  |                           ProvisionedIopsCapable                             |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||  us-west-2a                            |  True                                                                        |||
|||  us-west-2b                            |  True                                                                        |||
||+----------------------------------------+------------------------------------------------------------------------------+||
||                                               OrderableDBInstanceOptions                                                ||
|+-----------------+---------+----------------+--------------------------+-----------------+----------------------+--------+|
|| DBInstanceClass | Engine  | EngineVersion  |      LicenseModel        | MultiAZCapable  | ReadReplicaCapable   |  Vpc   ||
|+-----------------+---------+----------------+--------------------------+-----------------+----------------------+--------+|
||  db.m1.xlarge   |  mysql  |  5.1.57        |  general-public-license  |  True           |  True                |  True  ||
|+-----------------+---------+----------------+--------------------------+-----------------+----------------------+--------+|
|||                                                   AvailabilityZones                                                   |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||                  Name                  |                           ProvisionedIopsCapable                             |||
||+----------------------------------------+------------------------------------------------------------------------------+||
|||  us-west-2a                            |  True                                                                        |||
||+----------------------------------------+------------------------------------------------------------------------------+||
"""


# First record has "Tags" scalar, second record does not.
INNER_LIST = {
    "Snapshots": [
        {
            "Description": "TestVolume1",
            "Tags": [{"Value": "TestVolume", "Key": "Name"}],
            "VolumeId": "vol-12345",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            "StartTime": "2012-05-23T21:46:41.000Z",
            "SnapshotId": "snap-1234567",
            "OwnerId": "12345"
        },
        {
            "Description": "Created by CreateImage(i-1234) for ami-1234 from vol-1234",
            "VolumeId": "vol-e543b98b",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            "StartTime": "2012-05-25T00:07:20.000Z",
            "SnapshotId": "snap-23456",
            "OwnerId": "12345"
        }
    ]
}

INNER_LIST_TABLE = """\
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                               OperationName                                                                               |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
||                                                                                Snapshots                                                                                ||
|+-------------------+--------------+----------------+---------------------+--------------------------------------+-----------------+-----------------+--------------------+|
||    Description    |   OwnerId    |   Progress     |     SnapshotId      |              StartTime               |      State      |    VolumeId     |    VolumeSize      ||
|+-------------------+--------------+----------------+---------------------+--------------------------------------+-----------------+-----------------+--------------------+|
||  TestVolume1      |  12345       |  100%          |  snap-1234567       |  2012-05-23T21:46:41.000Z            |  completed      |  vol-12345      |  8                 ||
|+-------------------+--------------+----------------+---------------------+--------------------------------------+-----------------+-----------------+--------------------+|
|||                                                                                 Tags                                                                                  |||
||+-----------------------------------------------------------+-----------------------------------------------------------------------------------------------------------+||
|||                            Key                            |                                                   Value                                                   |||
||+-----------------------------------------------------------+-----------------------------------------------------------------------------------------------------------+||
|||  Name                                                     |  TestVolume                                                                                               |||
||+-----------------------------------------------------------+-----------------------------------------------------------------------------------------------------------+||
||                                                                                Snapshots                                                                                ||
|+------------------------------------------------------------+----------+-----------+-------------+---------------------------+------------+---------------+--------------+|
||                         Description                        | OwnerId  | Progress  | SnapshotId  |         StartTime         |   State    |   VolumeId    | VolumeSize   ||
|+------------------------------------------------------------+----------+-----------+-------------+---------------------------+------------+---------------+--------------+|
||  Created by CreateImage(i-1234) for ami-1234 from vol-1234 |  12345   |  100%     |  snap-23456 |  2012-05-25T00:07:20.000Z |  completed |  vol-e543b98b |  8           ||
|+------------------------------------------------------------+----------+-----------+-------------+---------------------------+------------+---------------+--------------+|
"""

LIST_WITH_MISSING_KEYS = {
    "Snapshots": [
        {
            "Description": "TestVolume1",
            "Tags": "foo",
            "VolumeId": "vol-12345",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            "StartTime": "2012-05-23T21:46:41.000Z",
            "SnapshotId": "snap-1234567",
            "OwnerId": "12345"
        },
        {
            "Description": "description",
            "VolumeId": "vol-e543b98b",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            "StartTime": "2012-05-25T00:07:20.000Z",
            "SnapshotId": "snap-23456",
            "OwnerId": "12345"
        }
    ]
}

LIST_WITH_MISSING_KEYS_TABLE = """\
-----------------------------------------------------------------------------------------------------------------------------------------
|                                                             OperationName                                                             |
+---------------------------------------------------------------------------------------------------------------------------------------+
||                                                              Snapshots                                                              ||
|+-------------+----------+-----------+---------------+---------------------------+------------+-------+----------------+--------------+|
|| Description | OwnerId  | Progress  |  SnapshotId   |         StartTime         |   State    | Tags  |   VolumeId     | VolumeSize   ||
|+-------------+----------+-----------+---------------+---------------------------+------------+-------+----------------+--------------+|
||  TestVolume1|  12345   |  100%     |  snap-1234567 |  2012-05-23T21:46:41.000Z |  completed |  foo  |  vol-12345     |  8           ||
||  description|  12345   |  100%     |  snap-23456   |  2012-05-25T00:07:20.000Z |  completed |       |  vol-e543b98b  |  8           ||
|+-------------+----------+-----------+---------------+---------------------------+------------+-------+----------------+--------------+|
"""

KEYS_NOT_FROM_FIRST_ROW = {
    "Snapshots": [
        {
            "Description": "TestVolume1",
            "Tags": "foo",
            "VolumeId": "vol-12345",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            "StartTime": "start_time",
            # Missing EndTime.
            "SnapshotId": "snap-1234567",
            "OwnerId": "12345"
        },
        {
            "Description": "description",
            "State": "completed",
            "VolumeSize": 8,
            "Progress": "100%",
            # Missing StartTime
            "EndTime": "end_time",
            "SnapshotId": "snap-23456",
            "OwnerId": "12345"
        }
    ]
}

KEYS_NOT_FROM_FIRST_ROW_TABLE = """\
------------------------------------------------------------------------------------------------------------------------------------
|                                                           OperationName                                                          |
+----------------------------------------------------------------------------------------------------------------------------------+
||                                                            Snapshots                                                           ||
|+-------------+-----------+----------+-----------+---------------+-------------+------------+-------+-------------+--------------+|
|| Description |  EndTime  | OwnerId  | Progress  |  SnapshotId   |  StartTime  |   State    | Tags  |  VolumeId   | VolumeSize   ||
|+-------------+-----------+----------+-----------+---------------+-------------+------------+-------+-------------+--------------+|
||  TestVolume1|           |  12345   |  100%     |  snap-1234567 |  start_time |  completed |  foo  |  vol-12345  |  8           ||
||  description|  end_time |  12345   |  100%     |  snap-23456   |             |  completed |       |             |  8           ||
|+-------------+-----------+----------+-----------+---------------+-------------+------------+-------+-------------+--------------+|
"""

JMESPATH_FILTERED_RESPONSE = [
    [
        [
            "i-12345",
            "ami-12345",
            "ebs",
            "t1.micro",
            "running",
            "disabled",
            "util"
        ]
    ],
    [
        [
            "i-56789",
            "ami-56789",
            "ebs",
            "c1.medium",
            "running",
            "disabled",
            "myname"
        ]
    ],
]
JMESPATH_FILTERED_RESPONSE_TABLE = """\
-------------------------------------------------------------------------------
|                                OperationName                                |
+---------+------------+------+------------+----------+------------+----------+
|  i-12345|  ami-12345 |  ebs |  t1.micro  |  running |  disabled  |  util    |
|  i-56789|  ami-56789 |  ebs |  c1.medium |  running |  disabled  |  myname  |
+---------+------------+------+------------+----------+------------+----------+
"""


JMESPATH_FILTERED_RESPONSE_DICT = [
    [
        {
            "InstanceId": "i-12345",
            "RootDeviceType": "ebs",
            "InstanceType": "t1.micro",
            "ImageId": "ami-12345"
        }
    ],
    [
        {
            "InstanceId": "i-56789",
            "RootDeviceType": "ebs",
            "InstanceType": "c1.medium",
            "ImageId": "ami-56789"
        }
    ],
]


JMESPATH_FILTERED_RESPONSE_DICT_TABLE = """\
---------------------------------------------------------------
|                        OperationName                        |
+-----------+-------------+----------------+------------------+
|  ImageId  | InstanceId  | InstanceType   | RootDeviceType   |
+-----------+-------------+----------------+------------------+
|  ami-12345|  i-12345    |  t1.micro      |  ebs             |
|  ami-56789|  i-56789    |  c1.medium     |  ebs             |
+-----------+-------------+----------------+------------------+
"""


class Object(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.query = None


class TestTableFormatter(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        styler = Styler()
        self.table = MultiTable(initial_section=False,
                                column_separator='|', styler=styler,
                                auto_reformat=False)
        self.formatter = TableFormatter(Object(color='off'))
        self.formatter.table = self.table
        self.stream = StringIO()

    def assert_data_renders_to(self, data, table):
        self.formatter('OperationName', data, stream=self.stream)
        rendered = self.stream.getvalue()
        if rendered != table:
            error_message = ['Expected table rendering does not match '
                             'the actual table rendering:']
            error_message.append('Expected:')
            error_message.append(table)
            error_message.append('Actual:')
            error_message.append(rendered)
            self.fail('\n'.join(error_message))

    def test_list_table(self):
        self.assert_data_renders_to(data=SIMPLE_LIST, table=SIMPLE_LIST_TABLE)

    def test_dict_table(self):
        self.assert_data_renders_to(data=SIMPLE_DICT, table=SIMPLE_DICT_TABLE)

    def test_list_of_dicts(self):
        self.assert_data_renders_to(data=LIST_OF_DICTS,
                                    table=LIST_OF_DICTS_TABLE)

    def test_inner_table(self):
        self.assert_data_renders_to(data=INNER_LIST,
                                    table=INNER_LIST_TABLE)

    def test_empty_table(self):
        self.assert_data_renders_to(data={},
                                    table='')

    def test_missing_keys(self):
        self.assert_data_renders_to(data=LIST_WITH_MISSING_KEYS,
                                    table=LIST_WITH_MISSING_KEYS_TABLE)

    def test_new_keys_after_first_row(self):
        self.assert_data_renders_to(data=KEYS_NOT_FROM_FIRST_ROW,
                                    table=KEYS_NOT_FROM_FIRST_ROW_TABLE)

    def test_jmespath_filtered_response(self):
        self.assert_data_renders_to(data=JMESPATH_FILTERED_RESPONSE,
                                    table=JMESPATH_FILTERED_RESPONSE_TABLE)

    def test_jmespath_filtered_dict_response(self):
        self.assert_data_renders_to(data=JMESPATH_FILTERED_RESPONSE_DICT,
                                    table=JMESPATH_FILTERED_RESPONSE_DICT_TABLE)
