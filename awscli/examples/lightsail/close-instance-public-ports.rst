**To close firewall ports for an instance**

The following ``close-instance-public-ports`` example closes TCP port ``22`` on instance ``MEAN-2``. ::

    aws lightsail close-instance-public-ports \
        --instance-name MEAN-2 \
        --port-info fromPort=22,protocol=TCP,toPort=22

Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "MEAN-2",
            "resourceType": "Instance",
            "createdAt": 1571072845.737,
            "location": {
                "availabilityZone": "us-west-2a",
                "regionName": "us-west-2"
            },
            "isTerminal": true,
            "operationDetails": "22/tcp",
            "operationType": "CloseInstancePublicPorts",
            "status": "Succeeded",
            "statusChangedAt": 1571072845.737
        }
    }

For more information, see `Control instance traffic with firewalls in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
