**To update a rule**

The following ``update-rule`` example deletes a ``Predicate`` object in a rule. Because the ``updates`` value has embedded double quotes, you must surround the entire value with single quotes. ::

    aws waf-regional update-rule \
        --rule-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates 'Action="DELETE",Predicate={Negated=false,Type="ByteMatch",DataId="MyByteMatchSetID"}'

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with rules <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-rules.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
