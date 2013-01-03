aws-cli
=======

This package provides a unified command line interface to many
Amazon Web Services.

The currently supported services include:

* Amazon Elastic Compute Cloud (Amazon EC2) including VPC
* Elastic Load Balancing
* Auto Scaling
* AWS CloudFormation
* AWS Elastic Beanstalk
* Amazon Simple Notification Service (Amazon SNS)
* Amazon Simple Queue Service (Amazon SQS)
* Amazon Relational Database Service (Amazon RDS)
* AWS Identity and Access Management (IAM)
* AWS Security Token Service (STS)
* Amazon CloudWatch
* Amazon Simple Email Service (Amazon SES)

The aws-cli package should work on Python versions 2.6.x - 3.3.x.

Installation
------------
The easiest way to install aws-cli is to use ``easy_install`` or ``pip``.

    $ easy_install awscli

or, if you are not installing in a ``virtualenv``:

    $ sudo easy_install awscli

Using ``pip``, it would simply be:

    $ pip install awscli

or:

    $ sudo pip install awscli

This will install the aws-cli package as well as all dependencies.  You can
also just clone the git repo or download the tarball.  Once you have the
awscli directory structure on your workstation, you can just:

    $ cd <path_to_awscli>
    $ python setup.py install

Command Completion
------------------
The aws-cli package includes a very useful command completion feature.
This feature is not automatically installed so you need to configure it manually.
To enable tab completion for bash use the built-in command ``complete``.

    $ complete -C aws_completer aws

For tcsh:

    $ complete aws 'p/*/`aws_completer`/'

You should add this to your startup scripts to enable it for future sessions.

Getting Started
---------------
Before using aws-cli, you need to tell it about your AWS credentials.  You
can do this in several ways:

* Environment variables
* Config file
* IAM Role

To use environment variables, do the following:

    $ export AWS_ACCESS_KEY_ID=<access_key>
    $ export AWS_SECRET_ACCESS_KEY=<secret_key>

To use a config file, create a configuration file like this:

    [default]
    aws_access_key_id=<default access key>
    aws_secret_access_key=<default secret key>
    region=us-west-1  # optional, to define default region for this profile

    [testing]
    aws_access_key_id=<testing access key>
    aws_secret_access_key=<testing secret key>
    region=us-west-2

As you can see, you can have multiple ``profiles`` defined in this
configuration file and specify which profile to use by using the
``--profile`` option.  If no profile is specified the ``default``
profile is used.  Once you have created the config file, you need to
tell aws-cli where to find it.  Do this by setting the appropriate
environment variable.

    $ export AWS_CONFIG_FILE=/path/to/config_file

The final option for credentials is highly recommended if you are
using aws-cli on an EC2 instance.  IAM Roles are
a great way to have credentials installed automatically on your
instance.  If you are using IAM Roles, aws-cli will find them and use
them automatically.

Other Important Environment Variables
-------------------------------------
The following additional environment variables can be useful in
configuring and customizing your environment.

AWS_DEFAULT_REGION can be used to specify a default region to use
if one is not provided explicitly on the command line with the
``--region`` option or in a config file.

    $ export AWS_DEFAULT_REGION=us-west-2

AWS_DEFAULT_PROFILE can be used to specify which profile to use
if one is not explicitly specified on the command line via the
``--profile`` option.

    $ export AWS_DEFAULT_PROFILE=testing

Complex Parameter Input
-----------------------
Many options that need to be provided are simple string or numeric
values.  However, some operations require complex data structures
as input parameters.  These options must be provided as JSON data
structures, either on the command line or in files.

For example, consider the command to authorize access to an EC2
security group.  In this case, we will add ingress access to port 22
for all IP addresses.

    $ aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --ip-permissions '{"from_port":22,"to_port":22,"ip_protocol":"tcp","ip_ranges":["0.0.0.0/0"]}'

You could also place the JSON in a file, called port22.json for example,
and use this:

    $ aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --ip-permissions /path/to/port22.json

Command Output
==============

The default output for commands is currently JSON.  This may change in the
future but for now it provides the most complete output.  You may find the
[jq](http://stedolan.github.com/jq/) tool useful in processing the JSON
output for other uses.
