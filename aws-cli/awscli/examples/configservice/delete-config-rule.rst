**To delete an AWS Config rule**

The following ``delete-config-rule`` example deletes an AWS Config rule named ``MyConfigRule``. ::

    aws configservice delete-config-rule \
        --config-rule-name MyConfigRule

This command produces no output.

For more information, see `Deleting AWS Config Rules <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_delete-rules.html>`__ in the *AWS Config Developer Guide*.
