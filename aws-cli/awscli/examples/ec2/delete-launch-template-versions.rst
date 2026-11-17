**To delete a launch template version**

The following ``delete-launch-template-versions`` example deletes the specified launch template version. ::

    aws ec2 delete-launch-template-versions \
        --launch-template-id lt-0abcd1234567890ab \
        --versions 1

Output::

    {
        "UnsuccessfullyDeletedLaunchTemplateVersions": [],
        "SuccessfullyDeletedLaunchTemplateVersions": [
            {
                "LaunchTemplateName": "TestVersion",
                "VersionNumber": 1,
                "LaunchTemplateId": "lt-0abcd1234567890ab"
            }
        ]
    }

For more information, see `Delete a launch template or a launch template version <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/delete-launch-template.html>`__ in the *Amazon EC2 User Guide*.
