**To view events for an environment**

The following ``describe-events`` example retrieves events for an environment named ``my-env``. ::

    aws elasticbeanstalk describe-events \
        --environment-name my-env

Output::

    {
        "Events": [
            {
                "ApplicationName": "my-app",
                "EnvironmentName": "my-env",
                "Message": "Environment health has transitioned from Info to Ok.",
                "EventDate": "2015-08-20T07:06:53.535Z",
                "Severity": "INFO"
            },
            {
                "ApplicationName": "my-app",
                "EnvironmentName": "my-env",
                "Severity": "INFO",
                "RequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Message": "Environment update completed successfully.",
                "EventDate": "2015-08-20T07:06:02.049Z"
            },
            {
                "ApplicationName": "my-app",
                "EnvironmentName": "my-env",
                "Severity": "INFO",
                "RequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Message": "Using elasticbeanstalk-us-west-2-123456789012 as Amazon S3 storage bucket for environment data.",
                "EventDate": "2015-08-13T19:16:27.561Z"
            },
            {
                "ApplicationName": "my-app",
                "EnvironmentName": "my-env",
                "Severity": "INFO",
                "RequestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Message": "createEnvironment is starting.",
                "EventDate": "2015-08-13T19:16:26.581Z"
            }
        ]
    }

For more information, see `Viewing an Elastic Beanstalk environment's event stream <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.events.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
