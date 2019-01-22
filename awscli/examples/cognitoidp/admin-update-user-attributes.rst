**To delete a user attribute**

This example updates a custom user attribute CustomAttr1 for user diego@example.com.

Command::

  aws cognito-idp admin-update-user-attributes --user-pool-id us-west-1_111111111 --username diego@example.com  Name="custom:CustomAttr1",Value="Purple"

