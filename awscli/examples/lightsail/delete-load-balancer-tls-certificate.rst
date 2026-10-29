**To delete a TLS certificate for a load balancer**

The following ``delete-load-balancer-tls-certificate`` example deletes the specifie TLS certificate from the specified load balancer. ::

    aws lightsail delete-load-balancer-tls-certificate \
        --load-balancer-name MyFirstLoadBalancer \
        --certificate-name MyFirstCertificate

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "MyFirstCertificate",
                "resourceType": "LoadBalancerTlsCertificate",
                "createdAt": 1569874989.48,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "DeleteLoadBalancerTlsCertificate",
                "status": "Started",
                "statusChangedAt": 1569874989.48
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MyFirstLoadBalancer",
                "resourceType": "LoadBalancer",
                "createdAt": 1569874989.48,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "DeleteLoadBalancerTlsCertificate",
                "status": "Started",
                "statusChangedAt": 1569874989.48
            }
        ]
    }

For more information, see `SSL/TLS certificates in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-tls-ssl-certificates-in-lightsail-https.html>`__ in the *Amazon Lightsail User Guide*.
