**To accept a resource share invitation**

The following ``reject-resource-share-invitation`` example rejects the specified resource share invitation. ::

    aws ram reject-resource-share-invitation \
        --resource-share-invitation-arn arn:aws:ram:us-west-2:123456789012:resource-share-invitation/arn:aws:ram:us-east-1:210774411744:resource-share-invitation/32b639f0-14b8-7e8f-55ea-e6117EXAMPLE

Output::

    {
        "resourceShareInvitations": [
            {
                "resourceShareInvitationArn": "arn:aws:ram:us-west2-1:21077EXAMPLE:resource-share-invitation/32b639f0-14b8-7e8f-55ea-e6117EXAMPLE",
                "resourceShareName": "project-resource-share",
                "resourceShareArn": "arn:aws:ram:us-west-2:21077EXAMPLE:resource-share/fcb639f0-1449-4744-35bc-a983fc0d4ce1",
                "senderAccountId": "21077EXAMPLE",
                "receiverAccountId": "123456789012",
                "invitationTimestamp": 1565319592.463,
                "status": "ACCEPTED"
            }
        ]
    }

