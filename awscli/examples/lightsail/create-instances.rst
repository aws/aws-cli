**Example 1: To create a single instance**

The following ``create-instances`` example creates an instance in the specified AWS Region and Availability Zone, using the WordPress blueprint, and the $5.00 USD bundle. ::

    aws lightsail create-instances \
        --instance-names Instance-1 \
        --availability-zone us-west-2a \
        --blueprint-id wordpress \
        --bundle-id nano_3_0

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Instance-1",
                "resourceType": "Instance",
                "createdAt": 1569447986.061,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateInstance",
                "status": "Started",
                "statusChangedAt": 1569447986.061
            }
        ]
    }

For more information, see `Create a Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/how-to-create-amazon-lightsail-instance-virtual-private-server-vps.html>`__ in the *Amazon Lightsail User Guide*.

**Example 2: To create multiple instances at one time**

The following ``create-instances`` example creates three instances in the specified AWS Region and Availability Zone, using the WordPress blueprint, and the $5.00 USD bundle. ::

    aws lightsail create-instances \
        --instance-names {"Instance1","Instance2","Instance3"} \
        --availability-zone us-west-2a \
        --blueprint-id wordpress \
        --bundle-id nano_3_0

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "Instance1",
                "resourceType": "Instance",
                "createdAt": 1569448780.054,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateInstance",
                "status": "Started",
                "statusChangedAt": 1569448780.054
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "Instance2",
                "resourceType": "Instance",
                "createdAt": 1569448780.054,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateInstance",
                "status": "Started",
                "statusChangedAt": 1569448780.054
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "resourceName": "Instance3",
                "resourceType": "Instance",
                "createdAt": 1569448780.054,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateInstance",
                "status": "Started",
                "statusChangedAt": 1569448780.054
            }
        ]
    }

For more information, see `Create a Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/how-to-create-amazon-lightsail-instance-virtual-private-server-vps.html>`__ in the *Amazon Lightsail User Guide*.
