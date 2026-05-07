**To describe portfolio share status**

The following ``describe-portfolio-share-status`` example describes portfolio share status. ::

    aws servicecatalog describe-portfolio-share-status \
        --portfolio-share-token "share-agngcybu4xxxx"

Output::

    {
        "PortfolioShareToken": "share-agngcybu4xxxx",
        "PortfolioId": "port-y3fnkeslxxxxx",
        "OrganizationNodeValue": "123456789012",
        "Status": "COMPLETED",
        "ShareDetails": {
            "SuccessfulShares": [
                "012345678901"
            ],
            "ShareErrors": []
        }
    }

For more information, see `Sharing a Portfolio <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_sharing_how-to-share.html>`__ in the *AWS Service Catalog User Guide*.
