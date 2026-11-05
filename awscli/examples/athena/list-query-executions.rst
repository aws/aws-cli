**To list the query IDs of the queries in a specified workgroup**

The following ``list-query-executions`` example lists a maximum of ten of the query IDs in the ``AthenaAdmin`` workgroup. ::

    aws athena list-query-executions \
        --work-group AthenaAdmin \
        --max-items 10

Output::

    {
        "QueryExecutionIds": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888",
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE99999"
        ]
    }

For more information, see `Working with Query Results, Output Files, and Query History <https://docs.aws.amazon.com/athena/latest/ug/querying.html>`__ in the *Amazon Athena User Guide*.