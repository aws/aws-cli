**To delete a resource server**

The following ``delete-resource-server`` example deletes a resource server named weather.example.com. ::

    aws cognito-idp delete-resource-server \
        --user-pool-id us-west-2_aaaaaaaaa \
        --identifier weather.example.com

This command produces no output.

For more information, see `Scopes, M2M, and resource servers <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html>`__ in the *Amazon Cognito Developer Guide*.
