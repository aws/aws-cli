**To delete a user pool client**

The following ``delete-user-pool-client`` example deletes a user pool client. ::

    aws cognito-idp delete-user-pool-client \
        --user-pool-id us-west-2_aaaaaaaaa \
        --client-id 38fjsnc484p94kpqsnet7mpld0

This command produces no output.

For more information, see `Application-specific settings with app clients <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html>`__ in the *Amazon Cognito Developer Guide*.
