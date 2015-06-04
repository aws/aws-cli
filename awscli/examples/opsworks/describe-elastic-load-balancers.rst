**To describe a stack's elastic load balancers**

The following ``describe-elastic-load-balancers`` command describes a specified stack's load balancers.  ::

  aws opsworks --region us-west-1 describe-elastic-load-balancers --stack-id d72553d4-8727-448c-9b00-f024f0ba1b06

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: This particular stack has one app.

::

  {
    "Apps": [
      {
        "StackId": "38ee91e2-abdc-4208-a107-0b7168b3cc7a",
        "AppSource": {
          "Url": "https://s3-us-west-2.amazonaws.com/opsworks-tomcat/simplejsp.zip",
          "Type": "archive"
        },
        "Name": "SimpleJSP",
        "EnableSsl": false,
        "SslConfiguration": {},
        "AppId": "da1decc1-0dff-43ea-ad7c-bb667cd87c8b",
        "Attributes": {
          "RailsEnv": null,
          "AutoBundleOnDeploy": "true",
          "DocumentRoot": "ROOT"
        },
        "Shortname": "simplejsp",
        "Type": "other",
        "CreatedAt": "2013-08-01T21:46:54+00:00"
      }
    ]
  }

**More Information**

For more information, see Apps_ in the *AWS OpsWorks User Guide*.

.. _Apps: http://docs.aws.amazon.com/opsworks/latest/userguide/workingapps.html

