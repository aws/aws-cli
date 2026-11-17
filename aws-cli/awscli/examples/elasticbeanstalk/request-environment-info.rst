**To request tailed logs**

The following ``request-environment-info`` example requests logs from an environment named ``my-env``. ::

    aws elasticbeanstalk request-environment-info \
        --environment-name my-env \
        --info-type tail

This command produces no output.

After requesting logs, retrieve their location with `retrieve-environment-info <https://docs.aws.amazon.com/cli/latest/reference/elasticbeanstalk/retrieve-environment-info.html>`__.

For more information, see `Viewing logs from Amazon EC2 instances in your Elastic Beanstalk environment <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.logging.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
