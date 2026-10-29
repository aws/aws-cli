**To remove a tag key from a resource**

The following ``untag-resource`` example removes the tag ``MyTag`` and its value from the thing group ``LightBulbs``. ::

    aws iot untag-resource \
        --resource-arn "arn:aws:iot:us-west-2:123456789012:thinggroup/LightBulbs" \
        --tag-keys MyTag

This command produces no output.

For more information, see `Tagging Your AWS IoT Resources <https://docs.aws.amazon.com/iot/latest/developerguide/tagging-iot.html>`__ in the *AWS IoT Developer Guide*.
