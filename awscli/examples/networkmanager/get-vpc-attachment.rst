**To get a VPC attachment**

The following ``get-vpc-attachment`` example returns information about a VPC attachment. ::

    aws networkmanager get-vpc-attachment \
        --attachment-id  attachment-03b7ea450134787da 

Output::

    {
        "VpcAttachment": {
            "Attachment": {
                "CoreNetworkId": "core-network-0522de1b226a5d7b3",
                "AttachmentId": "attachment-03b7ea450134787da",
                "OwnerAccountId": "123456789012",
                "AttachmentType": "VPC",
                "State": "CREATING",
                "EdgeLocation": "us-west-2",
                "ResourceArn": "arn:aws:ec2:us-west-2:123456789012:vpc/vpc-a7c4bbda",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "DevVPC"
                    }
                ],
                "CreatedAt": "2022-03-11T17:48:58+00:00",
                "UpdatedAt": "2022-03-11T17:48:58+00:00"
            },
            "SubnetArns": [
                "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-202cde6c",
                "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-e5022dba",
                "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-2387ae02",
                "arn:aws:ec2:us-west-2:123456789012:subnet/subnet-cda9dffc"
            ],
            "Options": {
                "Ipv6Support": false
            }
        }
    }

For more information, see `Attachments in AWS Cloud WAN <https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-create-attachment.html>`__ in the *Cloud WAN User Guide*.