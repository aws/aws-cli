**To update a constraint**

The following ``update-constraint`` example updates a constraint. ::

    aws servicecatalog update-constraint \
        --id cons-dgdyqdqrxxxxx \
        --parameters '{"LocalRoleName": "TestLaunchRole"}'

Output::

    {
        "ConstraintDetail": {
            "ConstraintId": "cons-dgdyqdqrxxxxx",
            "Type": "LAUNCH",
            "Description": "Launch as local role TestLaunchRole",
            "Owner": "123456789012",
            "ProductId": "prod-j6pd3hf6xxxxx",
            "PortfolioId": "port-y3fnkeslxxxxx"
        },
        "ConstraintParameters": "{\"LocalRoleName\": \"TestLaunchRole\"}",
        "Status": "CREATING"
    }

For more information, see `Using AWS Service Catalog Constraints <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/constraints.html>`__ in the *AWS Service Catalog User Guide*.
