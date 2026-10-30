**To retrieve state of a submitted query**

The following ``get-query-state`` example returns the state of a query previously submitted. ::

    aws lakeformation get-query-state \
        --query-id='1234273f-4a62-4cda-8d98-69615ee8be9b'

Output::

    {
        "State": "FINISHED"
    }
