**To change an application's description**

The following ``update-application`` example updates the description of an application named ``my-app``. ::

    aws elasticbeanstalk update-application \
        --application-name my-app \
        --description "my Elastic Beanstalk application"

Output::

    {
        "Application": {
            "ApplicationName": "my-app",
            "Description": "my Elastic Beanstalk application",
            "Versions": [
                "2fba-stage-150819_234450",
                "bf07-stage-150820_214945",
                "93f8",
                "fd7c-stage-150820_000431",
                "22a0-stage-150819_185942"
            ],
            "DateCreated": "2015-08-13T19:15:50.449Z",
            "ConfigurationTemplates": [],
            "DateUpdated": "2015-08-20T22:34:56.195Z"
        }
    }

For more information, see `Managing Elastic Beanstalk applications <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/applications.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
