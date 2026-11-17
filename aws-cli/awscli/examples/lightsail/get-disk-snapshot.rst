**To get information about a disk snapshot**

The following ``get-disk-snapshot`` example displays details about the disk snapshot ``Disk-1-1566839161``. ::

    aws lightsail get-disk-snapshot \
        --disk-snapshot-name Disk-1-1566839161

Output::

    {
        "diskSnapshot": {
            "name": "Disk-1-1566839161",
            "arn": "arn:aws:lightsail:us-west-2:123456789012:DiskSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "supportCode": "6EXAMPLE3362/snap-0EXAMPLE06100d09",
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
            "fromDiskArn": "arn:aws:lightsail:us-west-2:123456789012:Disk/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "isFromAutoSnapshot": false
        }
    }

For more information, see `Create Lightsail block storage disk snapshots for backup or baseline <https://docs.aws.amazon.com/lightsail/latest/userguide/create-block-storage-disk-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
