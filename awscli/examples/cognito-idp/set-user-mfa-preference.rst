**To set user MFA settings**

The following ``set-user-mfa-preference`` example modifies the MFA delivery options. It changes the MFA delivery medium to SMS. ::

    aws cognito-idp set-user-mfa-preference \
        --access-token "eyJra12345EXAMPLE" \
        --software-token-mfa-settings Enabled=true,PreferredMfa=true \
        --sms-mfa-settings Enabled=false,PreferredMfa=false

This command produces no output.

For more information, see `Adding MFA to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html>`__ in the *Amazon Cognito Developer Guide*.