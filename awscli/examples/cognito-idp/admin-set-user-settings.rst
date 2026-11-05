**To set user settings**

The following ``admin-set-user-settings`` example sets the MFA delivery preference for username diego@example.com to EMAIL. ::

    aws cognito-idp admin-set-user-settings \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --mfa-options DeliveryMedium=EMAIL

This command produces no output.

For more information, see `Adding MFA to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html>`__ in the *Amazon Cognito Developer Guide*.
