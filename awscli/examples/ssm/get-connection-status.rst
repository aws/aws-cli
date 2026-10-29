**To display the connection status of a managed instance**

The following ``get-connection-status`` example returns the connection status of the specified managed instance. ::

    aws ssm get-connection-status \
        --target i-1234567890abcdef0

Output::

    {
        "Target": "i-1234567890abcdef0",
        "Status": "connected"
    }

For more information, see `AWS Systems Manager Session Manager <https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html>`__ in the *AWS Systems Manager User Guide*.
