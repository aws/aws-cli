**To create a load balancer**

The following ``create-load-balancer`` example creates a load balancer with a TLS certificate. The TLS certificate applies to the specified domains, and routes traffic to instances on port 80. ::

    aws lightsail create-load-balancer \
        --certificate-alternative-names www.example.com test.example.com \
        --certificate-domain-name example.com \
        --certificate-name Certificate-1 \
        --instance-port 80 \
        --load-balancer-name LoadBalancer-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1569867169.406,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateLoadBalancer",
                "status": "Started",
                "statusChangedAt": 1569867169.406
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancerTlsCertificate",
                "createdAt": 1569867170.193,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "LoadBalancer-1",
                "operationType": "CreateLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1569867170.54
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1569867170.193,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "Certificate-1",
                "operationType": "CreateLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1569867170.54
            }
        ]
    }

For more information, see `Lightsail load balancers <https://lightsail.aws.amazon.com/ls/docs/en_us/articles/understanding-lightsail-load-balancers>`__ in the *Lightsail Developer Guide*.
