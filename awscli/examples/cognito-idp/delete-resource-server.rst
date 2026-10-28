**To delete a resource server**

The following ``delete-resource-server`` example deletes a resource server named weather.example.com. This command produces no output. ::

    aws cognito-idp delete-resource-server \
        --user-pool-id us-west-2_aaaaaaaaa \
        --identifier weather.example.com

