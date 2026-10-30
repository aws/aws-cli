**To delete known host keys from an instance**

The following ``delete-known-host-keys`` example deletes the known host key from the specified instance. ::

    aws lightsail delete-known-host-keys \
        --instance-name Instance-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "Instance-1",
                "resourceType": "Instance",
                "createdAt": 1569874760.201,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": true,
                "operationType": "DeleteKnownHostKeys",
                "status": "Succeeded",
                "statusChangedAt": 1569874760.201
            }
        ]
    }

For more information, see `Troubleshooting connection issues with the Amazon Lightsail browser-based SSH or RDP client <https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-troubleshooting-browser-based-ssh-rdp-client-connection>`__ in the *Lightsail Dev Guide*.
