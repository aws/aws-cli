**To update a web ACL**

The following ``update-web-acl`` example deletes an ``ActivatedRule`` object in a WebACL. ::

    aws waf update-web-acl \
        --web-acl-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates Action="DELETE",ActivatedRule='{Priority=1,RuleId="WAFRule-1-Example",Action={Type="ALLOW"},Type="REGULAR"}'

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with Web ACLs <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-working-with.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
