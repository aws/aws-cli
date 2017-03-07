**To list the commands requested by users of an account**

This example lists all commands requested.

Command::

  aws ssm list-commands

Output::

  {
	"Commands": [
		{
			"Comment": "IP config",
			"Status": "Success",
			"MaxErrors": "0",
			"Parameters": {
				"commands": [
					"ifconfig"
				]
			},
			"ExpiresAfter": 1487798019.876,
			"ServiceRole": "",
			"DocumentName": "AWS-RunShellScript",
			"TargetCount": 1,
			"OutputS3BucketName": "",
			"NotificationConfig": {
				"NotificationArn": "",
				"NotificationEvents": [],
				"NotificationType": ""
			},
			"CompletedCount": 1,
			"Targets": [],
			"StatusDetails": "Success",
			"ErrorCount": 0,
			"OutputS3KeyPrefix": "",
			"RequestedDateTime": 1487794419.876,
			"CommandId": "0831e1a8-a1ac-4257-a1fd-c831b48c4107",
			"InstanceIds": [
				"i-0cb2b964d3e14fd9f"
			],
			"MaxConcurrency": "50"
		},
		...
		}
	]
  }

**To get the status of a specific command**

This example gets the status of a command.

Command::

  aws ssm list-commands --command-id "0831e1a8-a1ac-4257-a1fd-c831b48c4107"
