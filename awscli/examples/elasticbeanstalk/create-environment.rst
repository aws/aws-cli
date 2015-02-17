**To create a new environment for an application**

The following command creates a new environment for version "v1" of a java application named "myApp"::

  $ aws elasticbeanstalk create-environment --application-name myApp --environment-name myAppEnv --cname-prefix myApp --version-label v1 --solution-stack-name "64bit Amazon Linux running Tomcat 7"

Output::

  {
    "ApplicationName": "myApp",
    "EnvironmentName": "myAppEnv",
    "VersionLabel": "v1",
    "Status": "Launching",
    "EnvironmentId": "e-izqpassy4h",
    "SolutionStackName": "64bit Amazon Linux running Tomcat 7",
    "CNAME": "myApp.elasticbeanstalk.com",
    "Health": "Grey",
    "Tier": {
        "Version": " ",
        "Type": "Standard",
        "Name": "WebServer"
    },
    "DateUpdated": "2015-02-03T23:04:54.479Z",
    "DateCreated": "2015-02-03T23:04:54.479Z"
  }

**To specify a JSON file to define environment configuration options**

The following ``create-environment`` command specifies that a JSON file with the name ``myoptions.json`` should be used to override values obtained from the solution stack or the configuration template::

  aws elasticbeanstalk create-environment --environment-name sample-env --application-name sampleapp --option-settings file://myoptions.json

For more information, see `Option Values`_ in the *AWS Elastic Beanstalk Developer Guide*.

.. _`Option Values`: http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html