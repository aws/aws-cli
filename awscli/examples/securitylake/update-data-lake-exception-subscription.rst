**To update notification subscription for Security Lake exceptions**

The following ``update-data-lake-exception-subscription`` example updates the notification subscription that notifies users of Security Lake exceptions. ::

    aws securitylake update-data-lake-exception-subscription \
        --notification-endpoint "123456789012" \
        --exception-time-to-live 30 \
        --subscription-protocol "email"

This command produces no output.

For more information, see `Troubleshooting Amazon Security Lake <https://docs.aws.amazon.com/security-lake/latest/userguide/securitylake-data-lake-troubleshoot.html>`__ in the *Amazon Security Lake User Guide*.