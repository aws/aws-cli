**To update a resource server**

The following ``update-resource-server`` example updates the resource server Weather. It adds a new scope. ::

    aws cognito-idp update-resource-server \
        --user-pool-id us-west-2_aaaaaaaaa \
        --identifier weather.example.com \
        --name Weather \
        --scopes ScopeName=NewScope,ScopeDescription="New scope description"

Output::

    {
        "ResourceServer": {
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "Identifier": "weather.example.com",
            "Name": "Happy",
            "Scopes": [
                {
                    "ScopeName": "NewScope",
                    "ScopeDescription": "New scope description"
                }
            ]
        }
    }

For more information, see `Scopes, M2M, and resource servers <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html>`__ in the *Amazon Cognito Developer Guide*.
