**To create a constraint**

The following ``create-constraint`` example creates a constraint. ::

    aws servicecatalog create-constraint  \
        --portfolio-id port-y3fnkesxxxxx \
        --product-id prod-cfrfxmraxxxxx \
        --type LAUNCH \
        --parameters '{"RoleArn" : "arn:aws:iam::123456789012:role/NewLaunchRole"}'   

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
        "Status": "CREATING"
    }