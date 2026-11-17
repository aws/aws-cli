**To attach instances to a load balancer**

The following ``attach-instances-to-load-balancer`` example attaches instances ``MEAN-1``, ``MEAN-2``, and ``MEAN-3`` to the load balancer ``LoadBalancer-1``. ::

    aws lightsail attach-instances-to-load-balancer \
        --instance-names {"MEAN-1","MEAN-2","MEAN-3"} \
        --load-balancer-name LoadBalancer-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571071699.892,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "MEAN-2",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.892
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MEAN-2",
                "resourceType": "Instance",
                "createdAt": 1571071699.887,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "LoadBalancer-1",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.887
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571071699.882,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "MEAN-3",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.882
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "resourceName": "MEAN-3",
                "resourceType": "Instance",
                "createdAt": 1571071699.901,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "LoadBalancer-1",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.901
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571071699.885,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "MEAN-1",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.885
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "resourceName": "MEAN-1",
                "resourceType": "Instance",
                "createdAt": 1571071699.901,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "LoadBalancer-1",
                "operationType": "AttachInstancesToLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1571071699.901
            }
        ]
    }

For more information, see `Distribute web traffic with a Lightsail load balancer <https://docs.aws.amazon.com/lightsail/latest/userguide/create-lightsail-load-balancer-and-attach-lightsail-instances.html>`__ in the *Amazon Lightsail User Guide*.
