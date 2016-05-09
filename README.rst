=======
aws-cli
=======

.. image:: https://travis-ci.org/aws/aws-cli.svg?branch=develop
   :target: https://travis-ci.org/aws/aws-cli
   :alt: Build Status


This package provides a unified command line interface to Amazon Web Services.

The aws-cli package works on Python versions:

* 2.6.5 and greater
* 2.7.x and greater
* 3.3.x and greater
* 3.4.x and greater
* 3.5.x and greater

.. attention::
   We recommend that all customers regularly monitor the
   `Amazon Web Services Security Bulletins website`_ for any important security bulletins related to
   aws-cli.


------------
Installation
------------

The easiest way to install aws-cli is to use `pip`_::

    $ pip install awscli

or, if you are not installing in a ``virtualenv``::

    $ sudo pip install awscli

If you have the aws-cli installed and want to upgrade to the latest version
you can run::

    $ pip install --upgrade awscli

.. note::

    On OS X, if you see an error regarding the version of six that came with
    distutils in El Capitan, use the ``--ignore-installed option``::

        $ sudo pip install awscli --ignore-installed six


This will install the aws-cli package as well as all dependencies.  You can
also just `download the tarball`_.  Once you have the
awscli directory structure on your workstation, you can just run::

    $ cd <path_to_awscli>
    $ python setup.py install

If you want to run the ``develop`` branch of the CLI, see the
"CLI Dev Version" section below.


------------
CLI Releases
------------

The release notes for the AWS CLI can be found `here <http://aws.amazon.com/releasenotes/CLI>`__.
You can also find a `CHANGELOG <https://github.com/aws/aws-cli/blob/develop/CHANGELOG.rst>`__
in the github repo.


------------------
Command Completion
------------------

The aws-cli package includes a very useful command completion feature.
This feature is not automatically installed so you need to configure it manually.
To enable tab completion for bash either use the built-in command ``complete``::

    $ complete -C aws_completer aws

Or add ``bin/aws_bash_completer`` file under ``/etc/bash_completion.d``,
``/usr/local/etc/bash_completion.d`` or any other ``bash_completion.d`` location.

For tcsh::

    $ complete aws 'p/*/`aws_completer`/'

You should add this to your startup scripts to enable it for future sessions.

For zsh please refer to bin/aws_zsh_completer.sh.  Source that file, e.g.
from your `~/.zshrc`, and make sure you run `compinit` before::

    $ source bin/aws_zsh_completer.sh

For now the bash compatibility auto completion (bashcompinit) is used.
For further details please refer to the top of bin/aws_zsh_completer.sh.

---------------
Getting Started
---------------

Before using aws-cli, you need to tell it about your AWS credentials.  You
can do this in several ways:

* Environment variables
* Shared credentials file
* Config file
* IAM Role

The quickest way to get started is to run the ``aws configure`` command::

    $ aws configure
    AWS Access Key ID: foo
    AWS Secret Access Key: bar
    Default region name [us-west-2]: us-west-2
    Default output format [None]: json

To use environment variables, do the following::

    $ export AWS_ACCESS_KEY_ID=<access_key>
    $ export AWS_SECRET_ACCESS_KEY=<secret_key>

To use the shared credentials file, create an INI formatted file like this::

    [default]
    aws_access_key_id=foo
    aws_secret_access_key=bar

    [testing]
    aws_access_key_id=foo
    aws_secret_access_key=bar

and place it in ``~/.aws/credentials`` (or in
``%UserProfile%\.aws/credentials`` on Windows). If you wish to place the
shared credentials file in a different location than the one specified above,
you need to tell aws-cli where to find it.  Do this by setting
the appropriate environment variable::

    $ export AWS_SHARED_CREDENTIALS_FILE=/path/to/shared_credentials_file

To use a config file, create a configuration file like this::

    [default]
    aws_access_key_id=<default access key>
    aws_secret_access_key=<default secret key>
    # Optional, to define default region for this profile.
    region=us-west-1

    [profile testing]
    aws_access_key_id=<testing access key>
    aws_secret_access_key=<testing secret key>
    region=us-west-2

and place it in ``~/.aws/config`` (or in ``%UserProfile%\.aws\config`` on Windows). If you wish to place the config file in a different location than the one
specified above, you need to tell aws-cli where to find it.  Do this by setting
the appropriate environment variable::

    $ export AWS_CONFIG_FILE=/path/to/config_file

