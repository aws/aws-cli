**To update device status**

The following ``admin-update-device-status`` example sets the device remembered status for the device identified by device-key to not_remembered. ::

    aws cognito-idp admin-update-device-status \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --device-key xxxx \
        --device-remembered-status not_remembered

This command produces no output.

For more information, see `Working with user devices in your user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-device-tracking.html>`__ in the *Amazon Cognito Developer Guide*.
