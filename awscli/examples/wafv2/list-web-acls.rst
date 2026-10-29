**To retrieve the web ACLs for a scope**

The following ``list-web-acls`` example retrieves all web ACLs that are defined for the account for the specified scope. ::

    aws wafv2 list-web-acls \
        --scope REGIONAL

Output::

    {
        "NextMarker":"Testt",
        "WebACLs":[
            {
                "ARN":"arn:aws:wafv2:us-west-2:123456789012:regional/webacl/Testt/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Description":"sssss",
                "Name":"Testt",
                "LockToken":"a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Id":"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Managing and Using a Web Access Control List (Web ACL) <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
