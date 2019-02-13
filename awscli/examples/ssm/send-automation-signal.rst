**To send a signal to an Automation execution**

This example sends the Approve signal to an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "Approve"

**To send a signal with a comment to an Automation execution**

This example sends the Approve signal with a comment to an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "Approve" --payload "Comment=Approved"