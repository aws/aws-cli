**To list the status of operations that return an operation ID**

The following ``list-operations`` example lists summary information, including the status, about the current domain-registration operations. Some domain registration operations run asynchronously and return a response before they finish. These operations return an operation ID that you can use to get the current status.

This command runs only in the ``us-east-1`` Region. If your default region is set to ``us-east-1``, you can omit the ``region`` parameter. ::

    aws route53domains list-operations \
        --region us-east-1

Output::

    {
        "Operations": [
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Status": "SUCCESSFUL",
                "Type": "DOMAIN_LOCK",
                "SubmittedDate": 1455321739.986
            },
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "SUCCESSFUL",
                "Type": "UPDATE_NAMESERVER",
                "SubmittedDate": 1468960475.109
            },
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "SUCCESSFUL",
                "Type": "RENEW_DOMAIN",
                "SubmittedDate": 1473561835.943
            },
            {
                "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Status": "SUCCESSFUL",
                "Type": "UPDATE_DOMAIN_CONTACT",
                "SubmittedDate": 1547501003.41
            }
        ]
    }

The output includes all the operations that return an operation ID and that you have performed on all the domains that you have ever registered using the current AWS account. If you want to get only the operations that you submitted after a specified date, you can include the ``submitted-since`` parameter and specify a date in Unix format and Coordinated Universal Time (UTC). The following command gets the status of all operations that were submitted after 12:00 am UTC on January 1, 2020. ::

    aws route53domains list-operations \
        --submitted-since 1577836800

For more information, see `Viewing the status of a domain registration <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-view-status.html>`__ in the *Amazon Route 53 Developer Guide*.
