**To update device status**

The following ``admin-update-device-status`` example sets the device remembered status for the device identified by device-key to not_remembered. ::

    aws cognito-idp admin-update-device-status \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com \
        --device-key xxxx \
        --device-remembered-status not_remembered

