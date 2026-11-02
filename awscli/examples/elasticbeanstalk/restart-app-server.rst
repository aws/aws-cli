**To restart application servers**

The following ``restart-app-server`` example restarts application servers on all instances in an environment named ``my-env``. ::

    aws elasticbeanstalk restart-app-server \
        --environment-name my-env

This command produces no output.

For more information, see `Environment actions <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-dashboard-actions.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
