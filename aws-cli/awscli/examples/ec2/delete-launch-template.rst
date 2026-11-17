**To delete a launch template**

The following ``delete-launch-template`` example deletes the specified launch template. ::

    aws ec2 delete-launch-template \
        --launch-template-id lt-0abcd29075EXAMPLE

Output::

    {
        "LaunchTemplate": {
            "LatestVersionNumber": 2,
            "LaunchTemplateId": "lt-0abcd29075EXAMPLE",
            "LaunchTemplateName": "TestTemplate",
            "DefaultVersionNumber": 2,
            "CreatedBy": "arn:aws:iam::123456789012:root",
            "CreateTime": "2017-11-23T16:46:25.000Z"
        }
    }

For more information, see `Delete a launch template or a launch template version <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/delete-launch-template.html>`__ in the *Amazon EC2 User Guide*.
