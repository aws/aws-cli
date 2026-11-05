**To create a static IP**

The following ``allocate-static-ip`` example creates the specified static IP, which can be attached to an instance. ::

    aws lightsail allocate-static-ip \
        --static-ip-name StaticIp-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "StaticIp-1",
                "resourceType": "StaticIp",
                "createdAt": 1571071325.076,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "AllocateStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571071325.274
            }
        ]
    }

For more information, see `Static IP addresses in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
