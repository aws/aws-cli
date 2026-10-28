**To restart application servers**

The following ``restart-app-server`` example restarts application servers on all instances in an environment named ``my-env``. This command produces no output. ::

    aws elasticbeanstalk restart-app-server \
        --environment-name my-env
