**To delete a CloudWatch Events rule**

The following ``delete-rule`` example deletes the rule named ``EC2InstanceStateChanges``. ::

    aws events delete-rule \
        --name "EC2InstanceStateChanges"

This command produces no output.

For more information, see `Disabling or deleting a rule in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-delete-rule.html>`__ in the *Amazon EventBridge User Guide*.
