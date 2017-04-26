**To view your inventory schema**

This example returns a list of inventory type names for the account.

Command::

  aws ssm get-inventory-schema

Output::

  {
    "Schemas": [
        {
            "TypeName": "AWS:AWSComponent",
            "Version": "1.0",
            "Attributes": [
                {
                    "DataType": "STRING",
                    "Name": "Name"
                },
                {
                    "DataType": "STRING",
                    "Name": "ApplicationType"
                },
                {
                    "DataType": "STRING",
                    "Name": "Publisher"
                },
                {
                    "DataType": "STRING",
                    "Name": "Version"
                },
                {
                    "DataType": "STRING",
                    "Name": "InstalledTime"
                },
                {
                    "DataType": "STRING",
                    "Name": "Architecture"
                },
                {
                    "DataType": "STRING",
                    "Name": "URL"
                }
            ]
        },
        ...
	}
  }