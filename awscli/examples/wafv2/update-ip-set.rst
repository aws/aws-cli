**To modify the settings for an existing IP set**

The following ``update-ip-set`` example updates the settings for the specified IP set. This call requires an ID, which you can obtain from the call, ``list-ip-sets``, and a lock token which you can obtain from the calls, ``list-ip-sets`` and ``get-ip-set``. This call also returns a lock token that you can use for a subsequent update. ::

    aws wafv2 update-ip-set \
        --name testip \
        --scope REGIONAL \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --addresses 198.51.100.0/16 \
        --lock-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "NextLockToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `IP Sets and Regex Pattern Sets <https://docs.aws.amazon.com/waf/latest/developerguide/waf-referenced-set-managing.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
