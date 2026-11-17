**To get information about all operations**

The following ``get-operations`` example displays details about all of the operations in the configured AWS Region. ::

    aws lightsail get-operations

Output::

    {
        "operations": [
            {
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
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1571678786.072,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "LoadBalancer-1",
                "operationType": "DetachInstancesFromLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1571679086.399
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571678786.071,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "WordPress-1",
                "operationType": "DetachInstancesFromLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1571679087.57
            }
        ]
    }

For more information, see `Virtual private server instances in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-instances-virtual-private-servers-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
