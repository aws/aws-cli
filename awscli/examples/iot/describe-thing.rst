**To display detailed information about a thing**

The following ``describe-thing`` example display information about a thing (device) that is defined in the AWS IoT registry for your AWS account.

    aws iot describe-thing \
        --thing-name "MyLightBulb"

Output::

    {
        "defaultClientId": "MyLightBulb",
        "thingName": "MyLightBulb",
        "thingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "thingArn": "arn:aws:iot:us-west-2:123456789012:thing/MyLightBulb",
        "thingTypeName": "LightBulb",
        "attributes": {
            "model": "123",
            "wattage": "75"
        },
        "version": 1
    }

For more information, see `How to Manage Things with the Registry <https://docs.aws.amazon.com/iot/latest/developerguide/thing-registry.html>`__ in the *AWS IoT Developers Guide*.
