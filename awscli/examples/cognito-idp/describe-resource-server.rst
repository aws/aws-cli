**To describe a resource server**

The following ``describe-resource-server`` example describes the resource server weather.example.com. ::

    aws cognito-idp describe-resource-server \
        --user-pool-id us-west-2_aaaaaaaaa \
        --identifier weather.example.com

Output::

    {
        "ResourceServer": {
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "Identifier": "weather.example.com",
            "Name": "Weather",
            "Scopes": [
                {
                    "ScopeName": "weather.update",
                    "ScopeDescription": "Update weather forecast"
                },
                {
                    "ScopeName": "weather.read",
                    "ScopeDescription": "Read weather forecasts"
                },
                {
                    "ScopeName": "weather.delete",
                    "ScopeDescription": "Delete a weather forecast"
                }
            ]
        }
    }

For more information, see `Scopes, M2M, and resource servers <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html>`__ in the *Amazon Cognito Developer Guide*.
