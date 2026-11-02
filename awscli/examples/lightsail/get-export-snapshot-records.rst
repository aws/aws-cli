**To get the records of snapshots exported to Amazon EC2**

The following ``get-export-snapshot-records`` example displays details about Amazon Lightsail instance or disk snapshots exported to Amazon EC2. ::

    aws lightsail get-export-snapshot-records

Output::

    {
        "exportSnapshotRecords": [
            {
                "name": "ExportSnapshotRecord-d2da10ce-0b3c-4ae1-ab3a-2EXAMPLEa586",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:ExportSnapshotRecord/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "createdAt": 1543534665.678,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "ExportSnapshotRecord",
                "state": "Succeeded",
                "sourceInfo": {
                    "resourceType": "InstanceSnapshot",
                    "createdAt": 1540339310.706,
                    "name": "WordPress-512MB-Oregon-1-1540339219",
                    "arn": "arn:aws:lightsail:us-west-2:123456789012:InstanceSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                    "fromResourceName": "WordPress-512MB-Oregon-1",
                    "fromResourceArn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "instanceSnapshotInfo": {
                        "fromBundleId": "nano_2_0",
                        "fromBlueprintId": "wordpress_4_9_8",
                        "fromDiskInfo": [
                            {
                                "path": "/dev/sda1",
                                "sizeInGb": 20,
                                "isSystemDisk": true
                            }
                        ]
                    }
                },
                "destinationInfo": {
                    "id": "ami-0EXAMPLEc0d65058e",
                    "service": "Aws::EC2::Image"
                }
            },
            {
                "name": "ExportSnapshotRecord-1c94e884-40ff-4fe1-9302-0EXAMPLE14c2",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:ExportSnapshotRecord/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "createdAt": 1543432110.2,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "ExportSnapshotRecord",
                "state": "Succeeded",
                "sourceInfo": {
                    "resourceType": "InstanceSnapshot",
                    "createdAt": 1540833603.545,
                    "name": "LAMP_PHP_5-512MB-Oregon-1-1540833565",
                    "arn": "arn:aws:lightsail:us-west-2:123456789012:InstanceSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                    "fromResourceName": "LAMP_PHP_5-512MB-Oregon-1",
                    "fromResourceArn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                    "instanceSnapshotInfo": {
                        "fromBundleId": "nano_2_0",
                        "fromBlueprintId": "lamp_5_6_37_2",
                        "fromDiskInfo": [
                            {
                                "path": "/dev/sda1",
                                "sizeInGb": 20,
                                "isSystemDisk": true
                            }
                        ]
                    }
                },
                "destinationInfo": {
                    "id": "ami-0EXAMPLE7c5ec84e2",
                    "service": "Aws::EC2::Image"
                }
            }
        ]
    }

For more information, see `Track snapshot export status in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-task-monitor.html>`__ in the *Amazon Lightsail User Guide*.
