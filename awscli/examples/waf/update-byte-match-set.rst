**To update a byte match set**

The following ``update-byte-match-set`` example deletes a ByteMatchTuple object (filter) in a ByteMatchSet. ::

    aws waf update-byte-match-set \
        --cli-binary-format raw-in-base64-out \
        --byte-match-set-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates Action="DELETE",ByteMatchTuple={FieldToMatch={Type="HEADER",Data="referer"},TargetString="badrefer1",TextTransformation="NONE",PositionalConstraint="CONTAINS"}

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with string match conditions <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-string-conditions.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
