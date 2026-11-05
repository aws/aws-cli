**To list action executions**

The following ``list-action-executions`` example views action execution details for a pipeline, such as action execution ID, input artifacts, output artifacts, execution result, and status. ::

    aws codepipeline list-action-executions \
        --pipeline-name myPipeline

Output::

    {
        "actionExecutionDetails": [
            {
                "pipelineExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "actionExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "pipelineVersion": 12,
                "stageName": "Deploy",
                "actionName": "Deploy",
                "startTime": 1598572628.6,
                "lastUpdateTime": 1598572661.255,
                "status": "Succeeded",
                "input": {
                    "actionTypeId": {
                        "category": "Deploy",
                        "owner": "AWS",
                        "provider": "CodeDeploy",
                        "version": "1"
                    },
                    "configuration": {
                        "ApplicationName": "my-application",
                        "DeploymentGroupName": "my-deployment-group"
                    },
                    "resolvedConfiguration": {
                        "ApplicationName": "my-application",
                        "DeploymentGroupName": "my-deployment-group"
                    },
                    "region": "us-west-2",
                    "inputArtifacts": [
                        {
                            "name": "SourceArtifact",
                            "s3location": {
                                "bucket": "artifact-bucket",
                                "key": "myPipeline/SourceArti/key"
                            }
                        }
                    ],
                    "namespace": "DeployVariables"
                },
                "output": {
                    "outputArtifacts": [],
                    "executionResult": {
                        "externalExecutionId": "d-EXAMPLEE5",
                        "externalExecutionSummary": "Deployment Succeeded",
                        "externalExecutionUrl": "https://myaddress.com"
                    },
                    "outputVariables": {}
                }
            },
            {
                "pipelineExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "actionExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "pipelineVersion": 12,
                "stageName": "Source",
                "actionName": "Source",
                "startTime": 1598572624.387,
                "lastUpdateTime": 1598572628.16,
                "status": "Succeeded",
                "input": {
                    "actionTypeId": {
                        "category": "Source",
                        "owner": "AWS",
                        "provider": "CodeCommit",
                        "version": "1"
                    },
                    "configuration": {
                        "BranchName": "production",
                        "PollForSourceChanges": "false",
                        "RepositoryName": "my-repo"
                    },
                    "resolvedConfiguration": {
                        "BranchName": "production",
                        "PollForSourceChanges": "false",
                        "RepositoryName": "my-repo"
                    },
                    "region": "us-west-2",
                    "inputArtifacts": [],
                    "namespace": "SourceVariables"
                },
                "output": {
                    "outputArtifacts": [
                        {
                            "name": "SourceArtifact",
                            "s3location": {
                                "bucket": "amzn-s3-demo-bucket",
                                "key": "myPipeline/SourceArti/key"
                            }
                        }
                    ],
                    "executionResult": {
                        "externalExecutionId": "1111111ad99dcd35914c00b7fbea13995EXAMPLE",
                        "externalExecutionSummary": "Edited template.yml",
                        "externalExecutionUrl": "https://myaddress.com"
                    },
                    "outputVariables": {
                        "AuthorDate": "2020-05-08T17:45:43Z",
                        "BranchName": "production",
                        "CommitId": "1111111ad99dcd35914c00b7fbea13995EXAMPLE",
                        "CommitMessage": "Edited template.yml",
                        "CommitterDate": "2020-05-08T17:45:43Z",
                        "RepositoryName": "my-repo"
                    }
                }
            }
        ]
    }

For more information, see `View action executions (CLI) <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-view-cli.html>`__ in the *AWS CodePipeline User Guide*.