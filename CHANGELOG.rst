=========
CHANGELOG
=========

1.2.5
=====

* Add support for AWS Cloudtrail
* Add support for identity federation using SAML 2.0 in the ``aws iam`` command
* Update the ``aws redshift`` command to include several new features related to
  event notifications, encryption, audit logging, data load from external hosts,
  WLM configuration, and database distribution styles and functions
* Add a ``--associate-public-ip-address`` option to the ``ec2 run-instances``
  command (`issue 479 <https://github.com/aws/aws-cli/issues/479>`__)
* Add an ``s3 website`` command for configuring website configuration for an S3
  bucket (`issue 482 <https://github.com/aws/aws-cli/pull/482>`__)


1.2.4
=====

* Fix an issue with the ``s3`` command when using GovCloud regions
  (boto/botocore#170)
* Fix an issue with the ``s3 ls`` command making an extra query at the
  root level (issue 439)
* Add detailed error message when unable to decode local filenames during
  an ``s3 sync`` (issue 378)
* Support ``-1`` and ``all`` as valid values to the ``--protocol`` argument
  to ``ec2 authorize-security-group-ingress`` and
  ``ec2 authorize-security-group-egress`` (issue 460)
* Log the reason why a file is synced when using the ``s3 sync`` command
* Fix an issue when uploading large files on low bandwidth networks
  (issue 454)
* Fix an issue with parsing shorthand boolean argument values (issue 477)
* Fix an issue with the ``cloudsearch`` command missing a required attribute
  (boto/botocore#175)
* Fix an issue with parsing XML response for
  ``ec2 describe-instance-attribute`` (boto/botocore#174)
* Update ``cloudformation`` command to support new features for stacks and
  templates
* Update ``storagegateway`` command to support a new gateway configuration,
  Gateway-Virtual Tape Library (Gateway-VTL)
* Update ``elb`` command to support cross-zone load balancing, which
  changes the way that Elastic Load Balancing (ELB) routes incoming requests


1.2.3
=====

* Add a new ``configure`` command that allows users to interactively specify
  configuration values (pull request 455)
* Add support for new EMR APIs, termination of specific cluster instances, and
  unlimited EMR steps
* Update Amazon CloudFront command to the 2013-09-27 API version
* Fix issue where Expires timestamp in bundle-instance policy is incorrect
  (issue 456)
* The requests library is now vendored in botocore (at version 2.0.1)
* Fix an issue where timestamps used for Signature Version 4 weren't being
  refreshed (boto/botocore#162)


1.2.2
=====

* Fix an issue causing ``s3 sync`` with the ``--delete`` incorrectly deleting files (issue 440)
* Fix an issue with ``--output text`` combined with paginated results (boto/botocore#165)
* Fix a bug in text output when an empty list is encountered (issue 446)


1.2.1
=====

* Update the AWS Direct Connect command to support the latest features
* Fix text output with single scalar value (issue 428)
* Fix shell quoting for ``PAGER``/``MANPAGER`` environment variable (issue 429)
* --endpoint-url is explicitly used for URL of remote service (boto/botocore#163)
* Fix an validation error when using ``--ip-permissions`` and ``--group-id`` together (issue 435)


1.2.0
=====

* Update Amazon Elastic Transcoder command with audio transcoding features
* Improve text output (``--output text``) to have a consistent output structure
* Add ``--query`` argument that allows you to specify output data using a JMESPath expression
* Upgrade requests library to 2.0.0
* Update Amazon Redshift region configuration to include ``ap-southeast-1``  and ``ap-southeast-2``
* Update Amazon S3 region configuration to include ``fips-us-gov-west-1``
* Add a bundled installer for the CLI which bundles all necessary dependencies (does not require pip)
* Fix an issue with ZSH tab completion (issue 411)
* Fix an issue with S3 requests timing out (issue 401)
* Fix an issue with ``s3api delete-objects`` not providing the ``Content-MD5`` header (issue 400)


1.1.2
=====

* Update the Amazon EC2 command to support Reserved Instance instance type modifications
* Update the AWS OpsWorks command to support new resource management features
* Fix an issue when transferring files on different drives on Windows
* Fix an issue that caused interactive help to emit control characters on certain Linux distributions


1.1.1
=====

* Update the Amazon CloudFront command to support the latest API version 2013-08-26
* Update the Auto Scaling client to support public IP address association of instances
* Update Amazon SWF to support signature version 4
* Update Amazon RDS with a new subcommand, ``add-source-identifier-to-subscription``


1.1.0
=====

* Update the ``s3`` commands to support the setting for how objects are stored in Amazon S3
* Update the Amazon EC2 command to support the latest API version (2013-08-15)
* Fix an issue causing excessive CPU utilization in some scenarios where many files were being uploaded
* Fix a memory growth issue with ``s3`` copying and syncing of files
* Fix an issue caused by a conflict with a dependency and Python 3.x that caused installation to fail
