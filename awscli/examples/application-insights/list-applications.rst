**To list all applications**

This example uses the ``list-applications`` command to lists the applications that you are monitoring. ::

    aws application-insights list-applications

Output::

    {
        "ApplicationInfoList": [{
            "AccountId": "123456789012",
            "ResourceGroupName": "MYEC2",
            "LifeCycle": "ACTIVE",
            "OpsCenterEnabled": false,
            "CWEMonitorEnabled": true,
            "Remarks": "",
            "AutoConfigEnabled": true,
            "DiscoveryType": "RESOURCE_GROUP_BASED",
            "AttachMissingPermission": true
        }]
    }