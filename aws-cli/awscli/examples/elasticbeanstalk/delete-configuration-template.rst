**To delete a configuration template**

The following ``delete-configuration-template`` example deletes a configuration template named ``my-template`` for an application named ``my-app``. ::

    aws elasticbeanstalk delete-configuration-template \
        --template-name my-template \
        --application-name my-app

This command produces no output.

For more information, see `Using Elastic Beanstalk saved configurations <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-configuration-savedconfig.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
