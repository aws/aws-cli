**To get the current status of an operation**

The following ``get-operation-detail`` example returns the status of the specified operation. Some domain registration operations operate asynchronously and return a response before they finish. These operations return an operation ID that you can use to get the current status.

This command runs only in the ``us-east-1`` Region. If your default region is set to ``us-east-1``, you can omit the ``region`` parameter. ::

    aws route53domains get-operation-detail \
        --region us-east-1 \
        --operation-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Status": "SUCCESSFUL",
        "DomainName": "example.com",
        "Type": "DOMAIN_LOCK",
        "SubmittedDate": 1573749367.864
    }

For more information, see `Viewing the status of a domain registration <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-view-status.html>`__ in the *Amazon Route 53 Developer Guide*.
