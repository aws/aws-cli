**To start an instance**

The following ``start-instance`` example starts the specified instance. ::

    aws lightsail start-instance \
        --instance-name WordPress-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1571695583.463,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "StartInstance",
                "status": "Started",
                "statusChangedAt": 1571695583.463
            }
        ]
    }

For more information, see `Start, stop, or reboot your Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-start-stop-or-restart-your-instance-virtual-private-server.html>`__ in the *Amazon Lightsail User Guide*.
