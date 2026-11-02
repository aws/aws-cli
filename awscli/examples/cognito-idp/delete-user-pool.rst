**To delete a user pool**

The following ``delete-user-pool`` example deletes a user pool using the user pool id, us-west-2_aaaaaaaaa. ::

    aws cognito-idp delete-user-pool \
        --user-pool-id us-west-2_aaaaaaaaa

This command produces no output.

For more information, see `Authenticating users with Amazon Cognito user pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html>`__ in the *Amazon Cognito Developer Guide*.
