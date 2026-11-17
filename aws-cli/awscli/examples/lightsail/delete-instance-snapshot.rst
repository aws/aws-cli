**To delete a snapshot of an instance**

The following ``delete-instance-snapshot`` example deletes the specified snapshot of an instance. ::

    aws lightsail delete-instance-snapshot \
        --instance-snapshot-name WordPress-1-Snapshot-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "WordPress-1-Snapshot-1",
                "resourceType": "InstanceSnapshot",
                "createdAt": 1569874524.562,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteInstanceSnapshot",
                "status": "Succeeded",
                "statusChangedAt": 1569874524.562
            }
        ]
    }

For more information, see `Delete unused Lightsail snapshots to avoid monthly charges <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-deleting-snapshots.html>`__ in the *Amazon Lightsail User Guide*.
