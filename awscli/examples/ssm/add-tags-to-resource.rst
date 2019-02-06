**To add tags to an SSM Document**

This example updates an SSM document with new tags. There is no output if the command succeeds.

Command::

   aws ssm add-tags-to-resource --resource-type "Document" --resource-id "My-Document" --tags "Key=Quarter,Value=Q3-21"
   
   
**To add tags to a Maintenance Window**

This example updates a Maintenance Window with new tags. There is no output if the command succeeds.

Command::

   aws ssm add-tags-to-resource --resource-type "MaintenanceWindow" --resource-id "mw-03eb9db428EXAMPLE" --tags "Key=Stack,Value=Production"

   
**To add tags to a patch baseline**

This example updates a patch baseline with new tags. There is no output if the command succeeds.

Command::

   aws ssm add-tags-to-resource --resource-type "PatchBaseline" --resource-id "pb-012345EXAMPLE" --tags "Key=OS,Value=RHEL7"
