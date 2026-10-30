**To update a size constraint set**

The following ``update-size-constraint-set`` example deletes a `SizeConstraint`` object (filters) in a size constraint set. Because the ``updates`` value contains embedded double quotes, you must surround the entire value with single quotes. ::

    aws waf-regional update-size-constraint-set \
        --size-constraint-set-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates 'Action="DELETE",SizeConstraint={FieldToMatch={Type="QUERY_STRING"},TextTransformation="NONE",ComparisonOperator="GT",Size=0}'

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with size constraint conditions <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-size-conditions.html>`__ in the *AWS WAF Developer Guide*.
