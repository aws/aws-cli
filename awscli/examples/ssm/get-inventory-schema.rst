**Example 1: To view your inventory schema**

The following ``get-inventory-schema`` example returns a list of inventory type names for the account. ::

    aws ssm get-inventory-schema

Output::

    {
        "Schemas": [
            {
                "TypeName": "AWS:AWSComponent",
                "Version": "1.0",
                "Attributes": [
                    {
                        "Name": "Name",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "ApplicationType",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Publisher",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Version",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "InstalledTime",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Architecture",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "URL",
                        "DataType": "STRING"
                    }
                ]
        }
        ],
        "NextToken": "--token string truncated--"
    }

For more information, see `Metadata collected by Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-schema.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To view the inventory schema for a specific inventory type**

The following ``get-inventory-schema`` example returns the inventory schema for the ``AWS:AWSComponent`` inventory type. ::

    aws ssm get-inventory-schema \
        --type-name "AWS:AWSComponent"

Output::

    {
        "Schemas": [
            {
                "TypeName": "AWS:AWSComponent",
                "Version": "1.0",
                "Attributes": [
                    {
                        "Name": "Name",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "ApplicationType",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Publisher",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Version",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "InstalledTime",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "Architecture",
                        "DataType": "STRING"
                    },
                    {
                        "Name": "URL",
                        "DataType": "STRING"
                    }
                ]
            }
        ]
    }

For more information, see `Metadata collected by Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-schema.html>`__ in the *AWS Systems Manager User Guide*.
