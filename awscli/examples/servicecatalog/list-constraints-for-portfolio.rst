**Example 1: To list all constraints for a portfolio**

The following ``list-constraints-for-portfolio`` example lists all constraints for a portfolio. ::

    aws servicecatalog list-constraints-for-portfolio \
        --portfolio-id port-y3fnkeslpoevg

Output::

    {
        "ConstraintDetails": [
            {
                "ConstraintId": "cons-dgdyqdqrxx4bq",
                "Type": "LAUNCH",
                "Description": "Launch as local role TestLaunchRole",
                "Owner": "123456789012",
                "ProductId": "prod-j6pd3hf6xxxxx",
                "PortfolioId": "port-y3fnkeslxxxxx"
            },
            {
                "ConstraintId": "cons-tzxjnj4l6yvck",
                "Type": "RESOURCE_UPDATE",
                "Owner": "123456789012",
                "ProductId": "prod-sphewkokxxxxx",
                "PortfolioId": "port-y3fnkeslxxxxx"
            }
        ]
    }


**Example 2: To list constraints on a product**

The following ``list-constraints-for-portfolio`` example lists constraints on a product. ::

    aws servicecatalog list-constraints-for-portfolio \
        --portfolio-id port-y3fnkeslxxxxx \
        --product-id prod-j6pd3hf6xxxxx

Output::

    {
        "ConstraintDetails": [
            {
                "ConstraintId": "cons-dgdyqdqrxx4bq",
                "Type": "LAUNCH",
                "Description": "Launch as local role TestLaunchRole",
                "Owner": "123456789012",
                "ProductId": "prod-j6pd3hf6xxxxx",
                "PortfolioId": "port-y3fnkeslxxxxx"
            }
        ]
    }
