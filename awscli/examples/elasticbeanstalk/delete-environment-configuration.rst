**To delete a draft configuration**

The following ``delete-environment-configuration`` example deletes a draft configuration for an environment named ``my-env``. ::

    aws elasticbeanstalk delete-environment-configuration \
        --environment-name my-env \
        --application-name my-app

This command produces no output.

For more information, see `Setting configuration options after environment creation <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-configuration-methods-after.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
