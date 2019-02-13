**To stop the execution of an Automation document**

This example stops an automation execution. There is no output if the command succeeds.

Command::

  aws ssm stop-automation-execution --automation-execution-id "4105a4fc-f944-11e6-9d32-0a1b2c3d495h"

**To cancel the execution of an Automation document**

This example cancels an automation execution. There is no output if the command succeeds.

Command::

  aws ssm stop-automation-execution --automation-execution-id "4105a4fc-f944-11e6-9d32-0a1b2c3d495h" --type "Cancel"
