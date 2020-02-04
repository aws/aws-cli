**To list tables**

The following ``list-tables`` example lists all of the tables associated with the current AWS account and Region. ::

    aws dynamodb list-tables

Output::

    {
        "TableNames": [
            "Forum", 
            "ProductCatalog", 
            "Reply", 
            "Thread", 
        ]
    }

For more information, see `Listing Table Names <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.Basics.html#WorkingWithTables.Basics.ListTables>`__ in the *Amazon DynamoDB Developer Guide*.
