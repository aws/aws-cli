**To delete a web ACL**

The following ``delete-web-acl`` example deletes the specified web ACL from your account. A web ACL can only be deleted when it's not associated with any resources. This call requires an ID, which you can obtain from the call, ``list-web-acls``, and a lock token, which you can obtain from the call ``list-web-acls`` or the call ``get-web-acl``. ::

    aws wafv2 delete-web-acl \
        --name test \
        --scope REGIONAL \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --lock-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

This command produces no output.

For more information, see `Managing and Using a Web Access Control List (Web ACL) <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
