**To create a block storage disk**

The following ``create-disk`` example creates a block storage disk ``Disk-1`` in the specified AWS Region and Availability Zone, with 32 GB of storage space. ::

    aws lightsail create-disk \
        --disk-name Disk-1 \
        --availability-zone us-west-2a \
        --size-in-gb 32

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Disk-1",
                "resourceType": "Disk",
                "createdAt": 1569449220.36,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateDisk",
                "status": "Started",
                "statusChangedAt": 1569449220.588
            }
        ]
    }

For more information, see `Create and attach Lightsail block storage disks to Linux instances <https://docs.aws.amazon.com/lightsail/latest/userguide/create-and-attach-additional-block-storage-disks-linux-unix.html>`__ in the *Amazon Lightsail User Guide*.
