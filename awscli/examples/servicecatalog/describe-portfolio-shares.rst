**To describe portfolio shares**

The following ``describe-portfolio-shares`` example describes portfolio shares. ::

    aws servicecatalog describe-portfolio-shares  \
        --portfolio-id port-y3fnkeslxxxxx \
        --type ACCOUNT

Output::

    {
        "PortfolioShareDetails": [
            {
                "PrincipalId": "012345678901",
                "Type": "ACCOUNT",
                "Accepted": true,
                "ShareTagOptions": false,
                "SharePrincipals": false
            },
            {
                "PrincipalId": "098765432109",
                "Type": "ACCOUNT",
                "Accepted": false,
                "ShareTagOptions": false,
                "SharePrincipals": false
            }
        ]
    }
