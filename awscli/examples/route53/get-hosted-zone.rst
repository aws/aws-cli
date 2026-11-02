**To get information about a hosted zone**

The following ``get-hosted-zone`` example gets information about the hosted zone with an ``id`` of ``Z1R8UBAEXAMPLE``. ::

    aws route53 get-hosted-zone \
        --id Z1R8UBAEXAMPLE

Output::

    {
        "HostedZone": {
            "Id": "/hostedzone/Z1R8UBAEXAMPLE",
            "Name": "example.com.",
            "CallerReference": "2014-04-01-18:47",
            "Config": {
                "Comment": "command-line version",
                "PrivateZone": false
            },
            "ResourceRecordSetCount": 2
        },
        "DelegationSet": {
            "NameServers": [
                "ns-2048.awsdns-64.com",
                "ns-2049.awsdns-65.net",
                "ns-2050.awsdns-66.org",
                "ns-2051.awsdns-67.co.uk"
            ]
        }
    }

For more information, see `Working with hosted zones <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zones-working-with.html>`__ in the *Amazon Route 53 Developer Guide*.
