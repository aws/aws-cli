**To update a configuration template**

The following ``update-configuration-template`` example removes the configured CloudWatch custom health metrics configuration ``ConfigDocument`` from a saved configuration template named ``my-template``. ::

    aws elasticbeanstalk update-configuration-template \
        --template-name my-template \
        --application-name my-app \
        --options-to-remove Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=ConfigDocument

Output::

    {
        "ApplicationName": "my-app",
        "TemplateName": "my-template",
        "DateCreated": "2015-08-20T22:39:31Z",
        "DateUpdated": "2015-08-20T22:43:11Z",
        "SolutionStackName": "64bit Amazon Linux 2015.03 v2.0.0 running Tomcat 8 Java 8"
    }

For more information about namespaces and supported options, see `Configuration options <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
