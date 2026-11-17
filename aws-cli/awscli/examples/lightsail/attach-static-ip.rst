**To attach a static IP to an instance**

The following ``attach-static-ip`` example attaches static IP ``StaticIp-1`` to instance ``MEAN-1``. ::

    aws lightsail attach-static-ip \
        --static-ip-name StaticIp-1 \
        --instance-name MEAN-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "StaticIp-1",
                "resourceType": "StaticIp",
                "createdAt": 1571072569.375,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MEAN-1",
                "operationType": "AttachStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571072569.375
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MEAN-1",
                "resourceType": "Instance",
                "createdAt": 1571072569.376,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "StaticIp-1",
                "operationType": "AttachStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571072569.376
            }
        ]
    }

For more information, see `Create and attach a static IP to your Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html>`__ in the *Amazon Lightsail User Guide*.
