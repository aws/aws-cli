**To swap environment CNAMES**

The following ``swap-environment-cnames`` example swaps the assigned subdomains of two environments. ::

    aws elasticbeanstalk swap-environment-cnames \
        --source-environment-name my-env-blue \
        --destination-environment-name my-env-green

This command produces no output.

For more information, see `Blue/Green deployments with Elastic Beanstalk <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.CNAMESwap.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
