**To set user MFA settings**

This example modifies the MFA delivery options. It changes the MFA delivery medium to SMS.

Command::

  aws cognito-idp set-user-mfa-preference --access-token ACCESS_TOKEN --sms-mfa-settings Enabled=true,PreferredMfa=true

