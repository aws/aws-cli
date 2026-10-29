**To view configuration options for an environment**

The following ``describe-configuration-options`` example retrieves descriptions of all available configuration options for an environment named ``my-env``. ::

    aws elasticbeanstalk describe-configuration-options \
        --environment-name my-env \
        --application-name my-app

Output::

    {
        "Options": [
            {
                "Name": "JVMOptions",
                "UserDefined": false,
                "DefaultValue": "Xms=256m,Xmx=256m,XX:MaxPermSize=64m,JVM Options=",
                "ChangeSeverity": "RestartApplicationServer",
                "Namespace": "aws:cloudformation:template:parameter",
                "ValueType": "KeyValueList"
            },
            {
                "Name": "Interval",
                "UserDefined": false,
                "DefaultValue": "30",
                "ChangeSeverity": "NoInterruption",
                "Namespace": "aws:elb:healthcheck",
                "MaxValue": 300,
                "MinValue": 5,
                "ValueType": "Scalar"
            },
            {
                "Name": "LowerThreshold",
                "UserDefined": false,
                "DefaultValue": "2000000",
                "ChangeSeverity": "NoInterruption",
                "Namespace": "aws:autoscaling:trigger",
                "MinValue": 0,
                "ValueType": "Scalar"
            },
            {
                "Name": "ListenerEnabled",
                "UserDefined": false,
                "DefaultValue": "true",
                "ChangeSeverity": "Unknown",
                "Namespace": "aws:elb:listener",
                "ValueType": "Boolean"
            }
        ]
    }

Available configuration options vary per platform and configuration version. For more information about namespaces and supported options, see `Configuration options <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
