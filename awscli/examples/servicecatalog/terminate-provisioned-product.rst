**To terminate a provisioned product**

The following ``terminate-provisioned-product`` example terminates a provisioned product. ::

    aws servicecatalog terminate-provisioned-product \
        --provisioned-product-id pp-7z4t3k4hxxxxx

Output::

    {
        "RecordDetail": {
            "RecordId": "rec-sbwnhzld3xxxx",
            "ProvisionedProductName": "test2",
            "Status": "CREATED",
            "CreatedTime": "2025-12-31T15:23:55.051000-06:00",
            "UpdatedTime": "2025-12-31T15:23:55.051000-06:00",
            "ProvisionedProductType": "CFN_STACK",
            "RecordType": "TERMINATE_PROVISIONED_PRODUCT",
            "ProvisionedProductId": "pp-7z4t3k4hxxxxx",
            "ProductId": "prod-j6pd3hf6xxxxx",
            "ProvisioningArtifactId": "pa-sbhovlh7wxxxx",
            "PathId": "lpv3-y3fnkeslpxxxx",
            "RecordErrors": [],
            "RecordTags": [],
            "LaunchRoleArn": "arn:aws:iam::123456789012:role/TestLaunchRole"
        }
    }

For more information, see `Managing Provisioned Products <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/provisioned-products.html>`__ in the *AWS Service Catalog User Guide*.
