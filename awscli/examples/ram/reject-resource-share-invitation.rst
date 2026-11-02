**To reject a resource share invitation**

The following ``reject-resource-share-invitation`` example rejects the specified resource share invitation. ::

    aws ram reject-resource-share-invitation \
        --resource-share-invitation-arn arn:aws:ram:us-west-2:123456789111:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "resourceShareInvitation": {
            "resourceShareInvitationArn": "arn:aws:ram:us-west-2:123456789111:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceShareName": "project-resource-share",
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789111:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "senderAccountId": "123456789111",
            "receiverAccountId": "123456789222",
            "invitationTimestamp": 1565319592.463,
            "status": "REJECTED"
        }
    }

For more information, see `Accepting and rejecting resource share invitations <https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-invitations.html>`__ in the *AWS RAM User Guide*.
