**To create a device pool**

The following ``create-device-pool`` example creates an Android device pool for a project. ::

    aws devicefarm create-device-pool \
        --name pool1 \
        --rules file://device-pool-rules.json \
        --project-arn "arn:aws:devicefarm:us-west-2:123456789012:project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

You can get the project ARN from the output of ``create-project`` or ``list-projects``. The file ``device-pool-rules.json`` is a JSON document in the current folder that specifies the device platform.

Contents of ``device-pool-rules.json``::

    [
        {
            "attribute": "PLATFORM",
            "operator": "EQUALS",
            "value": "\"ANDROID\""
        }
    ]

Output::

    {
        "devicePool": {
            "rules": [
                {
                    "operator": "EQUALS",
                    "attribute": "PLATFORM",
                    "value": "\"ANDROID\""
                }
            ],
            "type": "PRIVATE",
            "name": "pool1",
            "arn": "arn:aws:devicefarm:us-west-2:123456789012:devicepool:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

For more information, see `Creating a device pool in AWS Device Farm <https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-create-device-pool.html>`__ in the *AWS Device Farm Developer Guide*.
