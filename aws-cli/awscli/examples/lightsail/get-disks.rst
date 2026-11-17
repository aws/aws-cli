**To get information about all block storage disks**

The following ``get-disks`` example displays details about all of the disks in the configured AWS Region. ::

    aws lightsail get-disks

Output::

    {
        "disks": [
            {
                "name": "Disk-2",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/vol-0EXAMPLE929602087",
                "createdAt": 1571090461.634,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "Disk",
                "tags": [],
                "sizeInGb": 8,
                "isSystemDisk": false,
                "iops": 100,
                "state": "available",
                "isAttached": false,
                "attachmentState": "detached"
            },
            {
                "name": "Disk-1",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "supportCode": "6EXAMPLE3362/vol-0EXAMPLEf2f88b32f",
                "createdAt": 1566585439.587,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "resourceType": "Disk",
                "tags": [],
                "sizeInGb": 8,
                "isSystemDisk": false,
                "iops": 100,
                "path": "/dev/xvdf",
                "state": "in-use",
                "attachedTo": "WordPress_Multisite-1",
                "isAttached": true,
                "attachmentState": "attached"
            }
        ]
    }

For more information, see `Expand storage and performance with Lightsail block storage disks <https://docs.aws.amazon.com/lightsail/latest/userguide/elastic-block-storage-and-ssd-disks-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
