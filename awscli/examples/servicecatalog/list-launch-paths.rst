**To list launch paths**

The following ``list-launch-paths`` example lists launch paths for a portfolio. ::

    aws servicecatalog list-launch-paths  \
        --product-id prod-cfrfxmraxxxxx

Output::

    {
        "LaunchPathSummaries": [
            {
                "Id": "lpv3-y3fnkeslpoevg",
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
