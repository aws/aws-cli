**To describe an application**

This example uses the ``describe-application`` command to describe an application. ::

    aws application-insights describe-application \
        --resource-group-name MYEC2

Output::

    {
        "ApplicationInfo": {
            "AccountId": "123456789012",
            "ResourceGroupName": "MYEC2",
            "LifeCycle": "ACTIVE",
            "OpsCenterEnabled": false,
            "CWEMonitorEnabled": true,
            "Remarks": "Monitoring application, detected 1 unconfigured component",
            "AutoConfigEnabled": true,
            "DiscoveryType": "RESOURCE_GROUP_BASED",
            "AttachMissingPermission": true
        }
    }