**To create a maintenance window that runs only once**

The following ``create-maintenance-window`` creates a new maintenance window that only runs one time at the specified date and time. ::

    aws ssm create-maintenance-window \
        --name test \
        --schedule "at(2019-05-14T15:55:00)" \
        --duration 5 \
        --cutoff 2 \
        --allow-unassociated-targets

Output::

    {
        "WindowId": "mw-01234567890abcdef"
    }

For more information, see `Maintenance Windows <https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html>`_ in the *AWS Systems Manager User Guide*.
