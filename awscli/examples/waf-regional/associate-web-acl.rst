**To associate a web ACL with a resource**

The following ``associate-web-acl`` example associates a web ACL, specified by the web-acl-id, with a resource, specified by the resource-arn. The resource ARN can refer to either an application load balancer or an API Gateway. ::

    aws waf-regional associate-web-acl \
        --web-acl-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --resource-arn 12cs345-67cd-890b-1cd2-c3a4567d89f1

This command produces no output.

For more information, see `Working with Web ACLs <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-working-with.html>`__ in the *AWS WAF Developer Guide*.
