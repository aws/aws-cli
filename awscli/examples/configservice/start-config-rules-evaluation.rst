**To run an on-demand evaluation for AWS Config rules**

The following ``start-config-rules-evaluation`` example starts an evaluation for two AWS managed rules. This command produces no output. ::

    aws configservice start-config-rules-evaluation \
        --config-rule-names s3-bucket-versioning-enabled cloudtrail-enabled