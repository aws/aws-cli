**To disassociate a principal from a portfolio**

The following ``disassociate-principal-from-portfolio`` example disassociates the specified principal from the portfolio. ::

    aws servicecatalog disassociate-principal-from-portfolio \
        --portfolio-id port-2s6abcdq5wdh4 \
        --principal-arn arn:aws:iam::123456789012:group/myendusers

This command produces no output.

For more information, see `Granting Access to Users <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_users.html>`__ in the *AWS Service Catalog Administrator Guide*.
