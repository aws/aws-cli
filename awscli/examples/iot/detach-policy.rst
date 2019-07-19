**To detach a policy from a thing group**

The following ``detach-policy`` example detaches the specified policy from a thing group and, by extension, from all things in that group and any of the group's child groups. ::

    aws iot detach-policy \
        --target "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs" \
        --policy-name "MyFirstGroup_Core-policy"

This command produces no output.

For more information, see `Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html>`__ in the *AWS IoT Developers Guide*.
