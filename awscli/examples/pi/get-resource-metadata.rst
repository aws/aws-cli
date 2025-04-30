**To get resource metadata for a database**

The following ``get-resource-metadata`` example gets the resource metadata for the database ``db-loadtest-0`` with the report ID ``report-0d99cc91c4422ee61``. The response shows that SQL digest statistics are enabled. ::

    aws pi get-resource-metadata \
        --service-type RDS \
        --identifier db-loadtest-0

Output::

    {    
        "Identifier": "db-loadtest-0",
        "Features":{
            "SQL_DIGEST_STATISTICS":{
                "Status": "ENABLED"
            }
        }
    }

For more information about SQL statistics for Performance Insights, see `SQL statistics for Performance Insights <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/sql-statistics.html>`__ in the *Amazon RDS User Guide* and `SQL statistics for Performance Insights <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/sql-statistics.html>`__ in the *Amazon Aurora User Guide*.