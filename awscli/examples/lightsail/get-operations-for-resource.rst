**To get all operations for a resource**

The following ``get-operations-for-resource`` example displays details about all operations for the specified resource. ::

    aws lightsail get-operations-for-resource \
        --resource-name LoadBalancer-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571678786.071,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MEAN-1",
                "operationType": "DetachInstancesFromLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1571679087.57
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571678782.784,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MEAN-1",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1571678798.465
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571678775.297,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MEAN-3",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1571678842.806
            }
        ]
    }

For more information, see `Distribute web traffic with Lightsail load balancers <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-lightsail-load-balancers.html>`__ in the *Amazon Lightsail User Guide*.
