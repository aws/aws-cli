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
import six

from awscli.formatter import TableFormatter
from awscli.table import MultiTable, Styler

SIMPLE_LIST = {
    "QueueUrls": [
        "https://us-west-2.queue.amazonaws.com/1/queue1",
        "https://us-west-2.queue.amazonaws.com/1/queue2",
        "https://us-west-2.queue.amazonaws.com/1/queue3",
        "https://us-west-2.queue.amazonaws.com/1/queue4"
    ],
    "ResponseMetadata": {
        "RequestId": "b04d5718-93e6-5503-8ef1-1eb7b7e402e1"
    }
}



SIMPLE_LIST_TABLE = """\
---------------------------------------------------------
|                     OperationName                     |
+-------------------------------------------------------+
||                      QueueUrls                      ||
|+-----------------------------------------------------+|
||  https://us-west-2.queue.amazonaws.com/1/queue1     ||
||  https://us-west-2.queue.amazonaws.com/1/queue2     ||
||  https://us-west-2.queue.amazonaws.com/1/queue3     ||
||  https://us-west-2.queue.amazonaws.com/1/queue4     ||
|+-----------------------------------------------------+|
||                  ResponseMetadata                   ||
|+-----------+-----------------------------------------+|
||  RequestId|  b04d5718-93e6-5503-8ef1-1eb7b7e402e1   ||
|+-----------+-----------------------------------------+|
"""

SIMPLE_DICT = {"Attributes":
  {"a": "0",
   "b": "345600",
   "c": "0",
   "d": "65536",
   "e": "1351044153",
   "f": "0",
   "ResponseMetadata": {"RequestId": "0c8d2786-b7b4-56e2-a823-6e80a404d6fd"}}
}


SIMPLE_DICT_TABLE = """\
-----------------------------------------------------------
|                      OperationName                      |
+---------------------------------------------------------+
||                      Attributes                       ||
|+---+-----------+-----+----------+----------------+-----+|
|| a |     b     |  c  |    d     |       e        |  f  ||
|+---+-----------+-----+----------+----------------+-----+|
||  0|  345600   |  0  |  65536   |  1351044153    |  0  ||
|+---+-----------+-----+----------+----------------+-----+|
|||                  ResponseMetadata                   |||
||+-----------+-----------------------------------------+||
|||  RequestId|  0c8d2786-b7b4-56e2-a823-6e80a404d6fd   |||
||+-----------+-----------------------------------------+||
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


class Object(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestTableFormatter(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        styler = Styler()
        self.table = MultiTable(initial_section=False,
                                column_separator='|', styler=styler,
                                auto_reformat=False)
        self.formatter = TableFormatter(Object(color='off'))
        self.formatter.table = self.table
        self.stream = six.StringIO()

    def assert_data_renders_to(self, data, table):
        self.formatter(Object(name='OperationName'),
                              data, self.stream)
        rendered = self.stream.getvalue()
        self.assertEqual(rendered, table)

    def test_list_table(self):
        self.assert_data_renders_to(data=SIMPLE_LIST, table=SIMPLE_LIST_TABLE)

    def test_dict_table(self):
        self.assert_data_renders_to(data=SIMPLE_DICT, table=SIMPLE_DICT_TABLE)

    def test_list_of_dicts(self):
        self.assert_data_renders_to(data=LIST_OF_DICTS,
                                    table=LIST_OF_DICTS_TABLE)
