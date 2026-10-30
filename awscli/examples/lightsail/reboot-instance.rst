**To reboot an instance**

The following ``reboot-instance`` example reboots the specified instance. ::

    aws lightsail reboot-instance \
        --instance-name MEAN-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "MEAN-1",
                "resourceType": "Instance",
                "createdAt": 1571694445.49,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationDetails": "",
                "operationType": "RebootInstance",
                "status": "Succeeded",
                "statusChangedAt": 1571694445.49
            }
        ]
    }

For more information, see `Start, stop, or reboot your Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-start-stop-or-restart-your-instance-virtual-private-server.html>`__ in the *Amazon Lightsail User Guide*.
