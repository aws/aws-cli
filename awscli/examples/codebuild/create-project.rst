**Creates an AWS CodeBuild build project **

The following ``create-project`` example creates a CodeBuild build project. ::

    aws codebuild create-project --cli-input-json file://create-project.json

Where the file "create-project.json" is::

    {
        "name": "codebuild-demo-project",
        "source": {
            "type": "S3",
            "location": "codebuild-region-ID-account-ID-input-bucket/MessageUtil.zip"
        },
        "artifacts": {
            "type": "S3",
            "location": "codebuild-region-ID-account-ID-output-bucket"
        },
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:1.0",
            "computeType": "BUILD_GENERAL1_SMALL"
        },
        "serviceRole": "serviceIAMRole"
    }

Output::

    {
        "project": {
            "name": "codebuild-demo-project",
            "serviceRole": "serviceIAMRole",
            "tags": [],
            "artifacts": {
                "packaging": "NONE",
                "type": "S3",
                "location": "codebuild-region-ID-account-ID-output-bucket",
                "name": "message-util.zip"
            },
            "lastModified": 1472661575.244,
            "timeoutInMinutes": 60,
            "created": 1472661575.244,
            "environment": {
                "computeType": "BUILD_GENERAL1_SMALL",
                "image": "aws/codebuild/standard:1.0",
                "type": "LINUX_CONTAINER",
                "environmentVariables": []
            },
            "source": {
                "type": "S3",
                "location": "codebuild-region-ID-account-ID-input-bucket/MessageUtil.zip"
            },
            "encryptionKey": "arn:aws:kms:region-ID:account-ID:alias/aws/s3",
            "arn": "arn:aws:codebuild:region-ID:account-ID:project/codebuild-demo-project"
        }
    }

For more information, see `Create a Build Project (AWS CLI)`_ in the *AWS CodeBuild User Guide*

.. _`Create a Build Project (AWS CLI)`: https://docs.aws.amazon.com/codebuild/latest/userguide/create-project.html#create-project-cli
