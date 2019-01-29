**To set user MFA preference**

This example sets the user MFA preference to SMS.

Command::

  aws cognito-idp set-user-mfa-preference --access-token ACCESS_TOKEN --mfa-options DeliveryMedium="SMS",AttributeName="phone_number"

