**To delete a load balancer**

The following ``delete-load-balancer`` example deletes the specified load balancer and any associated TLS certificates. ::

    aws lightsail delete-load-balancer \
        --load-balancer-name MyFirstLoadBalancer

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "MyFirstLoadBalancer",
                "resourceType": "LoadBalancer",
                "createdAt": 1569875092.125,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteLoadBalancer",
                "status": "Succeeded",
                "statusChangedAt": 1569875092.125
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MySecondCertificate",
                "resourceType": "LoadBalancerTlsCertificate",
                "createdAt": 1569875091.938,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "DeleteLoadBalancerTlsCertificate",
                "status": "Started",
                "statusChangedAt": 1569875091.938
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "MyFirstLoadBalancer",
                "resourceType": "LoadBalancer",
                "createdAt": 1569875091.94,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "DeleteLoadBalancerTlsCertificate",
                "status": "Started",
                "statusChangedAt": 1569875091.94
            }
        ]
    }

For more information, see `Delete Lightsail load balancers <https://docs.aws.amazon.com/lightsail/latest/userguide/delete-lightsail-load-balancer.html>`__ in the *Amazon Lightsail User Guide*.
