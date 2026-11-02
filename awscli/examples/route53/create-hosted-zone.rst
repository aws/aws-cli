**To create a hosted zone**

The following ``create-hosted-zone`` example adds a hosted zone named ``example.com`` using the caller reference ``2014-04-01-18:47``. The optional comment includes a space, so it must be enclosed in quotation marks. ::

    aws route53 create-hosted-zone \
        --name example.com \
        --caller-reference 2014-04-01-18:47 \
        --hosted-zone-config Comment="command-line version"

Output::

    {
        "Location": "https://route53.amazonaws.com/2013-04-01/hostedzone/Z1D633PJEXAMPLE",
        "HostedZone": {
            "Id": "/hostedzone/Z1D633PJEXAMPLE",
            "Name": "example.com.",
            "CallerReference": "2014-04-01-18:47",
            "Config": {
                "Comment": "command-line version",
                "PrivateZone": false
            },
            "ResourceRecordSetCount": 2
        },
        "ChangeInfo": {
            "Id": "/change/C1PA6795EXAMPLE",
            "Status": "PENDING",
            "SubmittedAt": "2014-04-01T18:47:10.123Z"
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

For more information, see `Creating a public hosted zone <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/CreatingHostedZone.html>`__ in the *Amazon Route 53 Developer Guide*.
