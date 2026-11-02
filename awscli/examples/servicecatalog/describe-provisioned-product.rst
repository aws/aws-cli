**To describe a provisioned product**

The following ``describe-provisioned-product`` example displays details for the specified provisioned product. ::

    aws servicecatalog describe-provisioned-product \
        --id pp-dpom27bm4abcd

Output::

    {
        "ProvisionedProductDetail": {
            "Status": "ERROR",
            "CreatedTime": 1577222793.358,
            "Arn": "arn:aws:servicecatalog:us-west-2:123456789012:stack/mytestppname3/pp-dpom27bm4abcd",
            "Id": "pp-dpom27bm4abcd",
            "StatusMessage": "AmazonCloudFormationException  Parameters: [KeyName] must have values (Service: AmazonCloudFormation; Status Code: 400; Error Code: ValidationError; Request ID: a1b2c3d4-5678-90ab-cdef-EXAMPLE11111)",
            "IdempotencyToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "LastRecordId": "rec-tfuawdjovzxge",
            "Type": "CFN_STACK",
            "Name": "mytestppname3"
        },
        "CloudWatchDashboards": []
    }

For more information, see `Managing Provisioned Products <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/provisioned-products.html>`__ in the *AWS Service Catalog Administrator Guide*.
