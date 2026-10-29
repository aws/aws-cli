**Example 1: To get the status of a specific command**

The following ``list-commands`` example retrieves and displays the status of the specified command. ::

    aws ssm list-commands \
        --command-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Commands": [
            {
                "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "DocumentName": "AWS-RunShellScript",
                "DocumentVersion": "1",
                "Comment": "",
                "ExpiresAfter": "2020-02-19T12:28:02.500000-08:00",
                "Parameters": {
                    "commands": [
                        "ifconfig"
                    ]
                },
                "InstanceIds": [
                    "i-028ea792daEXAMPLE"
                ],
                "Targets": [],
                "RequestedDateTime": "2020-02-19T11:18:02.500000-08:00",
                "Status": "Success",
                "StatusDetails": "Success",
                "OutputS3BucketName": "",
                "OutputS3KeyPrefix": "",
                "MaxConcurrency": "50",
                "MaxErrors": "0",
                "TargetCount": 1,
                "CompletedCount": 1,
                "ErrorCount": 0,
                "DeliveryTimedOutCount": 0,
                "ServiceRole": "",
                "NotificationConfig": {
                    "NotificationArn": "",
                    "NotificationEvents": [],
                    "NotificationType": ""
                },
                "CloudWatchOutputConfig": {
                    "CloudWatchLogGroupName": "",
                    "CloudWatchOutputEnabled": false
                },
                "TimeoutSeconds": 3600
            }
        ]
    }

**Example 2: To get the status of commands requested after a specific date**

The following ``list-commands`` example retrieves the details of commands requested after the specified date. ::

    aws ssm list-commands \
        --filter "key=InvokedAfter,value=2020-02-01T00:00:00Z"

Output::

    {
        "Commands": [
            {
                "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "DocumentName": "AWS-UpdateSSMAgent",
                "DocumentVersion": "",
                "Comment": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "ExpiresAfter": "2020-02-19T11:28:02.500000-08:00",
                "Parameters": {},
                "InstanceIds": [
                    "i-028ea792daEXAMPLE",
                    "i-02feef8c46EXAMPLE",
                    "i-038613f3f0EXAMPLE",
                    "i-03a530a2d4EXAMPLE",
                    "i-083b678d37EXAMPLE",
                    "i-0dee81debaEXAMPLE"
                ],
                "Targets": [],
                "RequestedDateTime": "2020-02-19T10:18:02.500000-08:00",
                "Status": "Success",
                "StatusDetails": "Success",
                "OutputS3BucketName": "",
                "OutputS3KeyPrefix": "",
                "MaxConcurrency": "50",
                "MaxErrors": "100%",
                "TargetCount": 6,
                "CompletedCount": 6,
                "ErrorCount": 0,
                "DeliveryTimedOutCount": 0,
                "ServiceRole": "",
                "NotificationConfig": {
                    "NotificationArn": "",
                    "NotificationEvents": [],
                    "NotificationType": ""
                },
                "CloudWatchOutputConfig": {
                    "CloudWatchLogGroupName": "",
                    "CloudWatchOutputEnabled": false
                }
            }
        ]
    }

**Example 3: To list all commands requested in an AWS account**

The following ``list-commands`` example lists all commands requested by users in the current AWS account and Region. ::

    aws ssm list-commands

