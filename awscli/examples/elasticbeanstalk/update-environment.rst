**To update an environment to a new version**

The following command updates an environment named "MyAppEnv" to version "v2" of the application it belongs to::

  aws elasticbeanstalk update-environment --environment-name MyAppEnv --version-label v2

This command requires that the "MyAppEnv" environment already exists and belongs to an application that has a valid application version with the label "v2".

Output::

  {
    "ApplicationName": "MyApp",
    "EnvironmentName": "MyApp",
    "VersionLabel": "v2",
    "Status": "Updating",
    "EnvironmentId": "e-szqipays4h",
    "EndpointURL": "awseb-e-i-AWSEBLoa-1RDLX6TC9VUAO-0123456789.us-west-2.elb.amazonaws.com",
    "SolutionStackName": "64bit Amazon Linux running Tomcat 7",
    "CNAME": "MyApp.elasticbeanstalk.com",
    "Health": "Grey",
    "Tier": {
        "Version": " ",
        "Type": "Standard",
        "Name": "WebServer"
    },
    "DateUpdated": "2015-02-03T23:12:29.119Z",
    "DateCreated": "2015-02-03T23:04:54.453Z"
  }

**To set an environment variable**

The following command sets the value of the "PARAM1" variable in the "MyAppEnv" environment to "ParamValue"::

  aws elasticbeanstalk update-environment --environment-name MyAppEnv --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=PARAM1,Value=ParamValue

The ``option-settings`` parameter takes a namespace in addition to the name and value of the variable. Elastic Beanstalk supports several namespaces for options in addition to environment variables.

For more information about namespaces and supported options, see `Option Values`_ in the *AWS Elastic Beanstalk Developer Guide*.

.. _`Option Values`: http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html
