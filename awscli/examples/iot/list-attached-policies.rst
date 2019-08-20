**To list the policies attached to a group**

The following ``list-attached-policies`` example lists the policies that are attached to the specified group. ::

    aws iot list-attached-policies \
        --target "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs"

Output::

    {
        "policies": [
            {
                "policyName": "UpdateDeviceCertPolicy",
                "policyArn": "arn:aws:iot:us-west-2:123456789012:policy/UpdateDeviceCertPolicy"
            }
        ]
    }

For more information, see `Thing Groups <https://docs.aws.amazon.com/iot/latest/developerguide/thing-groups.html>`__ in the *AWS IoT Developers Guide*.
