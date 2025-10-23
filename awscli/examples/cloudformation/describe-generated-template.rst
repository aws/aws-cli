**To describe a generated template**

The following ``describe-generated-template`` example describes the specified template. ::

    aws cloudformation describe-generated-template \
        --generated-template-name MyTemplate

Output::

    {
        "GeneratedTemplateId": "arn:aws:cloudformation:us-east-1:123456789012:generatedTemplate/7d881acf-f307-4ded-910e-f8fb49b96894",
        "GeneratedTemplateName": "MyTemplate",
        "Resources": [
            {
                "ResourceType": "AWS::EC2::SecurityGroup",
                "LogicalResourceId": "EC2SecurityGroup",
                "ResourceIdentifier": {
                    "Id": "sg-1234567890abcdef0"
                },
                "ResourceStatus": "COMPLETE",
                "ResourceStatusReason": "Resource Template complete",
                "Warnings": []
            },
            {
                "ResourceType": "AWS::EC2::Instance",
                "LogicalResourceId": "EC2Instance",
                "ResourceIdentifier": {
                    "InstanceId": "i-1234567890abcdef0"
                },
                "ResourceStatus": "COMPLETE",
                "ResourceStatusReason": "Resource Template complete",
                "Warnings": []
            },
            {
                "ResourceType": "AWS::EC2::KeyPair",
                "LogicalResourceId": "EC2KeyPairSshkeypair",
                "ResourceIdentifier": {
                    "KeyName": "sshkeypair"
                },
                "ResourceStatus": "COMPLETE",
                "ResourceStatusReason": "Resource Template complete",
                "Warnings": []
            }
        ],
        "Status": "COMPLETE",
        "StatusReason": "All resources complete",
        "CreationTime": "2025-09-23T19:38:06.435000+00:00",
        "LastUpdatedTime": "2025-09-23T19:38:10.798000+00:00",
        "Progress": {
            "ResourcesSucceeded": 3,
            "ResourcesFailed": 0,
            "ResourcesProcessing": 0,
            "ResourcesPending": 0
        },
        "TemplateConfiguration": {
            "DeletionPolicy": "RETAIN",
            "UpdateReplacePolicy": "RETAIN"
        },
        "TotalWarnings": 0
    }

For more information, see `Generating templates from existing resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/generate-IaC.html>`__ in the *AWS CloudFormation User Guide*.
