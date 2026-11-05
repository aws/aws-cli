**To query the thing index**

The following ``search-index`` example queries the ``AWS_Things`` index for things that have a type of ``LightBulb``. ::

    aws iot search-index \
        --index-name "AWS_Things" \
        --query-string "thingTypeName:LightBulb"

Output::

    {
        "things": [
            {
                "thingName": "MyLightBulb",
                "thingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "thingTypeName": "LightBulb",
                "thingGroupNames": [
                    "LightBulbs",
                    "DeadBulbs"
                ],
                "attributes": {
                    "model": "123",
                    "wattage": "75"
                },
                "connectivity": {
                    "connected": false
                }
            },
            {
                "thingName": "ThirdBulb",
                "thingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "thingTypeName": "LightBulb",
                "attributes": {
                    "model": "123",
                    "wattage": "75"
                },
                "connectivity": {
                    "connected": false
                }
            },
            {
                "thingName": "MyOtherLightBulb",
                "thingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "thingTypeName": "LightBulb",
                "attributes": {
                    "model": "123",
                    "wattage": "75"
                },
                "connectivity": {
                    "connected": false
                }
            }
        ]
    }

For more information, see `Managing Thing Indexing <https://docs.aws.amazon.com/iot/latest/developerguide/managing-index.html>`__ in the *AWS IoT Developer Guide*.
