**To delete an identity provider**

The following ``delete-identity-provider`` example deletes an identity provider. ::

    aws cognito-idp delete-identity-provider \
        --user-pool-id us-west-2_aaaaaaaaa \
        --provider-name Facebook

This command produces no output.

For more information, see `User pool sign-in with third party identity providers <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-federation.html>`__ in the *Amazon Cognito Developer Guide*.
