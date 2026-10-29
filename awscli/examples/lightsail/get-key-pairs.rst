**To get information about all key pairs**

The following ``get-key-pairs`` example displays details about all of the key pairs in the configured AWS Region. ::

    aws lightsail get-key-pairs

Output::

    {
        "keyPairs": [
            {
                "name": "MyKey1",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:KeyPair/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/MyKey1",
                "createdAt": 1571255026.975,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "KeyPair",
                "tags": [],
                "fingerprint": "00:11:22:33:44:55:66:77:88:99:aa:bb:cc:dd:ee:ff:gg:hh:ii:jj"
            }
        ]
    }

For more information, see `Manage SSH key pairs and connect to your Lightsail instances <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-ssh-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
