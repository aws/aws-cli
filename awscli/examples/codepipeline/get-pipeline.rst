**To view the structure of a pipeline**

The following ``get-pipeline`` example returns the structure of a pipeline named MyFirstPipeline. ::

    aws codepipeline get-pipeline \
        --name MyFirstPipeline


Output::

    {
        "pipeline": {
            "roleArn": "arn:aws:iam::123456789012:role/AWS-CodePipeline-Service",
            "stages": [
                {
                    "name": "Source",
                    "actions": [
                        {
                            "inputArtifacts": [],
                            "name": "Source",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "version": "1",
                                "provider": "S3"
                            },
                            "outputArtifacts": [
                                {
                                    "name": "MyApp"
                                }
                            ],
                            "configuration": {
                                "S3Bucket": "awscodepipeline-demo-bucket",
                                "S3ObjectKey": "aws-codepipeline-s3-aws-codedeploy_linux.zip"
                            },
                            "runOrder": 1
                        }
                    ]
                },
                {
                    "name": "Beta",
                    "actions": [
                        {
                            "inputArtifacts": [
                                {
                                    "name": "MyApp"
                                }
                            ],
                            "name": "CodePipelineDemoFleet",
                            "actionTypeId": {
                                "category": "Deploy",
                                "owner": "AWS",
                                "version": "1",
                                "provider": "CodeDeploy"
                            },
                            "outputArtifacts": [],
                            "configuration": {
                                "ApplicationName": "CodePipelineDemoApplication",
                                "DeploymentGroupName": "CodePipelineDemoFleet"
                            },
                            "runOrder": 1
                        }
                    ]
                }
            ],
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-11EXAMPLE11"
            },
            "name": "MyFirstPipeline",
            "version": 1
        }
    }

For more information, see `View pipeline details and history (CLI) <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-view-cli.html>`__ in the *AWS CodePipeline User Guide*.
