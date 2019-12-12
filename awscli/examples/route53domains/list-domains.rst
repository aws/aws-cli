**To list the domains that are registered with the current AWS account**

The following ``list-domains`` command lists summary information about the domains that are registered with the current AWS account. ::

    aws route53domains list-domains

Output::

    {
        "Domains": [
            {
                "DomainName": "example.com",
                "AutoRenew": true,
                "TransferLock": true,
                "Expiry": 1602712345.0
            },
            {
                "DomainName": "example.net",
                "AutoRenew": true,
                "TransferLock": true,
                "Expiry": 1602723456.0
            },
            {
                "DomainName": "example.org",
                "AutoRenew": true,
                "TransferLock": true,
                "Expiry": 1602734567.0
            }
        ]
    }
