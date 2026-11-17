**To update a portfolio**

The following ``update-portfolio`` example updates the name of the specified portfolio. ::

    aws servicecatalog update-portfolio \
        --id port-5abcd3e5st4ei \
        --display-name "New portfolio name"

Output::

    {
        "PortfolioDetail": {
            "DisplayName": "New portfolio name",
            "ProviderName": "provider",
            "ARN": "arn:aws:catalog:us-west-2:123456789012:portfolio/port-5abcd3e5st4ei",
            "Id": "port-5abcd3e5st4ei",
            "CreatedTime": 1559665256.348
        },
        "Tags": []
    }

For more information, see `Managing Portfolios <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios.html>`__ in the *AWS Service Catalog Administrator Guide*.
