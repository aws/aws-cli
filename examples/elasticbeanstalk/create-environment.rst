**To specify a JSON file to define environment configuration options**

The following ``create-environment`` command specifies that a JSON file with the name ``myoptions.json`` should be used to override values obtained from the solution stack or the configuration template::

  aws elasticbeanstalk create-environment --environment-name sample-env --application-name sampleapp --option-settings file://myoptions.json

For more information, see `Option Values`_ in the *AWS Elastic Beanstalk Developer Guide*.

.. _`Option Values`: http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html
