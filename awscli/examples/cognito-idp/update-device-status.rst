**To update device status**

The following ``update-device-status`` example updates the status for a device to "not_remembered". ::

    aws cognito-idp update-device-status \
        --access-token ACCESS_TOKEN \
        --device-key DEVICE_KEY \
        --device-remembered-status "not_remembered"

This command produces no output.

For more information, see `Working with user devices in your user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-device-tracking.html>`__ in the *Amazon Cognito Developer Guide*.
