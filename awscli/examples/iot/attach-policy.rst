**To attach a policy to a thing group**

The following ``attach-policy`` example attaches a policy named ``UpdateDeviceCertPolicy`` to a thing group. ::

    aws iot attach-policy \
        --target "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs" \
        --policy-name "UpdateDeviceCertPolicy"

This command does not produce any output.

For more information, see `Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html>`__ in the *AWS IoT Developers Guide*.

