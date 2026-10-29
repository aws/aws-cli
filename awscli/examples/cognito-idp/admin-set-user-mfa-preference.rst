**To set the user MFA preference**

The following ``admin-set-user-mfa-preference`` example sets the SMS MFA preference for username diego@example.com. ::

    aws cognito-idp admin-set-user-mfa-preference \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --sms-mfa-settings Enabled=false,PreferredMfa=false

This command produces no output.

