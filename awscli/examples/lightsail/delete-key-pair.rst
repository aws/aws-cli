**To delete a key pair**

The following ``delete-key-pair`` example deletes the specified key pair. ::

    aws lightsail delete-key-pair \
        --key-pair-name MyPersonalKeyPair

Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "MyPersonalKeyPair",
            "resourceType": "KeyPair",
            "createdAt": 1569874626.466,
            "location": {
                "availabilityZone": "all",
                "regionName": "us-west-2"
            },
            "isTerminal": true,
            "operationType": "DeleteKeyPair",
            "status": "Succeeded",
            "statusChangedAt": 1569874626.685
        }
    }

For more information, see `Control secure instance connectivity with Lightsail SSH keys <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-managing-ssh-keys.html>`__ in the *Amazon Lightsail User Guide*.
