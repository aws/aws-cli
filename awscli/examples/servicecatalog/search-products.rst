**To get information about the products to which the caller has access*

The following ``search-products `` example gets all the products the caller has access to. ::

    aws servicecatalog search-products

Output::

    {
        "ProductViewSummaries": [
            {
                "Id": "prodview-5uksdh4xxxxxx",
                "ProductId": "prod-j6fu3hxxxxxxxx",
                "Name": "TestSC",
                "Owner": "test",
                "ShortDescription": "",
                "Type": "CLOUD_FORMATION_TEMPLATE",
                "Distributor": "",
                "HasDefaultPath": false,
                "SupportEmail": "",
                "SupportDescription": "",
                "SupportUrl": ""
            },
            {
                "Id": "prodview-3kfoaabxxxxxx",
                "ProductId": "prod-j6pd3xxxxxxxx",
                "Name": "TestProduct",
                "Owner": "test_owner",
                "ShortDescription": "",
                "Type": "CLOUD_FORMATION_TEMPLATE",
                "Distributor": "",
                "HasDefaultPath": false,
                "SupportEmail": "",
                "SupportDescription": "",
                "SupportUrl": ""
            }
        ]
    } 
