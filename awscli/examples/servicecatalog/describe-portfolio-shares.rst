**To describe portfolio shares**

The following ``describe-portfolio-shares`` example describes portfolio shares. ::

    aws servicecatalog describe-portfolio-shares \
        --portfolio-id port-y3fnkeslxxxxx \
        --type ACCOUNT

Output::

    {
        "PortfolioShareDetails": [
            {
                "PrincipalId": "123456789012",
                "Type": "ACCOUNT",
                "Accepted": true,
                "ShareTagOptions": false,
                "SharePrincipals": false
            },
            {
                "PrincipalId": "123456789012",
                "Type": "ACCOUNT",
                "Accepted": false,
                "ShareTagOptions": false,
                "SharePrincipals": false
            }
        ]
    }

For more information, see `Sharing a Portfolio <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_sharing_how-to-share.html>`__ in the *AWS Service Catalog User Guide*.
