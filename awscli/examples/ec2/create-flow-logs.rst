**To create a flow log**

This example creates a flow log that captures all rejected traffic for network interface ``eni-aa22bb33``. The flow logs are delivered to a log group in CloudWatch Logs called ``my-flow-logs`` in account 123456789101, using the IAM role ``publishFlowLogs``.

Command::

  aws ec2 create-flow-logs --resource-type NetworkInterface --resource-ids eni-aa22bb33 --traffic-type REJECT --log-group-name my-flow-logs --deliver-logs-permission-arn arn:aws:iam::123456789101:role/publishFlowLogs

Output::

  {
    "Unsuccessful": [], 
    "FlowLogIds": [
      "fl-1a2b3c4d"
    ], 
    "ClientToken": "lO+mDZGO+HCFEXAMPLEfWNO00bInKkBcLfrC"
  }