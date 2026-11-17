**Example 1: To create a thing group**

The following ``create-thing-group`` example creates a thing group named ``LightBulbs`` with a description and two attributes. ::

    aws iot create-thing-group \
        --thing-group-name LightBulbs \
        --thing-group-properties "thingGroupDescription=\"Generic bulb group\", attributePayload={attributes={Manufacturer=AnyCompany,wattage=60}}"

Output::

    {
        "thingGroupName": "LightBulbs",
        "thingGroupArn": "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs",
        "thingGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

**Example 2: To create a thing group that's part of a parent group**

The following ``create-thing-group`` example creates a thing group named ``HalogenBulbs`` that has a parent thing group named ``LightBulbs``. ::

    aws iot create-thing-group \
        --thing-group-name HalogenBulbs \
        --parent-group-name LightBulbs

Output::

    {
        "thingGroupName": "HalogenBulbs",
        "thingGroupArn": "arn:aws:iot:us-west-2:123456789012:thinggroup/HalogenBulbs",
        "thingGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html>`__ in the *AWS IoT Developers Guide*.
