**To update user attributes**

The following ``update-user-attributes`` example updates the user attribute "nickname". ::

    aws cognito-idp update-user-attributes \
        --access-token ACCESS_TOKEN \
        --user-attributes Name="nickname",Value="Dan"

Output::

    {
        "CodeDeliveryDetailsList": []
    }

For more information, see `Working with user attributes <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html>`__ in the *Amazon Cognito Developer Guide*.
