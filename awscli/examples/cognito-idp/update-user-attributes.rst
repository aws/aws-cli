**To update user attributes**

The following ``update-user-attributes`` example updates the user attribute "nickname". ::

    aws cognito-idp update-user-attributes \
        --access-token ACCESS_TOKEN \
        --user-attributes Name="nickname",Value="Dan"
