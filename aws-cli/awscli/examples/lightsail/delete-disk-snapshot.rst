**To delete a snapshot of a block storage disk**

The following ``delete-disk-snapshot`` example deletes the specified snapshot of a block storage disk. ::

    aws lightsail delete-disk-snapshot \
        --disk-snapshot-name DiskSnapshot-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "DiskSnapshot-1",
                "resourceType": "DiskSnapshot",
                "createdAt": 1569873552.79,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteDiskSnapshot",
                "status": "Succeeded",
                "statusChangedAt": 1569873552.79
            }
        ]
    }

For more information, see `Delete unused Lightsail snapshots to avoid monthly charges <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-deleting-snapshots.html>`__ in the *Amazon Lightsail User Guide*.
