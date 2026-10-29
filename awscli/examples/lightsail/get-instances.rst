**To get information about all instances**

The following ``get-instances`` example displays details about all of the instances in the configured AWS Region. ::

    aws lightsail get-instances

Output::

    {
        "instances": [
            {
                "name": "Windows_Server_2022-1",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "62EXAMPLE362/i-0bEXAMPLE71a686b9",
                "createdAt": 1571332358.665,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "Instance",
                "tags": [],
                "blueprintId": "windows_server_2022",
                "blueprintName": "Windows Server 2022",
                "bundleId": "large_win_3_0",
                "isStaticIp": false,
                "privateIpAddress": "192.0.2.0",
                "publicIpAddress": "192.0.2.0",
                "hardware": {
                    "cpuCount": 1,
                    "disks": [
                        {
                            "createdAt": 1571332358.665,
                            "sizeInGb": 160,
                            "isSystemDisk": true,
                            "iops": 180,
                            "path": "/dev/sda1",
                            "attachedTo": "Windows_Server_2022-1",
                            "attachmentState": "attached"
                        },
                        {
                            "name": "my-disk-for-windows-server",
                            "arn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                            "supportCode": "6EXAMPLE3362/vol-0EXAMPLEb2b99ca3d",
                            "createdAt": 1571355063.494,
                            "location": {
                                "availabilityZone": "us-west-2a",
                                "regionName": "us-west-2"
                            },
                            "resourceType": "Disk",
                            "tags": [],
                            "sizeInGb": 128,
                            "isSystemDisk": false,
                            "iops": 384,
                            "path": "/dev/xvdf",
                            "state": "in-use",
                            "attachedTo": "Windows_Server_2022-1",
                            "isAttached": true,
                            "attachmentState": "attached"
                        }
                    ],
                    "ramSizeInGb": 8.0
                },
                "networking": {
                    "monthlyTransfer": {
                        "gbPerMonthAllocated": 3072
                    },
                    "ports": [
                        {
                            "fromPort": 80,
                            "toPort": 80,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        },
                        {
                            "fromPort": 22,
                            "toPort": 22,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        },
                        {
                            "fromPort": 3389,
                            "toPort": 3389,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        }
                    ]
                },
                "state": {
                    "code": 16,
                    "name": "running"
                },
                "username": "Administrator",
                "sshKeyName": "LightsailDefaultKeyPair"
            },
            {
                "name": "MEAN-1",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "supportCode": "6EXAMPLE3362/i-0EXAMPLEa407c97d3",
                "createdAt": 1570635023.124,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "Instance",
                "tags": [],
                "blueprintId": "mean",
                "blueprintName": "MEAN",
                "bundleId": "medium_3_0",
                "isStaticIp": false,
                "privateIpAddress": "192.0.2.0",
                "publicIpAddress": "192.0.2.0",
                "hardware": {
                    "cpuCount": 2,
                    "disks": [
                        {
                            "name": "Disk-1",
                            "arn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                            "supportCode": "6EXAMPLE3362/vol-0EXAMPLEf2f88b32f",
                            "createdAt": 1566585439.587,
                            "location": {
                                "availabilityZone": "us-west-2a",
                                "regionName": "us-west-2"
                            },
                            "resourceType": "Disk",
                            "tags": [
                                {
                                    "key": "test"
                                }
                            ],
                            "sizeInGb": 8,
                            "isSystemDisk": false,
                            "iops": 240,
                            "path": "/dev/xvdf",
                            "state": "in-use",
                            "attachedTo": "MEAN-1",
                            "isAttached": true,
                            "attachmentState": "attached"
                        },
                        {
                            "createdAt": 1570635023.124,
                            "sizeInGb": 80,
                            "isSystemDisk": true,
                            "iops": 240,
                            "path": "/dev/sda1",
                            "attachedTo": "MEAN-1",
                            "attachmentState": "attached"
                        }
                    ],
                    "ramSizeInGb": 4.0
                },
                "networking": {
                    "monthlyTransfer": {
                        "gbPerMonthAllocated": 4096
                    },
                    "ports": [
                        {
                            "fromPort": 80,
                            "toPort": 80,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        },
                        {
                            "fromPort": 22,
                            "toPort": 22,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        },
                        {
                            "fromPort": 443,
                            "toPort": 443,
                            "protocol": "tcp",
                            "accessFrom": "Anywhere (0.0.0.0/0)",
                            "accessType": "public",
                            "commonName": "",
                            "accessDirection": "inbound"
                        }
                    ]
                },
                "state": {
                    "code": 16,
                    "name": "running"
                },
                "username": "bitnami",
                "sshKeyName": "MyTestKey"
            }
        ]
    }

For more information, see `Virtual private server instances in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-instances-virtual-private-servers-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