As you can see, you can have multiple ``profiles`` defined in both the shared
credentials file and the  configuration file. You can then specify which
profile to use by using the ``--profile`` option. If no profile is specified
the ``default`` profile is used.

In the config file, except for the default profile, you
**must** prefix each config section of a profile group with ``profile``.
For example, if you have a profile named "testing" the section header would
be ``[profile testing]``.

The final option for credentials is highly recommended if you are
using aws-cli on an EC2 instance.  IAM Roles are
a great way to have credentials installed automatically on your
instance.  If you are using IAM Roles, aws-cli will find them and use
them automatically.

----------------------------
Other Configurable Variables
----------------------------

In addition to credentials, a number of other variables can be
configured either with environment variables, configuration file
entries or both.  The following table documents these.

=========== =========== ===================== ===================== ============================
Variable    Option      Config Entry          Environment Variable  Description
=========== =========== ===================== ===================== ============================
profile     --profile   profile               AWS_DEFAULT_PROFILE   Default profile name
----------- ----------- --------------------- --------------------- ----------------------------
region      --region    region                AWS_DEFAULT_REGION    Default AWS Region
----------- ----------- --------------------- --------------------- ----------------------------
config_file                                   AWS_CONFIG_FILE       Alternate location of config
----------- ----------- --------------------- --------------------- ----------------------------
output      --output    output                AWS_DEFAULT_OUTPUT    Default output style
----------- ----------- --------------------- --------------------- ----------------------------
ca_bundle   --ca-bundle ca_bundle             AWS_CA_BUNDLE         CA Certificate Bundle
----------- ----------- --------------------- --------------------- ----------------------------
access_key              aws_access_key_id     AWS_ACCESS_KEY_ID     AWS Access Key
----------- ----------- --------------------- --------------------- ----------------------------
secret_key              aws_secret_access_key AWS_SECRET_ACCESS_KEY AWS Secret Key
----------- ----------- --------------------- --------------------- ----------------------------
token                   aws_session_token     AWS_SESSION_TOKEN     AWS Token (temp credentials)
=========== =========== ===================== ===================== ============================

^^^^^^^^
Examples
^^^^^^^^

If you get tired of specifying a ``--region`` option on the command line
all of the time, you can specify a default region to use whenever no
explicit ``--region`` option is included using the ``region`` variable.
To specify this using an environment variable::

    $ export AWS_DEFAULT_REGION=us-west-2

To include it in your config file::

    [default]
    aws_access_key_id=<default access key>
    aws_secret_access_key=<default secret key>
    region=us-west-1

Similarly, the ``profile`` variable can be used to specify which profile to use
if one is not explicitly specified on the command line via the
``--profile`` option.  To set this via environment variable::

    $ export AWS_DEFAULT_PROFILE=testing

The ``profile`` variable can not be specified in the configuration file
since it would have to be associated with a profile and would defeat the
purpose.

^^^^^^^^^^^^^^^^^^^
Further Information
^^^^^^^^^^^^^^^^^^^

For more information about configuration options, please refer the
`AWS CLI Configuration Variables topic <http://docs.aws.amazon.com/cli/latest/topic/config-vars.html#cli-aws-help-config-vars>`_. You can access this topic
from the CLI as well by running ``aws help config-vars``.


----------------------------------------
Accessing Services With Global Endpoints
----------------------------------------

Some services, such as AWS Identity and Access Management (IAM)
have a single, global endpoint rather than different endpoints for
each region.

To make access to these services simpler, aws-cli will automatically
use the global endpoint unless you explicitly supply a region (using
the ``--region`` option) or a profile (using the ``--profile`` option).
Therefore, the following::

    $ aws iam list-users

Will automatically use the global endpoint for the IAM service
regardless of the value of the ``AWS_DEFAULT_REGION`` environment
variable or the ``region`` variable specified in your profile.

--------------------
JSON Parameter Input
--------------------

Many options that need to be provided are simple string or numeric
values.  However, some operations require JSON data structures
as input parameters either on the command line or in files.

For example, consider the command to authorize access to an EC2
security group.  In this case, we will add ingress access to port 22
for all IP addresses::

    $ aws ec2 authorize-security-group-ingress --group-name MySecurityGroup \
      --ip-permissions '{"FromPort":22,"ToPort":22,"IpProtocol":"tcp","IpRanges":[{"CidrIp": "0.0.0.0/0"}]}'

