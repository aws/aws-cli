**To retrieve state of a submitted query**

The following ``get-query-state`` example returns the state of a query previously submitted. ::

    aws lakeformation get-query-state \
        --query-id='a1b2c3d4-5678-90ab-cdef-EXAMPLE11111'

Output::

    {
        "State": "FINISHED"
    }
