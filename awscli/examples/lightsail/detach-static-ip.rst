**To detach a static IP from an instance**

The following ``detach-static-ip`` example detaches static IP ``StaticIp-1`` from any attached instance. ::

    aws lightsail detach-static-ip \
        --static-ip-name StaticIp-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "StaticIp-1",
                "resourceType": "StaticIp",
                "createdAt": 1571088261.999,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "MEAN-1",
                "operationType": "DetachStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571088261.999
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "MEAN-1",
                "resourceType": "Instance",
                "createdAt": 1571088262.022,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "StaticIp-1",
                "operationType": "DetachStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571088262.022
            }
        ]
    }

For more information, see `Static IP addresses in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
