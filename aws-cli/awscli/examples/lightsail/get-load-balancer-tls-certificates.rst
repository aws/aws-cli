**To get information about TLS certificates for a load balancer**

The following ``get-load-balancer-tls-certificates`` example displays details about the TLS certificates for the specified load balancer. ::

    aws lightsail get-load-balancer-tls-certificates \
        --load-balancer-name LoadBalancer-1

Output::

    {
        "tlsCertificates": [
            {
                "name": "example-com",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:LoadBalancerTlsCertificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/arn:aws:acm:us-west-2:123456789111:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "createdAt": 1571678025.3,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "LoadBalancerTlsCertificate",
                "loadBalancerName": "LoadBalancer-1",
                "isAttached": false,
                "status": "ISSUED",
                "domainName": "example.com",
                "domainValidationRecords": [
                    {
                        "name": "_dEXAMPLE4ede046a0319eb44a4eb3cbc.example.com.",
                        "type": "CNAME",
                        "value": "_bEXAMPLE0899fb7b6bf79d9741d1a383.hkvuiqjoua.acm-validations.aws.",
                        "validationStatus": "SUCCESS",
                        "domainName": "example.com"
                    }
                ],
                "issuedAt": 1571678070.0,
                "issuer": "Amazon",
                "keyAlgorithm": "RSA-2048",
                "notAfter": 1605960000.0,
                "notBefore": 1571616000.0,
                "serial": "00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff",
                "signatureAlgorithm": "SHA256WITHRSA",
                "subject": "CN=example.com",
                "subjectAlternativeNames": [
                    "example.com"
                ]
            }
        ]
    }

For more information, see `SSL/TLS certificates in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-tls-ssl-certificates-in-lightsail-https.html>`__ in the *Amazon Lightsail User Guide*.
