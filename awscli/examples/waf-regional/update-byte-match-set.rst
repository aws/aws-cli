**To update a byte match set**

The following ``update-byte-match-set`` example deletes a ``ByteMatchTuple`` object (filter) in a ``ByteMatchSet``. Because the ``updates`` value has embedded double quotes, you must surround the value with single quotes. ::

    aws waf-regional update-byte-match-set \
        --cli-binary-format raw-in-base64-out \
        --byte-match-set-id a123fae4-b567-8e90-1234-5ab67ac8ca90 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates 'Action="DELETE",ByteMatchTuple={FieldToMatch={Type="HEADER",Data="referer"},TargetString="badrefer1",TextTransformation="NONE",PositionalConstraint="CONTAINS"}'

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with string match conditions <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-string-conditions.html>`__ in the *AWS WAF Developer Guide*.
