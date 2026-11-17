**To create a TLS certificate for a load balancer**

The following ``create-load-balancer-tls-certificate`` example creates a TLS certificate that is attached to the specified load balancer. The certificate created applies to the specified domains.
**Note:** Only two certificates can be created for a load balancer. ::

    aws lightsail create-load-balancer-tls-certificate \
        --certificate-alternative-names abc.example.com \
        --certificate-domain-name example.com \
        --certificate-name MySecondCertificate \
        --load-balancer-name MyFirstLoadBalancer

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "MySecondCertificate",
                "resourceType": "LoadBalancerTlsCertificate",
                "createdAt": 1569867364.971,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MyFirstLoadBalancer",
                "operationType": "CreateLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1569867365.219
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MyFirstLoadBalancer",
                "resourceType": "LoadBalancer",
                "createdAt": 1569867364.971,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MySecondCertificate",
                "operationType": "CreateLoadBalancerTlsCertificate",
                "status": "Succeeded",
                "statusChangedAt": 1569867365.219
            }
        ]
    }

For more information, see `Enable HTTPS with an SSL/TLS certificate for your Lightsail load balancer <https://docs.aws.amazon.com/lightsail/latest/userguide/create-tls-ssl-certificate-and-attach-to-lightsail-load-balancer-https.html>`__ in the *Amazon Lightsail User Guide*.
