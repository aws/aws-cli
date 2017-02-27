**To update the role of a managed instance**

This example updates the role of instance ``mi-08ab247cdf1046573`` with ``AutomationRole``. There is no output if the command succeeds.

Command::

  aws ssm update-managed-instance-role --instance-id "mi-08ab247cdf1046573" --iam-role "AutomationRole"
