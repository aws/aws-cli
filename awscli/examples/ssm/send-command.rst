**To execute a command on one or more remote instances**

This example runs an echo command on a target instance.

Command::

  aws ssm send-command --document-name "AWS-RunPowerShellScript" --parameters commands=["echo helloWorld"] --targets "Key=instanceids,Values=i-0cb2b964d3e14fd9f"
  
Output::

  {
    "Command": {
        "Comment": "",
        "Status": "Pending",
        "MaxErrors": "0",
        "Parameters": {
            "commands": [
                "echo helloWorld"
            ]
        },
        "ExpiresAfter": 1487888845.833,
        "ServiceRole": "",
        "DocumentName": "AWS-RunPowerShellScript",
        "TargetCount": 0,
        "OutputS3BucketName": "",
        "NotificationConfig": {
            "NotificationArn": "",
            "NotificationEvents": [],
            "NotificationType": ""
        },
        "CompletedCount": 0,
        "Targets": [
            {
                "Values": [
                    "i-0cb2b964d3e14fd9f"
                ],
                "Key": "instanceids"
            }
        ],
        "StatusDetails": "Pending",
        "ErrorCount": 0,
        "OutputS3KeyPrefix": "",
        "RequestedDateTime": 1487885245.833,
        "CommandId": "0d4fc863-2154-4e46-990e-d6a952469e91",
        "InstanceIds": [],
        "MaxConcurrency": "50"
    }
  }

**To get IP information about an instance**

This example gets the IP information about an instance.

Command::

  aws ssm send-command --instance-ids "i-0cb2b964d3e14fd9f" --document-name "AWS-RunShellScript" --comment "IP config" --parameters "commands=ifconfig" --output text

**To target multiple instances with different tags**

This example targets two different tag keys and values.

Command::

  aws ssm send-command --document-name "AWS-RunPowerShellScript" --parameters commands=["echo helloWorld"] --targets Key=tag:Env,Values=Dev Key=tag:Role,Values=WebServers

**To target multiple instances with the same tag key**

This example targets the same tag key with different values.

Command::

  aws ssm send-command --document-name "AWS-RunPowerShellScript" --parameters commands=["echo helloWorld"] --targets Key=tag:Env,Values=Dev,Test
