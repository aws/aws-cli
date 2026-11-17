**To create a pipeline**

The following ``create-pipeline`` example creates a pipeline in AWS CodePipeline using an already-created JSON file (here named MySecondPipeline.json) that contains the structure of the pipeline. ::

    aws codepipeline create-pipeline \
        --cli-input-json file://MySecondPipeline.json

Contents of ``MySecondPipeline.json``::

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
            "name": "MySecondPipeline",
            "version": 1
        }
    }

This command returns the structure of the pipeline.

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
            "name": "MySecondPipeline",
            "version": 1
        }
    }

For more information, see `Create a pipeline, stages, and actions <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-create.html>`__ in the *AWS CodePipeline User Guide*.
