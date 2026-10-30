**To manually delete evaluation results**

The following ``delete-evaluation-results`` example deletes the current evaluation results for the AWS managed rule s3-bucket-versioning-enabled. ::

    aws configservice delete-evaluation-results \
        --config-rule-name s3-bucket-versioning-enabled

This command produces no output.