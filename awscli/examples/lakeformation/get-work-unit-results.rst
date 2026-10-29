**To retrieve work units of given query**

The following ``get-work-unit-results`` example returns the work units resulting from the query. ::

    aws lakeformation get-work-unit-results \
        --query-id='a1b2c3d4-5678-90ab-cdef-EXAMPLE11111' \
        --work-unit-id '0' \
        --work-unit-token 'B2fMSdmQXe9umX8Ux8XCo4=' outfile

This command produces no output. The results are saved to the file ``outfile``.
