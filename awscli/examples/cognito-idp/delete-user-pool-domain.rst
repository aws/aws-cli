**To delete a user pool domain**

The following ``delete-user-pool-domain`` example deletes a user pool domain named ``my-domain``. ::

    aws cognito-idp delete-user-pool-domain \
        --user-pool-id us-west-2_aaaaaaaaa \
        --domain my-domain

This command produces no output.

For more information, see `Configuring a user pool domain <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-assign-domain.html>`__ in the *Amazon Cognito Developer Guide*.
