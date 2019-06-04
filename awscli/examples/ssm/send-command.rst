**Example 1: To run a command on one or more remote instances**

The following ``send-command`` example runs an ``echo`` command on a target instance. ::

    aws ssm send-command \
        --document-name "AWS-RunShellScript" \
        --parameters commands=["echo HelloWorld"] \
        --targets "Key=instanceids,Values=i-1234567890abcdef0" \
        --comment "echo HelloWorld"
  
Output::

    {
        "Command": {
            "CommandId": "92853adf-ba41-4cd6-9a88-142d119c083d",
            "DocumentName": "AWS-RunShellScript",
            "DocumentVersion": "",
            "Comment": "echo HelloWorld",
            "ExpiresAfter": 1550181014.717,
            "Parameters": {
                "commands": [
                    "echo HelloWorld"
                ]
            },
            "InstanceIds": [
                "i-0f00f008a2dcbefe2"
            ],
            "Targets": [],
            "RequestedDateTime": 1550173814.717,
            "Status": "Pending",
            "StatusDetails": "Pending",
            "OutputS3BucketName": "",
            "OutputS3KeyPrefix": "",
            "MaxConcurrency": "50",
            "MaxErrors": "0",
            "TargetCount": 1,
            "CompletedCount": 0,
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
    }

**Example 2: To get IP information about an instance**

The following ``send-command`` example retrieves the IP information about an instance. ::

    aws ssm send-command \
        --instance-ids "i-1234567890abcdef0" \
        --document-name "AWS-RunShellScript" \
        --comment "IP config" \
        --parameters "commands=ifconfig"

**Example 3: To runs a command on instances with specific tags**

The following ``send-command`` example runs a command on instances that have the tag key "ENV" and the value "Dev". ::

    aws ssm send-command \
        --targets "Key=tag:ENV,Values=Dev" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=ifconfig"

**Example 4: To runs a command that sends SNS Notifications**

The following ``send-command`` example runs a command that sends SNS notifications for all notification events and the Command notification type. ::

    aws ssm send-command \
        --instance-ids "i-1234567890abcdef0" \
        --document-name "AWS-RunShellScript" \
        --comment "IP config" \
        --parameters "commands=ifconfig" \
        --service-role-arn "arn:aws:iam::123456789012:role/SNS_Role" \
        --notification-config "NotificationArn=arn:aws:sns:us-east-1:123456789012:SNSTopicName,NotificationEvents=All,NotificationType=Command"

**Example 5: To run a command that outputs to S3 and CloudWatch**

The following ``send-command`` example runs a command that outputs command details to an S3 bucket and to a CloudWatch Logs Group. ::

    aws ssm send-command \
        --instance-ids "i-1234567890abcdef0" \
        --document-name "AWS-RunShellScript" \
        --comment "IP config" \
        --parameters "commands=ifconfig" \
        --output-s3-bucket-name "s3-bucket-name" \
        --output-s3-key-prefix "runcommand" \
        --cloud-watch-output-config "CloudWatchOutputEnabled=true,CloudWatchLogGroupName=CWLGroupName"

**Example 6: To run commands on multiple instances with different tags**

The follwoing ``send-command`` example runs a command on instances with two different tag keys and values. ::

    aws ssm send-command \
        --document-name "AWS-RunPowerShellScript" \
        --parameters commands=["echo helloWorld"] \
        --targets Key=tag:Env,Values=Dev Key=tag:Role,Values=WebServers

**Example 7: To target multiple instances with the same tag key**

The following ``send-command`` example runs a command on instances that have the same tag key but with different values. ::

    aws ssm send-command \
        --document-name "AWS-RunPowerShellScript" \
        --parameters commands=["echo helloWorld"] \
        --targets Key=tag:Env,Values=Dev,Test
