**To list all available provisioned products**

The following ``scan-provisioned-products`` example lists available provisioned products. ::

    aws servicecatalog scan-provisioned-products

Output::

    {
        "ProvisionedProducts": [
            {
                "Status": "ERROR",
                "Arn": "arn:aws:servicecatalog:us-west-2:123456789012:stack/mytestppname3/pp-abcd27bm4mldq",
                "StatusMessage": "AmazonCloudFormationException  Parameters: [KeyName] must have values (Service: AmazonCloudFormation; Status Code: 400; Error Code: ValidationError; Request ID: a1b2c3d4-5678-90ab-cdef-EXAMPLE11111)",
                "Id": "pp-abcd27bm4mldq",
                "Type": "CFN_STACK",
                "IdempotencyToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreatedTime": 1577222793.358,
                "Name": "mytestppname3",
                "LastRecordId": "rec-tfuawdabcdxge"
            }
        ]
    }

For more information, see `Managing Provisioned Products <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/provisioned-products.html>`__ in the *AWS Service Catalog Administrator Guide*.
