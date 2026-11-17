**To delete a static IP**

The following ``release-static-ip`` example deletes the specified static IP. ::

    aws lightsail release-static-ip \
        --static-ip-name StaticIp-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "StaticIp-1",
                "resourceType": "StaticIp",
                "createdAt": 1571694962.003,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "ReleaseStaticIp",
                "status": "Succeeded",
                "statusChangedAt": 1571694962.003
            }
        ]
    }

For more information, see `Static IP addresses in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
