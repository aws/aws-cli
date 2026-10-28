**To delete an AWS Config rule**

The following ``delete-config-rule`` example deletes an AWS Config rule named ``MyConfigRule``. This command produces no output. ::

    aws configservice delete-config-rule \
        --config-rule-name MyConfigRule