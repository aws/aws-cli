**To remove a tag from the specified resource**

The following ``untag-resource`` example removes a tag(Key Value pair) to the notifications resource in the specified account. ::

    aws notifications untag-resource \
        --arn arn:aws:notifications::123456789012:configuration/a01jjzhee9p37n8gc2ke1mr5zjx \
        --tag-keys usage=CLI-Demo

This command produces no output.

For more information, see `Tagging your AWS User Notifications resources <https://docs.aws.amazon.com/notifications/latest/userguide/tagging-resources.html>`__ in the *AWS User Notifications User Guide*.