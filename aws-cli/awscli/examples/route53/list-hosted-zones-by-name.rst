**Example 1: To list hosted zones ordered by domain name**

The following ``list-hosted-zones-by-name`` example lists up to 100 hosted zones ordered by domain name. ::

    aws route53 list-hosted-zones-by-name

Output::

    {
        "HostedZones": [
            {
                "ResourceRecordSetCount": 2,
                "CallerReference": "test20150527-2",
                "Config": {
                    "Comment": "test2",
                    "PrivateZone": false
                },
                "Id": "/hostedzone/Z119WBBTVP5WFX",
                "Name": "2.example.com."
            },
            {
                "ResourceRecordSetCount": 2,
                "CallerReference": "test20150527-1",
                "Config": {
                    "Comment": "test",
                    "PrivateZone": false
                },
                "Id": "/hostedzone/Z3P5QSUBK4POTI",
                "Name": "www.example.com."
            }
        ],
        "IsTruncated": false,
        "MaxItems": "100"
    }

**Example 2: To list hosted zones beginning with a specified domain name**

The following ``list-hosted-zones-by-name`` example lists hosted zones ordered by name, beginning with ``www.example.com``. ::

    aws route53 list-hosted-zones-by-name \
        --dns-name www.example.com

Output::

    {
        "HostedZones": [
            {
                "ResourceRecordSetCount": 2,
                "CallerReference": "mwunderl20150527-1",
                "Config": {
                    "Comment": "test",
                    "PrivateZone": false
                },
                "Id": "/hostedzone/Z3P5QSUBK4POTI",
                "Name": "www.example.com."
            }
        ],
        "DNSName": "www.example.com",
        "IsTruncated": false,
        "MaxItems": "100"
    }

For more information, see `Listing public hosted zones <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/ListInfoOnHostedZone.html>`__ in the *Amazon Route 53 Developer Guide*.
