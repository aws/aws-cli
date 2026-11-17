**To create a launch template version**

The following ``create-launch-template-version`` example creates a new launch template version based on version 1 of the launch template and specifies a different AMI ID. ::

    aws ec2 create-launch-template-version \
        --launch-template-id lt-0abcd1234567890ab \
        --version-description WebVersion2 \
        --source-version 1 \
        --launch-template-data '{"ImageId":"ami-c998b6b2"}'

Output::

    {
        "LaunchTemplateVersion": {
            "VersionDescription": "WebVersion2",
            "LaunchTemplateId": "lt-0abcd1234567890ab",
            "LaunchTemplateName": "WebServers",
            "VersionNumber": 2,
            "CreatedBy": "arn:aws:iam::123456789012:root",
            "LaunchTemplateData": {
                "ImageId": "ami-c998b6b2",
                "InstanceType": "t2.micro",
                "NetworkInterfaces": [
                    {
                        "Ipv6Addresses": [
                            {
                                "Ipv6Address": "2001:db8:1234:1a00::123"
                            }
                        ],
                        "DeviceIndex": 0,
                        "SubnetId": "subnet-7b16de0c",
                        "AssociatePublicIpAddress": true
                    }
                ]
            },
            "DefaultVersion": false,
            "CreateTime": "2017-12-01T13:35:46.000Z"
        }
    }

For more information, see `Modify a launch template (manage launch template versions) <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-launch-template-versions.html>`__ in the *Amazon EC2 User Guide*.
