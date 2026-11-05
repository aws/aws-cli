**To retrieve the current finding aggregation configuration**

The following ``get-finding-aggregator`` example retrieves the current finding aggregation configuration. ::

    aws securityhub get-finding-aggregator \
        --finding-aggregator-arn arn:aws:securityhub:us-east-1:123456789012:finding-aggregator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "FindingAggregatorArn": "arn:aws:securityhub:us-east-1:123456789012:finding-aggregator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "FindingAggregationRegion": "us-east-1",
        "RegionLinkingMode": "SPECIFIED_REGIONS",
        "Regions": [
            "us-west-1",
            "us-west-2"
        ]
    }

For more information, see `Viewing the current finding aggregation configuration <https://docs.aws.amazon.com/securityhub/latest/userguide/finding-aggregation-view-config.html>`__ in the *AWS Security Hub User Guide*.