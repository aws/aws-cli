**To attach a block storage disk to an instance**

The following ``attach-disk`` example attaches disk ``Disk-1`` to instance ``WordPress_Multisite-1`` with the disk path of ``/dev/xvdf``. ::

    aws lightsail attach-disk \
        --disk-name Disk-1 \
        --disk-path /dev/xvdf \
        --instance-name WordPress_Multisite-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Disk-1",
                "resourceType": "Disk",
                "createdAt": 1571071465.472,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "WordPress_Multisite-1",
                "operationType": "AttachDisk",
                "status": "Started",
                "statusChangedAt": 1571071465.472
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "WordPress_Multisite-1",
                "resourceType": "Instance",
                "createdAt": 1571071465.474,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Disk-1",
                "operationType": "AttachDisk",
                "status": "Started",
                "statusChangedAt": 1571071465.474
            }
        ]
    }

For more information, see `Create and attach Lightsail block storage disks to Linux instances <https://docs.aws.amazon.com/lightsail/latest/userguide/create-and-attach-additional-block-storage-disks-linux-unix.html>`__ in the *Amazon Lightsail User Guide*.
