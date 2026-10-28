**To set user settings**

The following ``set-user-settings`` example sets the MFA delivery preference to EMAIL. This command produces no output. ::

    aws cognito-idp set-user-settings \
        --access-token ACCESS_TOKEN \
        --mfa-options DeliveryMedium=EMAIL

