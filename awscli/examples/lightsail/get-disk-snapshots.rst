**To get information about all disk snapshots**

The following ``get-disk-snapshots`` example displays details about all of the disk snapshots in the configured AWS Region. ::

    aws lightsail get-disk-snapshots

Output::

    {
        "diskSnapshots": [
            {
                "name": "Disk-2-1571090588",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:DiskSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/snap-0EXAMPLE1ca192a4",
                "createdAt": 1571090591.226,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "DiskSnapshot",
                "tags": [],
                "sizeInGb": 8,
                "state": "completed",
                "progress": "100%",
                "fromDiskName": "Disk-2",
                "fromDiskArn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "isFromAutoSnapshot": false
            },
            {
                "name": "Disk-1-1566839161",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:DiskSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "supportCode": "6EXAMPLE3362/snap-0EXAMPLEe06100d09",
                "createdAt": 1566839163.749,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "DiskSnapshot",
                "tags": [],
                "sizeInGb": 8,
                "state": "completed",
                "progress": "100%",
                "fromDiskName": "Disk-1",
                "fromDiskArn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "isFromAutoSnapshot": false
            }
        ]
    }

For more information, see `Create Lightsail block storage disk snapshots for backup or baseline <https://docs.aws.amazon.com/lightsail/latest/userguide/create-block-storage-disk-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
