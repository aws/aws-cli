**To describe flow logs**

This example describes all of your flow logs.

Command::

  aws ec2 describe-flow-logs

Output::

  {
    "FlowLogs": [
      {
        "ResourceId": "eni-11aa22bb", 
        "CreationTime": "2015-06-12T14:41:15Z", 
        "LogGroupName": "MyFlowLogs", 
        "TrafficType": "ALL", 
        "FlowLogStatus": "ACTIVE", 
        "FlowLogId": "fl-1a2b3c4d", 
        "DeliverLogsPermissionArn": "arn:aws:iam::123456789101:role/flow-logs-role"
      }
    ]
  }
  
This example uses a filter to describe only flow logs that are in the log group ``MyFlowLogs`` in Amazon CloudWatch Logs.
 
Command::
 
  aws ec2 describe-flow-logs --filter "Name=log-group-name,Values=MyFlowLogs"