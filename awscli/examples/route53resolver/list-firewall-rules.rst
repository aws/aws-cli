**To list firewall rules**

The following ``list-firewall-rules`` example list all of your DNS Firewall rules within a firewall rule group. ::

    aws route53resolver list-firewall-rules \
        --firewall-rule-group-id rslvr-frg-47f93271fexample

Output::

    {
        "FirewallRules": [
            {
                "FirewallRuleGroupId": "rslvr-frg-47f93271fexample",
                "FirewallDomainListId": "rslvr-fdl-9e956e9ffexample",
                "Name": "allow-rule",
                "Priority": 101,
                "Action": "ALLOW",
                "CreatorRequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreationTime": "2021-05-25T21:44:00.346093Z",
                "ModificationTime": "2021-05-25T21:44:00.346093Z"
            }
        ]
    }

For more information, see `Managing rule groups and rules in DNS Firewall <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-rule-group-managing.html>`__ in the *Amazon Route 53 Developer Guide*.