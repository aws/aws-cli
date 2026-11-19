**To retrieve the SMS sandbox status for the calling Amazon Web Services account**

The following `get-sms-sandbox-account-status` example retrieves the SMS sandbox status of your Amazon Web Services account in the current region. ::

    aws sns get-sms-sandbox-account-status

Output::

    {
        "IsInSandbox": true
    }