**To delete the retention policy of a log group**

The following ``delete-retention-policy`` example removes the retention policy that has previously been applied to a log group named ``my-logs``. ::

    aws logs delete-retention-policy \
        --log-group-name my-logs
