**To update the current finding aggregation configuration**

The following ``update-finding-aggregator`` example changes the finding aggregation configuration to link from selected Regions. It is run from US East (Virginia), which is the aggregation Region. It selects US West (N. California) and US West (Oregon) as the linked Regions. ::

    aws securityhub update-finding-aggregator \
        --region us-east-1 \
        --finding-aggregator-arn arn:aws:securityhub:us-east-1:123456789012:finding-aggregator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --region-linking-mode SPECIFIED_REGIONS \
        --regions us-west-1,us-west-2

This command produces no output.

For more information, see `Updating the finding aggregation configuration <https://docs.aws.amazon.com/securityhub/latest/userguide/finding-aggregation-update.html>`__ in the *AWS Security Hub User Guide*.