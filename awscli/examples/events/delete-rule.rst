**To delete a CloudWatch Events rule**

The following ``delete-rule`` example deletes the rule named ``EC2InstanceStateChanges``. This command produces no output. ::

    aws events delete-rule \
        --name "EC2InstanceStateChanges"
