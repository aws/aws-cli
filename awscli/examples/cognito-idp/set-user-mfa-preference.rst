**To set user MFA preference**

This example sets the SMS and software MFA settings.

Command::

  aws cognito-idp set-user-mfa-preference --access-token ACCESS_TOKEN --sms-mfa-settings Enabled=true,PreferredMfa=true --software-mfa-settings Enabled=true,PreferredMfa=true

