**To list your resource share invitations**

The following ``get-resource-share-invitations`` example lists your resource share invitations. ::

    aws ram get-resource-share-invitations

Output::

    {
        "resourceShareInvitations": [
            {
                "resourceShareInvitationArn": "arn:aws:ram:us-west2-1:21077EXAMPLE:resource-share-invitation/32b639f0-14b8-7e8f-55ea-e6117EXAMPLE",
                "resourceShareName": "project-resource-share",
                "resourceShareArn": "arn:aws:ram:us-west-2:21077EXAMPLE:resource-share/fcb639f0-1449-4744-35bc-a983fc0d4ce1",
                "senderAccountId": "21077EXAMPLE",
                "receiverAccountId": "123456789012",
                "invitationTimestamp": 1565312166.258,
                "status": "PENDING"
            }
        ]
    }
