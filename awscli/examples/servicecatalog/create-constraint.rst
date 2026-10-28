**To create a constraints**

The following ``create-constraint`` example creates a constraint. ::

    aws servicecatalog create-constraint \
        --portfolio-id port-y3fnkesxxxxx \
        --product-id prod-cfrfxmraxxxxx \
        --type LAUNCH \
        --parameters '{"RoleArn" : "arn:aws:iam::123456789012:role/LaunchRole"}'   

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
        "Status": "CREATING"
    }

For more information, see `Using AWS Service Catalog Constraints <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/constraints.html>`__ in the *AWS Service Catalog User Guide*.
