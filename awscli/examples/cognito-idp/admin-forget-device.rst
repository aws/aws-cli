**To forget a device**

The following ``admin-forget-device`` example forgets a device for username jane@example.com. ::

    aws cognito-idp admin-forget-device \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username jane@example.com \
        --device-key us-west-2_abcd_1234-5678

This command produces no output.

