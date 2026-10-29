**To confirm user registration**

The following ``admin-confirm-sign-up`` example confirms user jane@example.com. ::

    aws cognito-idp admin-confirm-sign-up \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username jane@example.com

This command produces no output.

For more information, see `Signing up and confirming user accounts <https://docs.aws.amazon.com/cognito/latest/developerguide/signing-up-users-in-your-app.html>`__ in the *Amazon Cognito Developer Guide*.