--------------------------
File-based Parameter Input
--------------------------

Some parameter values are so large or so complex that it would be easier
to place the parameter value in a file and refer to that file rather than
entering the value directly on the command line.

Let's use the ``authorize-security-group-ingress`` command shown above.
Rather than provide the value of the ``--ip-permissions`` parameter directly
in the command, you could first store the values in a file.  Let's call
the file ip_perms.json::

    {"FromPort":22,
     "ToPort":22,
     "IpProtocol":"tcp",
     "IpRanges":[{"CidrIp":"0.0.0.0/0"}]}

Then, we could make the same call as above like this::

    $ aws ec2 authorize-security-group-ingress --group-name MySecurityGroup \
        --ip-permissions file://ip_perms.json

The ``file://`` prefix on the parameter value signals that the parameter value
is actually a reference to a file that contains the actual parameter value.
aws-cli will open the file, read the value and pass use that value as the
parameter value.

This is also useful when the parameter is really referring to file-based
data.  For example, the ``--user-data`` option of the ``aws ec2 run-instances``
command or the ``--public-key-material`` parameter of the
``aws ec2 import-key-pair`` command.

-------------------------
URI-based Parameter Input
-------------------------

Similar to the file-based input described above, aws-cli also includes a
way to use data from a URI as the value of a parameter.  The idea is exactly
the same except the prefix used is ``https://`` or ``http://``::

    $ aws ec2 authorize-security-group-ingress --group-name MySecurityGroup \
        --ip-permissions http://mybucket.s3.amazonaws.com/ip_perms.json

--------------
Command Output
--------------

The default output for commands is currently JSON.  You can use the
``--query`` option to extract the output elements from this JSON document.
For more information on the expression language used for the ``--query``
argument, you can read the
`JMESPath Tutorial <http://jmespath.org/tutorial.html>`__.

^^^^^^^^
Examples
^^^^^^^^

Get a list of IAM user names::

    $ aws iam list-users --query Users[].UserName

Get a list of key names and their sizes in an S3 bucket::

    $ aws s3api list-objects --bucket b --query Contents[].[Key,Size]

Get a list of all EC2 instances and include their Instance ID, State Name,
and their Name (if they've been tagged with a Name)::

    $ aws ec2 describe-instances --query \
      'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`] | [0].Value]'


You may also find the `jq <http://stedolan.github.com/jq/>`_ tool useful in
processing the JSON output for other uses.

There is also an ASCII table format available.  You can select this style with
the ``--output table`` option or you can make this style your default output
style via environment variable or config file entry as described above.
Try adding ``--output table`` to the above commands.


---------------
CLI Dev Version
---------------

If you are just interested in using the latest released version of the AWS CLI,
please see the "Installation" section above.  This section is for anyone that
wants to install the development version of the CLI.  You normally would not
need to do this unless:

* You are developing a feature for the CLI and plan on submitting a Pull
  Request.
* You want to test the latest changes of the CLI before they make it into an
  official release.

The latest changes to the CLI are in the ``develop`` branch on github.  This is
the default branch when you clone the git repository.

Additionally, there are several other packages that are developed in tandem
with the CLI.  This includes:

* `botocore <https://github.com/boto/botocore>`__
* `jmespath <https://github.com/boto/jmespath>`__

If you just want to install a snapshot of the latest development version of
the CLI, you can use the ``requirements.txt`` file included in this repo.
This file points to the development version of the above packages::

    cd <path_to_awscli>
    pip install -r requirements.txt
    pip install -e .

However, to keep up to date, you will continually have to run the
``pip install -r requirements.txt`` file to pull in the latest changes
from the develop branches of botocore, jmespath, etc.

You can optionally clone each of those repositories and run "pip install -e ."
for each repository::

    git clone <jmespath> && cd jmespath/
    pip install -e . && cd ..
    git clone <botocore> && cd botocore/
    pip install -e . && cd ..
    git clone <awscli> && cd aws-cli/
    pip install -e .


.. _`Amazon Web Services Security Bulletins website`: https://aws.amazon.com/security/security-bulletins
.. _pip: http://www.pip-installer.org/en/latest/
.. _`download the tarball`: https://pypi.python.org/pypi/awscli
