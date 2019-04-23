**To send a signal to an Automation execution**

This example sends the Approve signal to an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "Approve"

**To send an approve signal with a comment to an Automation execution**

This example sends the Approve signal with a comment to an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "Approve" --payload "Comment=Approved"

**To start an Automation step**

This example starts the specified step in an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "StartStep" --payload "StepName=stopInstances"

**To resume an Automation step**

This example resumes the specified step in an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "Resume" --payload "StepName=stopInstances"
  
**To stop an Automation step**

This example stops the specified step that is currently in progress within an Automation execution. There is no output if the command succeeds.

Command::

  aws ssm send-automation-signal --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --signal-type "StopStep" --payload "StepExecutionId=35de5ba9-e3de-45ae-8c95-0123456789ab"
  
