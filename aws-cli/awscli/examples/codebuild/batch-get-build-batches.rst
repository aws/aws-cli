**To view details of builds in AWS CodeBuild.**

The following ``batch-get-build-batches`` example gets information about build batches in CodeBuild with the specified IDs. ::

    aws codebuild batch-get-build-batches \
        --ids codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "buildBatches": [
            {
                "id": "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "arn": "arn:aws:codebuild:us-west-2:123456789012:build-batch/codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "startTime": "2020-11-03T21:52:20.775000+00:00",
                "endTime": "2020-11-03T21:56:59.784000+00:00",
                "currentPhase": "SUCCEEDED",
                "buildBatchStatus": "SUCCEEDED",
                "resolvedSourceVersion": "0a6546f68309560d08a310daac92314c4d378f6b",
                "projectName": "codebuild-demo-project",
                "phases": [
                    {
                        "phaseType": "SUBMITTED",
                        "phaseStatus": "SUCCEEDED",
                        "startTime": "2020-11-03T21:52:20.775000+00:00",
                        "endTime": "2020-11-03T21:52:20.976000+00:00",
                        "durationInSeconds": 0
                    },
                    {
                        "phaseType": "DOWNLOAD_BATCHSPEC",
                        "phaseStatus": "SUCCEEDED",
                        "startTime": "2020-11-03T21:52:20.976000+00:00",
                        "endTime": "2020-11-03T21:52:57.401000+00:00",
                        "durationInSeconds": 36
                    },
                    {
                        "phaseType": "IN_PROGRESS",
                        "phaseStatus": "SUCCEEDED",
                        "startTime": "2020-11-03T21:52:57.401000+00:00",
                        "endTime": "2020-11-03T21:56:59.751000+00:00",
                        "durationInSeconds": 242
                    },
                    {
                        "phaseType": "COMBINE_ARTIFACTS",
                        "phaseStatus": "SUCCEEDED",
                        "startTime": "2020-11-03T21:56:59.751000+00:00",
                        "endTime": "2020-11-03T21:56:59.784000+00:00",
                        "durationInSeconds": 0
                    },
                    {
                        "phaseType": "SUCCEEDED",
                        "startTime": "2020-11-03T21:56:59.784000+00:00"
                    }
                ],
                "source": {
                    "type": "GITHUB",
                    "location": "https://github.com/my-repo/codebuild-demo-project.git",
                    "gitCloneDepth": 1,
                    "gitSubmodulesConfig": {
                        "fetchSubmodules": false
                    },
                    "reportBuildStatus": false,
                    "insecureSsl": false
                },
                "secondarySources": [],
                "secondarySourceVersions": [],
                "artifacts": {
                    "location": ""
                },
                "secondaryArtifacts": [],
                "cache": {
                    "type": "NO_CACHE"
                },
                "environment": {
                    "type": "LINUX_CONTAINER",
                    "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
                    "computeType": "BUILD_GENERAL1_SMALL",
                    "environmentVariables": [],
                    "privilegedMode": false,
                    "imagePullCredentialsType": "CODEBUILD"
                },
                "logConfig": {
                    "cloudWatchLogs": {
                        "status": "ENABLED"
                    },
                    "s3Logs": {
                        "status": "DISABLED",
                        "encryptionDisabled": false
                    }
                },
                "buildTimeoutInMinutes": 60,
                "queuedTimeoutInMinutes": 480,
                "complete": true,
                "initiator": "Strohm",
                "encryptionKey": "arn:aws:kms:us-west-2:123456789012:alias/aws/s3",
                "buildBatchNumber": 6,
                "buildBatchConfig": {
                    "serviceRole": "arn:aws:iam::123456789012:role/service-role/codebuild-demo-project",
                    "restrictions": {
                        "maximumBuildsAllowed": 100
                    },
                    "timeoutInMins": 480
                },
                "buildGroups": [
                    {
                        "identifier": "DOWNLOAD_SOURCE",
                        "ignoreFailure": false,
                        "currentBuildSummary": {
                            "arn": "arn:aws:codebuild:us-west-2:123456789012:build/codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                            "requestedOn": "2020-11-03T21:52:21.394000+00:00",
                            "buildStatus": "SUCCEEDED",
                            "primaryArtifact": {
                                "type": "no_artifacts",
                                "identifier": "DOWNLOAD_SOURCE"
                            },
                            "secondaryArtifacts": []
                        }
                    },
                    {
                        "identifier": "linux_small",
                        "dependsOn": [],
                        "ignoreFailure": false,
                        "currentBuildSummary": {
                            "arn": "arn:aws:codebuild:us-west-2:123456789012:build/codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                            "requestedOn": "2020-11-03T21:52:57.604000+00:00",
                            "buildStatus": "SUCCEEDED",
                            "primaryArtifact": {
                                "type": "no_artifacts",
                                "identifier": "linux_small"
                            },
                            "secondaryArtifacts": []
                        }
                    },
                    {
                        "identifier": "linux_medium",
                        "dependsOn": [
                            "linux_small"
                        ],
                        "ignoreFailure": false,
                        "currentBuildSummary": {
                            "arn": "arn:aws:codebuild:us-west-2:123456789012:build/codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                            "requestedOn": "2020-11-03T21:54:18.474000+00:00",
                            "buildStatus": "SUCCEEDED",
                            "primaryArtifact": {
                                "type": "no_artifacts",
                                "identifier": "linux_medium"
                            },
                            "secondaryArtifacts": []
                        }
                    },
                    {
                        "identifier": "linux_large",
                        "dependsOn": [
                            "linux_medium"
                        ],
                        "ignoreFailure": false,
                        "currentBuildSummary": {
                            "arn": "arn:aws:codebuild:us-west-2:123456789012:build/codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                            "requestedOn": "2020-11-03T21:55:39.203000+00:00",
                            "buildStatus": "SUCCEEDED",
                            "primaryArtifact": {
                                "type": "no_artifacts",
                                "identifier": "linux_large"
                            },
                            "secondaryArtifacts": []
                        }
                    }
                ]
            }
        ],
        "buildBatchesNotFound": []
    }

For more information, see `Run builds in batches <https://docs.aws.amazon.com/codebuild/latest/userguide/batch-build.html>`__ in the *AWS CodeBuild User Guide*.
