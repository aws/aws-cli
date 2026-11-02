**To retrieve a list of custom rule groups**

The following ``list-rule-groups`` example retrieves all custom rule groups that are defined for the account for the specified scope. ::

    aws wafv2 list-rule-groups \
        --scope REGIONAL

Output::

    {
        "RuleGroups":[
            {
                "ARN":"arn:aws:wafv2:us-west-2:123456789012:regional/rulegroup/TestRuleGroup/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description":"",
                "Name":"TestRuleGroup",
                "LockToken":"a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Id":"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "ARN":"arn:aws:wafv2:us-west-2:123456789012:regional/rulegroup/test/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Description":"",
                "Name":"test",
                "LockToken":"a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Id":"a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ],
        "NextMarker":"test"
    }

For more information, see `Managing Your Own Rule Groups <https://docs.aws.amazon.com/waf/latest/developerguide/waf-user-created-rule-groups.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
