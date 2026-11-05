**To process query statement**

The following ``start-query-planning`` example submits a request to process a query statement. ::

    aws lakeformation start-query-planning \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "QueryPlanningContext": {
            "CatalogId": "123456789012",
            "DatabaseName": "tpc"
        },
        "QueryString": "select * from dl_tpc_household_demographics_gov where hd_income_band_sk=9"
    }

Output::

    {
        "QueryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }
