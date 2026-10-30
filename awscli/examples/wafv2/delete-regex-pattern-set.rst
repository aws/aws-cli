**To delete a regex pattern set**

The following ``delete-regex-pattern-set`` example deletes the specified regex pattern set. This call requires an ID, which you can obtain from the call, ``list-regex-pattern-sets``, and a lock token, which you can obtain from the call ``list-regex-pattern-sets`` or the call ``get-regex-pattern-set``. ::

    aws wafv2 delete-regex-pattern-set \
        --name regexPatterSet01 \
        --scope REGIONAL \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --lock-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

This command produces no output.

For more information, see `IP Sets and Regex Pattern Sets <https://docs.aws.amazon.com/waf/latest/developerguide/waf-referenced-set-managing.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
