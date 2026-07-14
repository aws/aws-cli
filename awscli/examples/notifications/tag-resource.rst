**To add a tag to the specified resource**

The following ``tag-resource`` example add a tag(Key Value pair) to the notifications resource in the specified account. ::

    aws notifications tag-resource \
        --arn arn:aws:notifications::123456789012:configuration/a01jjzhee9p37n8gc2ke1mr5zjx \
        --tags usage=CLI-Demo,costcenter=usernotifications

This command produces no output.

For more information, see `Tagging your AWS User Notifications resources <https://docs.aws.amazon.com/notifications/latest/userguide/tagging-resources.html>`__ in the *AWS User Notifications User Guide*.