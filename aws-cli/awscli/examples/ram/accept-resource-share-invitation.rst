**To accept a resource share invitation**

The following ``accept-resource-share-invitation`` example accepts the specified resource share invitation. Principals in the invited account can immediately start using the resources in the share. ::

    aws ram accept-resource-share-invitation \
        --resource-share-invitation-arn arn:aws:ram:us-west-2:123456789111:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resourceShareInvitation": {
            "resourceShareInvitationArn": "arn:aws:ram:us-west-2:123456789111:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceShareName": "MyLicenseShare",
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789111:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "senderAccountId": "123456789111",
            "receiverAccountId": "123456789222",
            "invitationTimestamp": "2021-09-22T15:07:35.620000-07:00",
            "status": "ACCEPTED"
        }
    }

For more information, see `Accepting and rejecting resource share invitations <https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-invitations.html>`__ in the *AWS RAM User Guide*.
