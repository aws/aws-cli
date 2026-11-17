**To delete a user attribute**

The following ``admin-delete-user-attributes`` example deletes a custom attribute CustomAttr1 for user diego@example.com. ::

    aws cognito-idp admin-delete-user-attributes \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --user-attribute-names "custom:CustomAttr1"

This command produces no output.

For more information, see `Working with user attributes <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html>`__ in the *Amazon Cognito Developer Guide*.
