**To list the invocations of a specific command**

This example lists all the invocations of a command.

Command::

  aws ssm list-command-invocations --command-id "ef7fdfd8-9b57-4151-a15c-db9a12345678" --details

Output::

  {
	"CommandInvocations": [
        {
            "CommandId": "ef7fdfd8-9b57-4151-a15c-db9a12345678",
            "InstanceId": "i-1234567890abcdef0",
            "InstanceName": "",
            "Comment": "",
            "DocumentName": "AWS-RunPowerShellScript",
            "DocumentVersion": "1",
            "RequestedDateTime": 1550172741.988,
            "Status": "Success",
            "StatusDetails": "Success",
            "StandardOutputUrl": "",
            "StandardErrorUrl": "",
            "CommandPlugins": [
                {
                    "Name": "aws:runPowerShellScript",
                    "Status": "Success",
                    "StatusDetails": "Success",
                    "ResponseCode": 0,
                    "ResponseStartDateTime": 1550172742.696,
                    "ResponseFinishDateTime": 1550172743.245,
                    "Output": "HelloWorld\r\n",
                    "StandardOutputUrl": "",
                    "StandardErrorUrl": "",
                    "OutputS3Region": "us-east-1",
                    "OutputS3BucketName": "",
                    "OutputS3KeyPrefix": ""
                }
            ],
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
            "CommandId": "ef7fdfd8-9b57-4151-a15c-db9a12345678",
            "InstanceId": "i-12345abcdef678901",
            "InstanceName": "",
            "Comment": "",
            "DocumentName": "AWS-RunPowerShellScript",
            "DocumentVersion": "1",
            "RequestedDateTime": 1550172741.906,
            "Status": "Success",
            "StatusDetails": "Success",
            "StandardOutputUrl": "",
            "StandardErrorUrl": "",
            "CommandPlugins": [
                {
                    "Name": "aws:runPowerShellScript",
                    "Status": "Success",
                    "StatusDetails": "Success",
                    "ResponseCode": 0,
                    "ResponseStartDateTime": 1550172742.291,
                    "ResponseFinishDateTime": 1550172742.694,
                    "Output": "HelloWorld\r\n",
                    "StandardOutputUrl": "",
                    "StandardErrorUrl": "",
                    "OutputS3Region": "us-east-1",
                    "OutputS3BucketName": "",
                    "OutputS3KeyPrefix": ""
                }
            ],
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
