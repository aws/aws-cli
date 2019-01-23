**To set user settings**

This example sets the MFA delivery preference for username diego@example.com to EMAIL. 

Command::

  aws cognito-idp admin-set-user-settings --user-pool-id us-west-1_111111111 --username diego@example.com --mfa-options DeliveryMedium=EMAIL
  
