**To delete an attachment**

The following ``delete-attachment`` example deletes a Connect attachment. ::

    aws networkmanager delete-attachment \
        --attachment-id attachment-01feddaeae26ab68c

Output::

    {
        "Attachment": {
            "CoreNetworkId": "core-network-0f4b0a9d5ee7761d1",
            "AttachmentId": "attachment-01feddaeae26ab68c",
            "OwnerAccountId": "123456789012",
            "AttachmentType": "CONNECT",
            "State": "DELETING",
            "EdgeLocation": "us-west-2",
            "ResourceArn": "arn:aws:networkmanager::123456789012:attachment/attachment-02c3964448fedf5aa",
            "CreatedAt": "2022-03-15T19:18:41+00:00",
            "UpdatedAt": "2022-03-15T19:28:59+00:00"
        }
    }

For more information, see `Delete an AWS Cloud WAN core network attachment <https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-attachments-deleting.html>`__ in the *Cloud WAN User Guide*.