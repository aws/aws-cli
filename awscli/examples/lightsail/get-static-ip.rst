**To get information about a static IP**

The following ``get-static-ip`` example displays details about the specified static IP. ::

    aws lightsail get-static-ip \
        --static-ip-name StaticIp-1

Output::

    {
        "staticIp": {
            "name": "StaticIp-1",
            "arn": "arn:aws:lightsail:us-west-2:123456789012:StaticIp/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "supportCode": "6EXAMPLE3362/192.0.2.0",
            "createdAt": 1571071325.076,
            "location": {
                "availabilityZone": "all",
                "regionName": "us-west-2"
            },
            "resourceType": "StaticIp",
            "ipAddress": "192.0.2.0",
            "isAttached": false
        }
    }

For more information, see `Static IP addresses in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
