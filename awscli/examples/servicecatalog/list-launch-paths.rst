**To list launch paths**

The following ``list-launch-paths`` example lists launch paths for a portfolio. ::

    aws servicecatalog list-launch-paths \
        --product-id prod-cfrfxmraxxxxx

Output::

    {
        "LaunchPathSummaries": [
            {
                "Id": "lpv3-y3fnkeslpxxxx",
                "ConstraintSummaries": [
                    {
                        "Type": "LAUNCH"
                    }
                ],
                "Tags": [],
                "Name": "TestPort"
            }
        ]
    }

For more information, see `Granting Access to Users <https://docs.aws.amazon.com/servicecatalog/latest/adminguide/catalogs_portfolios_users.html>`__ in the *AWS Service Catalog User Guide*.
