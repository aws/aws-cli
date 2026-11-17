**To create a snapshot of an instance**

The following ``create-instance-snapshot`` example creates a snapshot from the specified instance. ::

    aws lightsail create-instance-snapshot \
        --instance-name WordPress-1 \
        --instance-snapshot-name WordPress-Snapshot-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "WordPress-Snapshot-1",
                "resourceType": "InstanceSnapshot",
                "createdAt": 1569866438.48,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "WordPress-1",
                "operationType": "CreateInstanceSnapshot",
                "status": "Started",
                "statusChangedAt": 1569866438.48
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1569866438.48,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "WordPress-Snapshot-1",
                "operationType": "CreateInstanceSnapshot",
                "status": "Started",
                "statusChangedAt": 1569866438.48
            }
        ]
    }

For more information, see `Back up Linux/Unix Lightsail instances with snapshots <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-a-snapshot-of-your-instance.html>`__ in the *Amazon Lightsail User Guide*.
