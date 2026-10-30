**To retrieve a list of IP sets**

The following ``list-ip-sets`` example retrieves all IP sets for the account that have regional scope. ::

    aws wafv2 list-ip-sets \
        --scope REGIONAL

Output::

    {
        "IPSets":[
            {
                "ARN":"arn:aws:wafv2:us-west-2:123456789012:regional/ipset/testip/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description":"",
                "Name":"testip",
                "LockToken":"a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Id":"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111  "
            }
        ],
        "NextMarker":"testip"
    } 

For more information, see `IP Sets and Regex Pattern Sets <https://docs.aws.amazon.com/waf/latest/developerguide/waf-referenced-set-managing.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
