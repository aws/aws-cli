**To update a SQL Injection Match Set**

The following ``update-sql-injection-match-set`` example deletes a ``SqlInjectionMatchTuple`` object (filters) in a SQL injection match set. Because the ``updates`` value contains embedded double quotes, you must surround the entire value in single quotes. ::

    aws waf-regional update-sql-injection-match-set \
        --sql-injection-match-set-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates 'Action="DELETE",SqlInjectionMatchTuple={FieldToMatch={Type="QUERY_STRING"},TextTransformation="URL_DECODE"}'

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with SQL injection match conditions <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-sql-conditions.html>`__ in the *AWS WAF Developer Guide*.
