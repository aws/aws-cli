**To stop finding aggregation**

The following ``delete-finding-aggregator`` example stops finding aggregation. It is run from US East (Virginia), which is the aggregation Region. ::

    aws securityhub delete-finding-aggregator \
        --region us-west-2 \
        --finding-aggregator-arn arn:aws:securityhub:us-west-2:123456789012:finding-aggregator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Stopping finding aggregation <https://docs.aws.amazon.com/securityhub/latest/userguide/finding-aggregation-stop.html>`__ in the *AWS Security Hub User Guide*.