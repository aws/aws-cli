**To create a portfolio**

The following ``create-portfolio`` example creates a portfolio. ::

    aws servicecatalog create-portfolio  \
        --provider-name my-provider \
        --display-name my-portfolio

Output::

    {
        "PortfolioDetail": {
            "ProviderName": "my-provider",
            "DisplayName": "my-portfolio",
            "CreatedTime": 1571337221.555,
            "ARN": "arn:aws:catalog:us-west-2:123456789012:portfolio/port-2s6xmplq5wdh4",
            "Id": "port-2s6xmplq5wdh4"
        }
    }

For more information, see `Creating and Deleting Portfolios <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/portfoliomgmt-create.html>`__ in the *AWS Service Catalog Administrator Guide*.
