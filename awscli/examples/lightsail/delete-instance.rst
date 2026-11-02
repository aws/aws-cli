**To delete an instance**

The following ``delete-instance`` example deletes the specified instance. ::

    aws lightsail delete-instance \
        --instance-name WordPress-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Disk-1",
                "resourceType": "Disk",
                "createdAt": 1569874357.469,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "WordPress-1",
                "operationType": "DetachDisk",
                "status": "Started",
                "statusChangedAt": 1569874357.469
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1569874357.465,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Disk-1",
                "operationType": "DetachDisk",
                "status": "Started",
                "statusChangedAt": 1569874357.465
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1569874357.829,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteInstance",
                "status": "Succeeded",
                "statusChangedAt": 1569874357.829
            }
        ]
    }

For more information, see `Delete Lightsail instances <https://docs.aws.amazon.com/lightsail/latest/userguide/delete-an-amazon-lightsail-instance.html>`__ in the *Amazon Lightsail User Guide*.
