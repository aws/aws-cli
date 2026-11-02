**To set user settings**

The following ``set-user-settings`` example sets the MFA delivery preference to EMAIL. ::

    aws cognito-idp set-user-settings \
        --access-token ACCESS_TOKEN \
        --mfa-options DeliveryMedium=EMAIL

This command produces no output.

For more information, see `Adding MFA to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html>`__ in the *Amazon Cognito Developer Guide*.
