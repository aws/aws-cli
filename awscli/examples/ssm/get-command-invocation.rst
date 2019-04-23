**To display the details of a command invocation**

This example lists all the invocations of a command on an instance.

Command::

  aws ssm get-command-invocation --command-id "ef7fdfd8-9b57-4151-a15c-db9a12345678" --instance-id "i-1234567890abcdef0"

Output::

  {
    "CommandId": "ef7fdfd8-9b57-4151-a15c-db9a12345678",
    "InstanceId": "i-1234567890abcdef0",
    "Comment": "",
    "DocumentName": "AWS-RunPowerShellScript",
    "DocumentVersion": "1",
    "PluginName": "aws:runPowerShellScript",
    "ResponseCode": 0,
    "ExecutionStartDateTime": "2019-02-14T19:26:26.439Z",
    "ExecutionElapsedTime": "PT0.541S",
    "ExecutionEndDateTime": "2019-02-14T19:26:26.439Z",
    "Status": "Success",
    "StatusDetails": "Success",
    "StandardOutputContent": "HelloWorld\r\n",
    "StandardOutputUrl": "",
	"StandardErrorContent": "",
	"StandardErrorUrl": "",
	"CloudWatchOutputConfig": {
        "CloudWatchLogGroupName": "",
        "CloudWatchOutputEnabled": false
  }
