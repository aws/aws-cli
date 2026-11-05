**To get information about all static IPs**

The following ``get-static-ips`` example displays details about all of the static IPs in the configured AWS Region. ::

    aws lightsail get-static-ips

Output::

    {
        "staticIps": [
            {
                "name": "StaticIp-1",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:StaticIp/2257cd76-1f0e-4ac0-8EXAMPLE16f9423ad",
                "supportCode": "6EXAMPLE3362/192.0.2.0",
                "createdAt": 1571071325.076,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "StaticIp",
                "ipAddress": "192.0.2.0",
                "isAttached": false
            },
            {
                "name": "StaticIP-2",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:StaticIp/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/192.0.2.2",
                "createdAt": 1568305385.681,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "StaticIp",
                "ipAddress": "192.0.2.2",
                "attachedTo": "WordPress-1",
                "isAttached": true
            }
        ]
    }

For more information, see `Static IP addresses in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
