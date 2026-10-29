**To delete a Resolver rule**

The following ``delete-resolver-rule`` example deletes the specified rule. 

**Note** If a rule is associated with any VPCs, you must first disassociate the rule from the VPCs before you can delete it. ::

    aws route53resolver delete-resolver-rule \
        --resolver-rule-id rslvr-rr-5b3809426bexample

Output::

    {
        "ResolverRule": {
            "Id": "rslvr-rr-5b3809426bexample",
            "CreatorRequestId": "2020-01-03-18:47",
            "Arn": "arn:aws:route53resolver:us-west-2:123456789012:resolver-rule/rslvr-rr-5b3809426bexample",
            "DomainName": "zenith.example.com.",
            "Status": "DELETING",
            "StatusMessage": "[Trace id: 1-5dc5e05b-602e67b052cb74f05example] Deleting Resolver Rule.",
            "RuleType": "FORWARD",
            "Name": "my-resolver-rule",
            "TargetIps": [
                {
                    "Ip": "192.0.2.50",
                    "Port": 53
                }
            ],
            "ResolverEndpointId": "rslvr-out-d5e5920e3example",
            "OwnerId": "123456789012",
            "ShareStatus": "NOT_SHARED"
        }
    }

For more information, see `Managing forwarding rules <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-rules-managing.html#resolver-rules-managing-deleting>`__ in the *Amazon Route 53 Developer Guide*.
