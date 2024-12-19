**To update an application and its settings**

This example uses the ``update-application`` command to update an application's settings to enable SSM Ops Center. ::

    aws application-insights update-application \
        --resource-group-name ec2 —ops-center-enabled

Output::

    {
        "ApplicationInfo": {
            "AccountId": "012345678901",
            "ResourceGroupName": "ec2",
            "LifeCycle": "ACTIVE",
            "OpsCenterEnabled": true,
            "CWEMonitorEnabled": true,
            "Remarks": "",
            "AutoConfigEnabled": true,
            "DiscoveryType": "RESOURCE_GROUP_BASED",
            "AttachMissingPermission": true
        }
    }