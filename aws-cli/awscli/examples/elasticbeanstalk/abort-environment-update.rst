**To abort a deployment**

The following ``abort-environment-update`` example aborts a running application version deployment for an environment named ``my-env``. ::

    aws elasticbeanstalk abort-environment-update \
        --environment-name my-env

This command produces no output.

For more information, see `Deploying applications to Elastic Beanstalk environments <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.deploy-existing-version.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
