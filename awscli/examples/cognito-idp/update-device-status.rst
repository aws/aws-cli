**To update device status**

The following ``update-device-status`` example updates the status for a device to "not_remembered". ::

    aws cognito-idp update-device-status \
        --access-token ACCESS_TOKEN \
        --device-key DEVICE_KEY \
        --device-remembered-status "not_remembered"
