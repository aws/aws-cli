**To list your resource share invitations**

The following ``get-resource-share-invitations`` example lists your current resource share invitations. ::

    aws ram get-resource-share-invitations

Output::

    {
        "resourceShareInvitations": [
            {
                "resourceShareInvitationArn": "arn:aws:ram:us-west2-1:123456789111:resource-share-invitation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceShareName": "project-resource-share",
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789111:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "senderAccountId": "123456789111",
                "receiverAccountId": "123456789222",
                "invitationTimestamp": 1565312166.258,
                "status": "PENDING"
            }
        ]
    }

For more information, see `Accepting and rejecting resource share invitations <https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-invitations.html>`__ in the *AWS RAM User Guide*.
