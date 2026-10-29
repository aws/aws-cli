**To delete an application version**

The following ``delete-application-version`` example deletes an application version named ``22a0-stage-150819_182129`` for an application named ``my-app``. ::

    aws elasticbeanstalk delete-application-version \
        --version-label 22a0-stage-150819_182129 \
        --application-name my-app

This command produces no output.

For more information, see `Managing application versions <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/applications-versions.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
