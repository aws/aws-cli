**To list IP addresses for a specified inbound or outbound endpoint**

The following ``list-resolver-endpoint-ip-addresses`` example lists information about the IP addresses that are associated with the inbound endpoint ``rslvr-in-f9ab8a03f1example``. You can also use ``list-resolver-endpoint-ip-addresses`` for outbound endpoints by specifying the applicable endpoint ID. ::

    aws route53resolver list-resolver-endpoint-ip-addresses \
        --resolver-endpoint-id rslvr-in-f9ab8a03f1example

Output::

    {
        "MaxResults": 10,
        "IpAddresses": [
            {
                "IpId": "rni-1de60cdbfeexample",
                "SubnetId": "subnet-ba47exam",
                "Ip": "192.0.2.44",
                "Status": "ATTACHED",
                "StatusMessage": "This IP address is operational.",
                "CreationTime": "2020-01-03T23:02:29.587Z",
                "ModificationTime": "2020-01-03T23:03:05.555Z"
            },
            {
                "IpId": "rni-aac7085e38example",
                "SubnetId": "subnet-12d8exam",
                "Ip": "192.0.2.45",
                "Status": "ATTACHED",
                "StatusMessage": "This IP address is operational.",
                "CreationTime": "2020-01-03T23:02:29.593Z",
                "ModificationTime": "2020-01-03T23:02:55.060Z"
            }
        ]
    }

For more information about the values in the output, see `Values that you specify when you create or edit inbound endpoints <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries-values.html>`__ and `Values that you specify when you create or edit outbound endpoints <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries-endpoint-values.html>`__ in the *Amazon Route 53 Developer Guide*.
