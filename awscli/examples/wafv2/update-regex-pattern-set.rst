**To  modify the settings for an existing regex pattern set**

The following ``update-regex-pattern-set`` example updates the settings for the specified regex pattern set. This call requires an ID, which you can obtain from the call, ``list-regex-pattern-sets``, and a lock token which you can obtain from the calls, ``list-regex-pattern-sets`` and ``get-regex-pattern-set``. This call also returns a lock token that you can use for a subsequent update. ::

    aws wafv2 update-regex-pattern-set \
        --name ExampleRegex \
        --scope REGIONAL \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --regular-expression-list RegexString="^.+$"  \
        --lock-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "NextLockToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `IP Sets and Regex Pattern Sets <https://docs.aws.amazon.com/waf/latest/developerguide/waf-referenced-set-managing.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
