**To remove a tag from the specified resource**

The following ``untag-resource`` example removes a tag(Key Value pair) to the notificationscontacts resource in the specified account. ::

    aws notificationscontacts untag-resource \
        --arn arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr \
        --tag-keys usage=CLI-Demo

This command produces no output.

For more information, see `Tagging your AWS User Notifications resources <https://docs.aws.amazon.com/notifications/latest/userguide/tagging-resources.html>`__ in the *AWS User Notifications User Guide*.