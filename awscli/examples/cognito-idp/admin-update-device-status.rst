**To update device status**

This example sets the device remembered status for the device identified by device-key to not_remembered.

Command::

  aws cognito-idp admin-update-device-status --user-pool-id us-west-1_111111111 --username diego@example.com --device-key xxxx  --device-remembered-status not_remembered
  
