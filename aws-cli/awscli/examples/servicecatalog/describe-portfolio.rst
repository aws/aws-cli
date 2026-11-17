**To describe a portfolio**

The following ``describe-portfolio`` example displays details for the specified portfolio. ::

    aws servicecatalog describe-portfolio \
        --id port-2s6abcdq5wdh4

Output::

    {
        "TagOptions": [],
        "PortfolioDetail": {
            "ARN": "arn:aws:catalog:us-west-2:123456789012:portfolio/port-2s6abcdq5wdh4",
            "Id": "port-2s6wuzyq5wdh4",
            "CreatedTime": 1571337221.555,
            "DisplayName": "my-portfolio",
            "ProviderName": "my-provider"
        },
        "Tags": []
    }

For more information, see `Managing Portfolios <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios.html>`__ in the *AWS Service Catalog Administrator Guide*.
