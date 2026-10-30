**To update user attributes**

The following ``admin-update-user-attributes`` example updates a custom user attribute CustomAttr1 for user diego@example.com. ::

    aws cognito-idp admin-update-user-attributes \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --user-attributes Name="custom:CustomAttr1",Value="Purple"

