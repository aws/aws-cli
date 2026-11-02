**To open firewall ports for an instance**

The following ``open-instance-public-ports`` example opens TCP port 22 on the specified instance. ::

    aws lightsail open-instance-public-ports \
        --instance-name MEAN-2 \
        --port-info fromPort=22,protocol=TCP,toPort=22

Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "MEAN-2",
            "resourceType": "Instance",
            "createdAt": 1571072906.849,
            "location": {
                "availabilityZone": "us-west-2a",
                "regionName": "us-west-2"
            },
            "isTerminal": true,
            "operationDetails": "22/tcp",
            "operationType": "OpenInstancePublicPorts",
            "status": "Succeeded",
            "statusChangedAt": 1571072906.849
        }
    }

For more information, see `Control instance traffic with firewalls in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
