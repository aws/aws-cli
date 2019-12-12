**To get the current status of an operation**

Some domain registration operations don't finish immediately. These operations return an operation ID that you can use to get the current status. The following ``get-operation-detail`` command returns the status of the specified operation. ::

    aws route53domains get-operation-detail \
        --operation-id edbd8d63-7fe7-4343-9bc5-54033example

Output::

    {
        "OperationId": "edbd8d63-7fe7-4343-9bc5-54033example",
        "Status": "SUCCESSFUL",
        "DomainName": "example.com",
        "Type": "DOMAIN_LOCK",
        "SubmittedDate": 1573749367.864
    }
