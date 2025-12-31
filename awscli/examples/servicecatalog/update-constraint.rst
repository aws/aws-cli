**To update a constraint**

The following ``update-constraint`` example updates a constraint. ::

    aws servicecatalog update-constraint  \
        --id cons-dgdyqdqrxx4bq \
        --parameters '{"LocalRoleName": "TestLaunchRole"}'

Output::

    {
        "ConstraintDetail": {
            "ConstraintId": "cons-dgdyqdqrxx4bq",
            "Type": "LAUNCH",
            "Description": "Launch as local role TestLaunchRole",
            "Owner": "123456789012",
            "ProductId": "prod-j6pd3hf6xxxxx",
            "PortfolioId": "port-y3fnkeslxxxxx"
        },
        "ConstraintParameters": "{\"LocalRoleName\": \"TestLaunchRole\"}",
        "Status": "CREATING"
    }
