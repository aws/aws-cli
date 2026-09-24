**To add a tag to the specified resource**

The following ``tag-resource`` example add a tag(Key Value pair) to the notificationscontacts resource in the specified account. ::

    aws notificationscontacts tag-resource \
        --arn arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr \
        --tags usage=CLI-Demo,costcenter=usernotifications

This command produces no output.

For more information, see `Tagging your AWS User Notifications resources <https://docs.aws.amazon.com/notifications/latest/userguide/tagging-resources.html>`__ in the *AWS User Notifications User Guide*.