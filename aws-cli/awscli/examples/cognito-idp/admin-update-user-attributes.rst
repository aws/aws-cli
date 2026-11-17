**To update user attributes**

The following ``admin-update-user-attributes`` example updates a custom user attribute CustomAttr1 for user diego@example.com. ::

    aws cognito-idp admin-update-user-attributes \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --user-attributes Name="custom:CustomAttr1",Value="Purple"

This command produces no output.

For more information, see `Working with user attributes <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html>`__ in the *Amazon Cognito Developer Guide*.
