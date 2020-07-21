**To get information about a maintenance window**

The following ``get-maintenance-window`` example retrieves details about the specified maintenance window. ::

    aws ssm get-maintenance-window \
        --window-id "mw-03eb9db428EXAMPLE"

Output::

    {
        "Cutoff": 1,
        "Name": "TestMaintWin",
        "Schedule": "cron(0 */30 * * * ? *)",
        "Enabled": true,
        "AllowUnassociatedTargets": false,
        "WindowId": "mw-03eb9db428EXAMPLE",
        "ModifiedDate": 1487614445.527,
        "CreatedDate": 1487614445.527,
        "Duration": 2
    }

For more information, see `View Information About Maintenance Windows (AWS CLI)  <https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows-cli-tutorials-describe.html>`__ in the *AWS Systems Manager User Guide*.
