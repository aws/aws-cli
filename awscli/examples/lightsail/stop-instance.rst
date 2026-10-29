**To stop an instance**

The following ``stop-instance`` example stops the specified instance. ::

    aws lightsail stop-instance \
        --instance-name WordPress-1

Output::

    {
        "operations": [
            {
                "id": "265357e2-2943-4d51-888a-1EXAMPLE7585",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1571695471.134,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "StopInstance",
                "status": "Started",
                "statusChangedAt": 1571695471.134
            }
        ]
    }

For more information, see `Start, stop, or reboot your Lightsail instance <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-start-stop-or-restart-your-instance-virtual-private-server.html>`__ in the *Amazon Lightsail User Guide*.
