**To create a Resolver rule**

The following ``create-resolver-rule`` example creates a Resolver forwarding rule. The rule uses the outbound endpoint ``rslvr-out-d5e5920e37example`` to forward DNS queries for example.com to the IP address 192.0.2.44. ::

    aws route53resolver create-resolver-rule \
        --creator-request-id 2020-01-02-18:47 \
        --domain-name example.com \
        --name my-rule \
        --resolver-endpoint-id rslvr-out-d5e5920e37example \
        --rule-type FORWARD \
        --target-ips="Ip=192.0.2.44" 

Output::

    {
        "ResolverRule": {
            "Id": "rslvr-rr-42b60677c0example",
            "CreatorRequestId": "2020-01-02-18:47",
            "Arn": "arn:aws:route53resolver:us-west-2:111122223333:resolver-rule/rslvr-rr-42b60677c0example",
            "DomainName": "example.com.",
            "Status": "COMPLETE",
            "StatusMessage": "[Trace id: 1-5dc4b177-ff1d9d001a0f80005example] Successfully created Resolver Rule.",
            "RuleType": "FORWARD",
            "Name": "my-rule",
            "TargetIps": [
                {
                    "Ip": "192.0.2.44",
                    "Port": 53
                }
            ],
            "ResolverEndpointId": "rslvr-out-d5e5920e37example",
            "OwnerId": "111122223333",
            "ShareStatus": "NOT_SHARED"
        }
    }

Alternatively, when you have complicated parameters with multiple values, you can choose to include the parameters in a JSON file and then specify the file when you call ``create-resolver-rule``. Here's the command, which includes a parameter that specifies the name and location of the JSON file. ::

    aws route53resolver create-resolver-rule \
        --cli-input-json file://c:\temp\create-resolver-rule.json

Contents of ``create-resolver-rule.json``::

    {
        "CreatorRequestId": "2020-01-02-18:47",
        "Name": "my-rule",
        "RuleType": "FORWARD",
        "DomainName": "example.com",
        "TargetIps": [
            {
                "Ip": "192.0.2.44",
                "Port": 53
            }
        ],
        "ResolverEndpointId": "rslvr-out-d5e5920e37example",
        "Tags": [
            {
                "Key": "my-key",
                "Value": "my-value"
            }
        ]
    }

For more information about rules, see `Managing Forwarding Rules <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-rules-managing.html>`__ in the *Amazon Route 53 Developer Guide*.
