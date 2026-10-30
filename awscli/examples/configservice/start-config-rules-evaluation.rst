**To run an on-demand evaluation for AWS Config rules**

The following ``start-config-rules-evaluation`` example starts an evaluation for two AWS managed rules. ::

    aws configservice start-config-rules-evaluation \
        --config-rule-names s3-bucket-versioning-enabled cloudtrail-enabled

This command produces no output.

For more information, see `Evaluating Your Resources with AWS Config Rules <https://docs.aws.amazon.com/config/latest/developerguide/evaluating-your-resources.html>`__ in the *AWS Config Developer Guide*.
