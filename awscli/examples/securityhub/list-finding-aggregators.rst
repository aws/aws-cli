**To list the available widgets**

The following ``list-finding-aggregators`` example returns the ARN of the finding aggregation configuration. ::

    aws securityhub list-finding-aggregators

Output::

    {
        "FindingAggregators": [
            {
                "FindingAggregatorArn": "arn:aws:securityhub:us-west-2:123456789012:finding-aggregator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Viewing the current finding aggregation configuration <https://docs.aws.amazon.com/securityhub/latest/userguide/finding-aggregation-view-config.html>`__ in the *AWS Security Hub User Guide*.