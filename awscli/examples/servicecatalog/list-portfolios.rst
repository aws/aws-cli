**To list portfolios**

The following ``list-portfolios`` example lists the Service Catalog portfolios in the current Region. ::

    aws servicecatalog list-portfolios

Output::

    {
        "PortfolioDetails": [
            {
                "CreatedTime": 1559665256.348,
                "ARN": "arn:aws:catalog:us-west-2:123456789012:portfolio/port-5pzcxmplst4ei",
                "DisplayName": "my-portfolio",
                "Id": "port-5pzcxmplst4ei",
                "ProviderName": "my-user"
            }
        ]
    }

For more information, see `Managing Portfolios <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios.html>`__ in the *AWS Service Catalog Administrator Guide*.