Output::

    {
        "Commands": [
            {
                "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "DocumentName": "AWS-UpdateSSMAgent",
                "DocumentVersion": "",
                "Comment": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "ExpiresAfter": "2020-02-19T11:28:02.500000-08:00",
                "Parameters": {},
                "InstanceIds": [
                    "i-028ea792daEXAMPLE",
                    "i-02feef8c46EXAMPLE",
                    "i-038613f3f0EXAMPLE",
                    "i-03a530a2d4EXAMPLE",
                    "i-083b678d37EXAMPLE",
                    "i-0dee81debaEXAMPLE"
                ],
                "Targets": [],
                "RequestedDateTime": "2020-02-19T10:18:02.500000-08:00",
                "Status": "Success",
                "StatusDetails": "Success",
                "OutputS3BucketName": "",
                "OutputS3KeyPrefix": "",
                "MaxConcurrency": "50",
                "MaxErrors": "100%",
                "TargetCount": 6,
                "CompletedCount": 6,
                "ErrorCount": 0,
                "DeliveryTimedOutCount": 0,
                "ServiceRole": "",
                "NotificationConfig": {
                    "NotificationArn": "",
                    "NotificationEvents": [],
                    "NotificationType": ""
                },
                "CloudWatchOutputConfig": {
                    "CloudWatchLogGroupName": "",
                    "CloudWatchOutputEnabled": false
                }
            },
            {
                "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "DocumentName": "AWS-FindWindowsUpdates",
                "DocumentVersion": "1",
                "Comment": "",
                "ExpiresAfter": "2020-01-24T12:37:31.874000-08:00",
                "Parameters": {
                    "KbArticleIds": [
                        ""
                    ],
                    "UpdateLevel": [
                        "All"
                    ]
                },
                "InstanceIds": [],
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-00ec29b21eEXAMPLE",
                            "i-09911ddd90EXAMPLE"
                        ]
                    }
                ],
                "RequestedDateTime": "2020-01-24T11:27:31.874000-08:00",
                "Status": "Success",
                "StatusDetails": "Success",
                "OutputS3BucketName": "my-us-east-2-bucket",
                "OutputS3KeyPrefix": "my-rc-output",
                "MaxConcurrency": "50",
                "MaxErrors": "0",
                "TargetCount": 2,
                "CompletedCount": 2,
                "ErrorCount": 0,
                "DeliveryTimedOutCount": 0,
                "ServiceRole": "arn:aws:iam::123456789012:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "NotificationConfig": {
                    "NotificationArn": "arn:aws:sns:us-west-2:123456789012:my-us-east-2-notification-arn",
                    "NotificationEvents": [
                        "All"
                    ],
                    "NotificationType": "Invocation"
                },
                "CloudWatchOutputConfig": {
                    "CloudWatchLogGroupName": "",
                    "CloudWatchOutputEnabled": false
                }
            },
            {
                "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
                "DocumentName": "AWS-RunPatchBaseline",
                "DocumentVersion": "1",
                "Comment": "",
                "ExpiresAfter": "2020-01-24T12:21:04.350000-08:00",
                "Parameters": {
                    "InstallOverrideList": [
                        ""
                    ],
                    "Operation": [
                        "Install"
                    ],
                    "RebootOption": [
                        "RebootIfNeeded"
                    ],
                    "SnapshotId": [
                        ""
                    ]
                },
                "InstanceIds": [],
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-00ec29b21eEXAMPLE",
                            "i-09911ddd90EXAMPLE"
                        ]
                    }
                ],
                "RequestedDateTime": "2020-01-24T11:11:04.350000-08:00",
                "Status": "Success",
                "StatusDetails": "Success",
                "OutputS3BucketName": "my-us-east-2-bucket",
                "OutputS3KeyPrefix": "my-rc-output",
                "MaxConcurrency": "50",
                "MaxErrors": "0",
                "TargetCount": 2,
                "CompletedCount": 2,
                "ErrorCount": 0,
                "DeliveryTimedOutCount": 0,
                "ServiceRole": "arn:aws:iam::123456789012:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "NotificationConfig": {
                    "NotificationArn": "arn:aws:sns:us-west-2:123456789012:my-us-east-2-notification-arn",
                    "NotificationEvents": [
                        "All"
                    ],
                    "NotificationType": "Invocation"
                },
                "CloudWatchOutputConfig": {
                    "CloudWatchLogGroupName": "",
                    "CloudWatchOutputEnabled": false
                }
            }
        ]
    }

For more information, see `Running Commands Using Systems Manager Run Command <https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html>`__ in the *AWS Systems Manager User Guide*.
