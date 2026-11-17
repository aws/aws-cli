**To create a dynamic thing group**

The following ``create-dynamic-thing-group`` example creates a dynamic thing group that contains any thing with a temperature attribute that is greater than 60 degrees. You must enable AWS IoT fleet indexing before you can use dynamic thing groups. ::

    aws iot create-dynamic-thing-group \
        --thing-group-name "RoomTooWarm" \
        --query-string "attributes.temperature>60"

Output::

    {
        "thingGroupName": "RoomTooWarm",
        "thingGroupArn": "arn:aws:iot:us-west-2:123456789012:thinggroup/RoomTooWarm",
        "thingGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "indexName": "AWS_Things",
        "queryString": "attributes.temperature>60",
        "queryVersion": "2017-09-30"
    }

For more information, see `Dynamic Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/dynamic-thing-groups.html>`__ in the *AWS IoT Developers Guide*.

