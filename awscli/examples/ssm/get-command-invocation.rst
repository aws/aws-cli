**To display the details of a command invocation**

This example lists all the invocations of a command on an instance.

Command::

  aws ssm get-command-invocation --command-id "bca3371c-3fdf-43f1-9323-7a7780b1b4db" --instance-id "i-0000293ffd8c57862"

Output::

  {
    "Comment": "Apply association with id at creation time: a052fd99-0852-4df2-ad69-0299f2c82047",
    "Status": "SUCCESS",
    "ExecutionEndDateTime": "",
    "StandardErrorContent": "",
    "InstanceId": "i-0000293ffd8c57862",
    "StandardErrorUrl": "",
    "DocumentName": "AWS-RefreshAssociation",
    "StandardOutputContent": "",
    "PluginName": "",
    "ResponseCode": -1,
    "CommandId": "bca3371c-3fdf-43f1-9323-7a7780b1b4db",
    "StandardOutputUrl": ""
  }
