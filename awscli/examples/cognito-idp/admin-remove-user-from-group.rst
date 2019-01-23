**To remove a user from a group**

This example removes jane@example.com from SampleGroup. 

Command::

  aws cognito-idp admin-remove-user-from-group --user-pool-id us-west-1_111111111 --username jane@example.com --group-name SampleGroup
