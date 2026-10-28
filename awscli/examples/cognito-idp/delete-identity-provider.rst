**To delete an identity provider**

The following ``delete-identity-provider`` example deletes an identity provider. This command produces no output. ::

    aws cognito-idp delete-identity-provider \
        --user-pool-id us-west-2_aaaaaaaaa \
        --provider-name Facebook

