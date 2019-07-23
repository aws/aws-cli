**To list the targets to which a policy is attached**

The following ``list-targets-for-policy`` example lists all targets, including groups, to which the specified policy is attached. ::

    aws iot list-targets-for-policy \
        --policy-name UpdateDeviceCertPolicy

Output::

    {
        "targets": [
            "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs"
        ]
    }

For more information, see `Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html>`__ in the *AWS IoT Developers Guide*.
