**To describe portfolio share status**

The following ``describe-portfolio-share-status`` example describes portfolio share status. ::

    aws servicecatalog describe-portfolio-share-status  \
        --portfolio-share-token "share-agngcybu4uufe"

Output::

    {
        "PortfolioShareToken": "share-agngcybu4uufe",
        "PortfolioId": "port-y3fnkeslxxxxx",
        "OrganizationNodeValue": "123456789012",
        "Status": "COMPLETED",
        "ShareDetails": {
            "SuccessfulShares": [
                "210987654321"
            ],
            "ShareErrors": []
        }
    }
