**Example 1: To create data cell filter**

The following ``create-data-cells-filter`` example creates a data cell filter to allow one to grant access to certain columns based on row condition. ::

    aws lakeformation create-data-cells-filter \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "TableData": {
            "ColumnNames": ["p_channel_details", "p_start_date_sk", "p_promo_name"],
            "DatabaseName": "tpc",
            "Name": "developer_promotion",
            "RowFilter": {
                "FilterExpression": "p_promo_name='ese'"
            },
            "TableCatalogId": "123456789111",
            "TableName": "dl_tpc_promotion"
        }
    }

This command produces no output.

For more information, see `Data filtering and cell-level security in Lake Formation <https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html>`__ in the *AWS Lake Formation Developer Guide*.

**Example 2: To create column filter**

The following ``create-data-cells-filter`` example creates a data filter to allow one to grant access to certain columns. ::

    aws lakeformation create-data-cells-filter \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "TableData": {
            "ColumnNames": ["p_channel_details", "p_start_date_sk", "p_promo_name"],
            "DatabaseName": "tpc",
            "Name": "developer_promotion_allrows",
            "RowFilter": {
                "AllRowsWildcard": {}
            },
            "TableCatalogId": "123456789111",
            "TableName": "dl_tpc_promotion"
        }
    }

This command produces no output.

For more information, see `Data filtering and cell-level security in Lake Formation <https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html>`__ in the *AWS Lake Formation Developer Guide*.

**Example 3: To create data filter with exclude columns**

The following ``create-data-cells-filter`` example creates a data filter to allow one to grant access all except the mentioned columns. ::

    aws lakeformation create-data-cells-filter \
        --cli-input-json file://input.json

Contents of ``input.json``::

    {
        "TableData": {
            "ColumnWildcard": {
                "ExcludedColumnNames": ["p_channel_details", "p_start_date_sk"]
            },
            "DatabaseName": "tpc",
            "Name": "developer_promotion_excludecolumn",
            "RowFilter": {
                "AllRowsWildcard": {}
            },
            "TableCatalogId": "123456789111",
            "TableName": "dl_tpc_promotion"
        }
    }

This command produces no output.

For more information, see `Data filtering and cell-level security in Lake Formation <https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html>`__ in the *AWS Lake Formation Developer Guide*.

.. note::

   **TIMESTAMP data type not supported in RowFilter FilterExpression**

   AWS Lake Formation Data Cells Filters do **not** support ``TIMESTAMP`` columns
   in the ``RowFilter.FilterExpression`` predicate.  Attempting to use a timestamp
   column in the filter expression (e.g.
   ``"timestamp" > '2026-05-01 00:00:00'``) will return::

       InvalidInputException: TIMESTAMP data type not supported for row level filter predicate.

   **Tested expressions that all fail:**

   - ``"timestamp" > '2026-05-01 00:00:00'``
   - ``timestamp > date_sub(current_date(), 30)``
   - ``timestamp > cast(now() - interval 30 days as timestamp)``
   - ``timestamp >= current_timestamp - interval '30' day``
   - ``timestamp >= current_date() - INTERVAL 30 DAYS``

   **Workarounds:**

   - Filter on a *derived string column* (e.g., a partition column formatted as
     ``YYYY-MM-DD``) using string comparison instead of a native timestamp column.
   - Pre-process the table to store the date portion as a ``STRING`` or ``DATE``
     column and apply the row filter on that column.
   - Use column-level security (``ColumnNames`` / ``ExcludedColumnNames``) to
     restrict access to the timestamp column entirely rather than filtering by
     value.

   For more information see the
   `Data Cells Filters documentation <https://docs.aws.amazon.com/lake-formation/latest/dg/data-filtering.html>`__.

