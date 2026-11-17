**To attach a TLS certificate to a load balancer**

The following ``attach-load-balancer-tls-certificate`` example attaches the load balancer TLS certificate ``Certificate2`` to the load balancer ``LoadBalancer-1``. ::

    aws lightsail attach-load-balancer-tls-certificate \
        --certificate-name Certificate2 \
        --load-balancer-name LoadBalancer-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "LoadBalancer-1",
                "resourceType": "LoadBalancer",
                "createdAt": 1571072255.416,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "Certificate2",
                "operationType": "AttachLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1571072255.416
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "Certificate2",
                "resourceType": "LoadBalancerTlsCertificate",
                "createdAt": 1571072255.416,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "LoadBalancer-1",
                "operationType": "AttachLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1571072255.416
            }
        ]
    }

For more information, see `Enable HTTPS with an SSL/TLS certificate for your Lightsail load balancer <https://docs.aws.amazon.com/lightsail/latest/userguide/create-tls-ssl-certificate-and-attach-to-lightsail-load-balancer-https.html>`__ in the *Amazon Lightsail User Guide*.
