**To change the default launch template version**

The following ``modify-launch-template`` example specifies version 2 of the specified launch template as the default version. ::

    aws ec2 modify-launch-template \
        --launch-template-id lt-0abcd2907511931ef \
        --default-version 2

Output::

    {
        "LaunchTemplate": {
            "LatestVersionNumber": 2,
            "LaunchTemplateId": "lt-0abcd2907511931ef",
            "LaunchTemplateName": "WebServers",
            "DefaultVersionNumber": 2,
            "CreatedBy": "arn:aws:iam::123456789012:root",
            "CreateTime": "2017-12-01T13:35:46.000Z"
        }
    }

For more information, see `Modify a launch template (manage launch template versions) <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-launch-template-versions.html>`__ in the *Amazon EC2 User Guide*.
