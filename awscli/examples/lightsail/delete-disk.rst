**To delete a block storage disk**

The following ``delete-disk`` example deletes the specified block storage disk. ::

    aws lightsail delete-disk \
        --disk-name Disk-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Disk-1",
                "resourceType": "Disk",
                "createdAt": 1569872887.864,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteDisk",
                "status": "Succeeded",
                "statusChangedAt": 1569872887.864
            }
        ]
    }

For more information, see `Detach and delete Lightsail block storage disks <https://docs.aws.amazon.com/lightsail/latest/userguide/detach-and-delete-block-storage-disks.html>`__ in the *Amazon Lightsail User Guide*.
