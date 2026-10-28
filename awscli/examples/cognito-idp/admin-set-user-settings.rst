**To set user settings**

The following ``admin-set-user-settings`` example sets the MFA delivery preference for username diego@example.com to EMAIL. ::

    aws cognito-idp admin-set-user-settings --user-pool-id us-west-2_aaaaaaaaa --username diego@example.com --mfa-options DeliveryMedium=EMAIL

