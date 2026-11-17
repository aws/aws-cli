**To list accounts with access to a portfolio**

The following ``list-portfolio-access`` example lists the AWS accounts that have access to the specified portfolio. ::

    aws servicecatalog list-portfolio-access \
        --portfolio-id port-2s6abcdq5wdh4

Output::

    {
        "AccountIds": [
            "123456789012"
        ]
    }

For more information, see `Sharing a Portfolio <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_sharing_how-to-share.html>`__ in the *AWS Service Catalog Administrator Guide*.
