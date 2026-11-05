**To describe launch template versions**

The following ``describe-launch-template-versions`` example describes the versions of the specified launch template. ::

    aws ec2 describe-launch-template-versions \
        --launch-template-id lt-068f72b72934aff71

Output::

    {
        "LaunchTemplateVersions": [
            {
                "LaunchTemplateId": "lt-068f72b72934aff71",
                "LaunchTemplateName": "Webservers",
                "VersionNumber": 3,
                "CreatedBy": "arn:aws:iam::123456789012:root",
                "LaunchTemplateData": {
                    "KeyName": "kp-us-east",
                    "ImageId": "ami-6057e21a",
                    "InstanceType": "t2.small",
                    "NetworkInterfaces": [
                        {
                            "SubnetId": "subnet-7b16de0c",
                            "DeviceIndex": 0,
                            "Groups": [
                                "sg-7c227019"
                            ]
                        }
                    ]
                },
                "DefaultVersion": false,
                "CreateTime": "2017-11-20T13:19:54.000Z"
            },
            {
                "LaunchTemplateId": "lt-068f72b72934aff71",
                "LaunchTemplateName": "Webservers",
                "VersionNumber": 2,
                "CreatedBy": "arn:aws:iam::123456789012:root",
                "LaunchTemplateData": {
                    "KeyName": "kp-us-east",
                    "ImageId": "ami-6057e21a",
                    "InstanceType": "t2.medium",
                    "NetworkInterfaces": [
                        {
                            "SubnetId": "subnet-1a2b3c4d",
                            "DeviceIndex": 0,
                            "Groups": [
                                "sg-7c227019"
                            ]
                        }
                    ]
                },
                "DefaultVersion": false,
                "CreateTime": "2017-11-20T13:12:32.000Z"
            },
            {
                "LaunchTemplateId": "lt-068f72b72934aff71",
                "LaunchTemplateName": "Webservers",
                "VersionNumber": 1,
                "CreatedBy": "arn:aws:iam::123456789012:root",
                "LaunchTemplateData": {
                    "UserData": "",
                    "KeyName": "kp-us-east",
                    "ImageId": "ami-aabbcc11",
                    "InstanceType": "t2.medium",
                    "NetworkInterfaces": [
                        {
                            "SubnetId": "subnet-7b16de0c",
                            "DeviceIndex": 0,
                            "DeleteOnTermination": false,
                            "Groups": [
                                "sg-7c227019"
                            ],
                            "AssociatePublicIpAddress": true
                        }
                    ]
                },
                "DefaultVersion": true,
                "CreateTime": "2017-11-20T12:52:33.000Z"
            }
        ]
    }

For more information, see `Modify a launch template (manage launch template versions) <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-launch-template-versions.html>`__ in the *Amazon EC2 User Guide*.
