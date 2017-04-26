**To add tags to a resource**

This example updates a maintenance window with new tags. There is no output if the command succeeds.

Command::

   aws ssm add-tags-to-resource --resource-type "MaintenanceWindow" --resource-id "mw-03eb9db42890fb82d" --tags "Key=Stack,Value=Production"
