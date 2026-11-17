**To describe an identity provider**

The following ``describe-identity-provider`` example describes an identity provider named Facebook. ::

    aws cognito-idp describe-identity-provider \
        --user-pool-id us-west-2_aaaaaaaaa \
        --provider-name Facebook

Output::

    {
        "IdentityProvider": {
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "ProviderName": "Facebook",
            "ProviderType": "Facebook",
            "ProviderDetails": {
                "attributes_url": "https://graph.facebook.com/me?fields=",
                "attributes_url_add_attributes": "true",
            "authorize_scopes": "myscope",
                "authorize_url": "https://www.facebook.com/v2.9/dialog/oauth",
                "client_id": "11111",
                "client_secret": "11111",
                "token_request_method": "GET",
                "token_url": "https://graph.facebook.com/v2.9/oauth/access_token"
            },
            "AttributeMapping": {
                "username": "id"
            },
            "IdpIdentifiers": [],
            "LastModifiedDate": 1548105901.736,
            "CreationDate": 1548105901.736
        }
    }

For more information, see `User pool sign-in with third party identity providers <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-federation.html>`__ in the *Amazon Cognito Developer Guide*.
