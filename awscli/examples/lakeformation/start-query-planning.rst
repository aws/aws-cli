**To process query statement**

The following ``start-query-planning`` example submits a request to process a query statement. ::

    aws lakeformation start-query-planning \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "QueryPlanningContext": {
            "CatalogId": "012345678901",
            "DatabaseName": "tpc"
        },
        "QueryString": "select * from dl_tpc_household_demographics_gov where hd_income_band_sk=9"
    }

Output::

    {
        "QueryId": "772a273f-4a62-4cda-8d98-69615ee8be9b"
    }
