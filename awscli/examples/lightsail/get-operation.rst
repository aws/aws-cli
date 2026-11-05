**To get information about a single operation**

The following ``get-operation`` example displays details about the specified operation. ::

    aws lightsail get-operation \
        --operation-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111


Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "Instance-1",
            "resourceType": "Instance",
            "createdAt": 1571679872.404,
            "location": {
                "availabilityZone": "us-west-2a",
                "regionName": "us-west-2"
            },
            "isTerminal": true,
            "operationType": "CreateInstance",
            "status": "Succeeded",
            "statusChangedAt": 1571679890.304
        }
    }

For more information, see `Virtual private server instances in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-instances-virtual-private-servers-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
