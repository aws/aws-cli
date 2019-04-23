**To update the service setting for managed instance activation**

This example updates the current service setting tier for managed instance activations in the specified region to use advanced instances.  There is no output if the command succeeds.  For more information, see `Using the Advanced-Instances Tier`_ in the *AWS Systems Manager User Guide*.

.. _`Using the Advanced-Instances Tier`: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-managedinstances-advanced.html

Command::

   aws ssm update-service-setting --setting-id arn:aws:ssm:us-east-1:123456789012:servicesetting/ssm/managed-instance/activation-tier --setting-value advanced
   
