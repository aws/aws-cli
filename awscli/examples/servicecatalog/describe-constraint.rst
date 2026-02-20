**To describe a constraint**

The following ``describe-constraint`` example describes a constraint. ::

    aws servicecatalog describe-constraint  \
        --id "cons-oqp52evr4bfx2g"   

Output::

    {
        "ConstraintDetail": {
            "ConstraintId": "cons-7tr6gei4bfx2g",
            "Type": "LAUNCH",
            "Owner": "123456789012",
            "ProductId": "prod-cfrfxmra3vnu4",
            "PortfolioId": "port-y3fnkeslpoevg"
        },
        "ConstraintParameters": "{\"RoleArn\" : \"arn:aws:iam::123456789012:role/LaunchRole\"}",
        "Status": "AVAILABLE"
    }