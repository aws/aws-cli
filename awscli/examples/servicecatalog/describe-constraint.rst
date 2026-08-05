**To describe a constraint**

The following ``describe-constraint`` example describes a constraint. ::

    aws servicecatalog describe-constraint \
        --id "cons-oqp52evr4bxxxx"   

Output::

    {
        "ConstraintDetail": {
            "ConstraintId": "cons-7tr6gei4bxxxx",
            "Type": "LAUNCH",
            "Owner": "123456789012",
            "ProductId": "prod-cfrfxmra3xxxx",
            "PortfolioId": "port-y3fnkeslpxxxx"
        },
        "ConstraintParameters": "{\"RoleArn\" : \"arn:aws:iam::123456789012:role/LaunchRole\"}",
        "Status": "AVAILABLE"
    }

For more information, see `Using AWS Service Catalog Constraints <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/constraints.html>`__ in the *AWS Service Catalog User Guide*.
