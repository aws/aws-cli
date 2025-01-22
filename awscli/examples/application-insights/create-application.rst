**To create an application from a resource group**

This example uses the ``create-application command`` to create an application from a resource group. ::

    aws application-insights create-application \
        --resource-group-name myapp

Output::

    {
        "ApplicationInfo": {
            "AccountId": "123456789012",
            "ResourceGroupName": "myapp",
            "LifeCycle": "CREATING",
            "OpsCenterEnabled": false,
            "CWEMonitorEnabled": false,
            "Remarks": "",
            "AutoConfigEnabled": false,
            "DiscoveryType": "RESOURCE_GROUP_BASED",
            "AttachMissingPermission": false
        }
    }