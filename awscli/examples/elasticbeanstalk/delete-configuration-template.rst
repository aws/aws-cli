**To delete a configuration template**

The following ``delete-configuration-template`` example deletes a configuration template named ``my-template`` for an application named ``my-app``. This command produces no output. ::

    aws elasticbeanstalk delete-configuration-template \
        --template-name my-template \
        --application-name my-app
