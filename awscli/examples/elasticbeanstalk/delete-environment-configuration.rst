**To delete a draft configuration**

The following ``delete-environment-configuration`` example deletes a draft configuration for an environment named ``my-env``. ::

    aws elasticbeanstalk delete-environment-configuration \
        --environment-name my-env \
        --application-name my-app

This command produces no output.
