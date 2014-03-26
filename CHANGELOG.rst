=========
CHANGELOG
=========

Next Release (TBD)
==================

* bugfix:Table Output: Fix issue when displaying unicode
  characters in table output
  (`issue 721 <https://github.com/aws/aws-cli/pull/721>`__)


1.3.4
=====

* bugfix:``aws ec2``: Fix issue with EC2 model resulting in
  responses not being parsed.


1.3.3
=====

* feature:``aws ec2``: Add support for Amazon VPC peering
* feature:``aws redshift``: Add support for the latest Amazon Redshift API
* feature:``aws cloudsearch``: Add support for the latest Amazon CloudSearch
  API
* bugfix:``aws cloudformation``: Documentation updates
* bugfix:Argument Parsing: Fix issue when list arguments were
  not being decoded to unicode properly
  (`issue 711 <https://github.com/aws/aws-cli/issues/711>`__)
* bugfix:Output: Fix issue when invalid output type was provided
  in a config file or environment variable
  (`issue 600 <https://github.com/aws/aws-cli/issues/600>`__)


1.3.2
=====

* bugfix:``aws datapipeline``: Fix issue when serializing
  pipeline definitions containing list elements
  (`issue 705 <https://github.com/aws/aws-cli/issues/705>`__)
* bugfix:``aws s3``: Fix issue when recursively removing keys
  containing control characters
  (`issue 675 <https://github.com/aws/aws-cli/issues/675>`__)
* bugfix:``aws s3``: Honor ``--no-verify-ssl`` in high level
  ``aws s3`` commands
  (`issue 696 <https://github.com/aws/aws-cli/issues/696>`__)


1.3.1
=====

* bugfix:Parameters: Fix issue parsing with CLI
  parameters of type ``long``
  (`issue 693 <https://github.com/aws/aws-cli/pull/693/files>`__)
* bugfix:Pagination: Fix issue where ``--max-items``
  in pagination was always assumed to be an integer
  (`issue 689 <https://github.com/aws/aws-cli/pull/689>`__)
* feature:``aws elb``: Add support for AccessLog
* bugfix:Bundled Installer: Allow creation of bundled
  installer with ``pip 1.5``
  (`issue 691 <https://github.com/aws/aws-cli/issues/691>`__)
* bugfix:``aws s3``: Fix issue when copying objects using
  ``aws s3 cp`` with key names containing ``+`` characters
  (`issue #614 <https://github.com/aws/aws-cli/issues/614>`__)
* bugfix:``ec2 create-snapshot``: Remove ``Tags`` key from
  output response
  (`issue 247 <https://github.com/boto/botocore/pull/247>`__)
* bugfix:``aws s3``: ``aws s3`` commands should not be requiring regions
  (`issue 681 <https://github.com/aws/aws-cli/issues/681>`__)
* bugfix:``CLI Arguments``: Fix issue where unicode command line
  arguments were not being handled correctly
  (`issue 679 <https://github.com/aws/aws-cli/pull/679>`__)


1.3.0
=====

* bugfix:``aws s3``: Fix issue where S3 downloads would hang
  in certain cases and could not be interrupted
  (`issue 650 <https://github.com/aws/aws-cli/issues/650>`__,
   `issue 657 <https://github.com/aws/aws-cli/issues/657>`__)
* bugfix:``aws s3``: Support missing canned ACLs when using
  the ``--acl`` parameter
  (`issue 663 <https://github.com/aws/aws-cli/issues/663>`__)
* bugfix:``aws rds describe-engine-default-parameters``: Fix
  pagination issue when calling
  ``aws rds describe-engine-default-parameters``
  (`issue 607 <https://github.com/aws/aws-cli/issues/607>`__)
* bugfix:``aws cloudtrail``: Merge existing SNS topic policy
  with the existing AWS CloudTrail policy instead of overwriting
  the default topic policy
* bugfix:``aws s3``: Fix issue where streams were not being
  rewound when encountering 307 redirects with multipart uploads
  (`issue 544 <https://github.com/aws/aws-cli/issues/544>`__)
* bugfix:``aws elb``: Fix issue with documentation errors
  in ``aws elb help``
  (`issue 622 <https://github.com/aws/aws-cli/issues/622>`__)
* bugfix:JSON Parameters: Add a more clear error message
  when parsing invalid JSON parameters
  (`issue 639 <https://github.com/aws/aws-cli/pull/639>`__)
* bugfix:``aws s3api``: Properly handle null inputs
  (`issue 637 <https://github.com/aws/aws-cli/issues/637>`__)
* bugfix:Argument Parsing: Handle files containing JSON with
  leading and trailing spaces
  (`issue 640 <https://github.com/aws/aws-cli/pull/640>`__)


1.2.13
======

* feature:``aws route53``: Update ``aws route53`` command to
  support string-match health checks and the UPSERT action for the
  ``aws route53 change-resource-record-sets`` command
* bugfix:Command Completion: Don't show tracebacks on SIGINT
  (`issue 628 <https://github.com/aws/aws-cli/issues/628>`__)
* bugfix:Docs: Don't duplicate enum values in reference docs
  (`issue 632 <https://github.com/aws/aws-cli/pull/632>`__)
* bugfix:``aws s3``: Don't require ``s3://`` prefix
  (`issue 626 <https://github.com/aws/aws-cli/pull/626>`__)


1.2.12
======

* feature:``aws configure``: Add support for ``configure get`` and ``configure
  set`` command which allow you to set and get configuration values from the
  AWS config file (`issue 602 <https://github.com/aws/aws-cli/issues/602`__)
* bugfix:``aws s3``: Fix issue with Amazon S3 downloads on certain OSes
  (`issue 619 <https://github.com/aws/aws-cli/issues/619`__)


1.2.11
======

* Add support for the ``--recursive`` option in the ``aws s3 ls`` command
  (`issue 465 <https://github.com/aws/aws-cli/issues/465`)
* Add support for the ``AWS_CA_BUNDLE`` environment variable so that users
  can specify an alternate path to a cert bundle
  (`issue 586 <https://github.com/aws/aws-cli/pull/586>`__)
* Add ``metadata_service_timeout`` and ``metadata_service_num_attempts``
  config parameters to control behavior when retrieving credentials using
  an IAM role (`issue 597 <https://github.com/aws/aws-cli/pull/597>`__)
* Retry intermittent ``aws s3`` download failures including socket timeouts
  and content length mismatches (`issue 594 <https://github.com/aws/aws-cli/pull/594>`__)
* Fix response parsing of ``aws s3api get-bucket-location``
  (`issue 345 <https://github.com/aws/aws-cli/issues/345>`__)
* Fix response parsing of the ``aws elastictranscoder`` command
  (`issue 207 <https://github.com/boto/botocore/pull/207>`__)
* Update ``aws elasticache`` command to not require certain parameters


1.2.10
======

* Add support for creating launch configuration or Auto Scaling groups
  using an Amazon EC2 instance, for attaching Amazon EC2 isntances to an
  existing Auto Scaling group, and for describing the limits on the Auto
  Scaling resources in the ``aws autoscaling`` command
* Update documentation in the ``aws support`` command
* Allow the ``--protocol`` customization for ``CreateNetworkAclEntry`` to
  also work for ``ReplaceNetworkAclEntry`` (`issue 559 <https://github.com/aws/aws-cli/issues/559>`__)
* Remove one second delay when tasks are finished running for several
  ``aws s3`` subcommands (`issue 551 <https://github.com/aws/aws-cli/pull/551>`__)
* Fix bug in shorthand documentation generation that prevented certain
  nested structure parameters from being fully documented (`issue 579 <https://github.com/aws/aws-cli/pull/579>`__)
* Update default timeout from .1 second to 1 second (`botocore issue 202 <https://github.com/boto/botocore/pull/202>`__)
* Removed filter parameter in RDS operations (`issue 515 <https://github.com/aws/aws-cli/issues/515>`__)
* Fixed region endpoint for the ``aws kinesis`` command (`botocore issue 194 <https://github.com/boto/botocore/pull/194>`__)


1.2.9
=====

* Fix issue 548 where ``--include/--exclude`` arguments for various
  ``aws s3`` commands were prepending the CWD instead of the source
  directory for filter patterns
* Fix issue 552 where a remote location without a trailing slash would
  show a malformed XML error when using various  ``aws s3`` commands
* Add support for tagging in ``aws emr`` command
* Add support for georestrictions in ``aws cloudfront`` command
* Add support for new audio compression codecs in the
  ``aws elastictranscoder`` command
* Update the ``aws cloudtrail`` command to the latest API
* Add support for the new China (Beijing) Region. Note: Although the AWS CLI
  now includes support for the newly announced China (Beijing)
  Region, the service endpoints will not be accessible until the Region’s
  limited preview is launched in early 2014. To find out more about the new
  Region and request a limited preview account, please visit
  http://www.amazonaws.cn/.


1.2.8
=====

* Add support for parallel multipart uploads when copying objects
  between Amazon S3 locations when using the ``aws s3`` command (issue 538)
* Fix issue 542 where the ``---stack-policy-url`` will parameter will not
  interpret its value as a URL when using the
  ``aws cloudformation create-stack`` command
* Add support for global secondary indexes in the ``aws dynamodb`` command
* Add support for the ``aws kinesis`` command
* Add support for worker roles in the ``aws elasticbeanstalk`` command
* Add support for resource tagging and other new operations in the
  ``aws emr`` command
* Add support for resource-based permissions in the
  ``aws opsworks`` command
* Update the ``aws elasticache`` command to signature version 4


1.2.7
=====

* Allow tcp, udp, icmp, all for ``--protocol`` param of
  the ``ec2 create-network-acl-entry`` command
  (`issue 508 <https://github.com/aws/aws-cli/issues/508>`__)
* Fix bug when filtering ``s3://`` locations with the
  ``--include/--exclude`` params
  (issue 531 <https://github.com/aws/aws-cli/pull/531>`__)
* Fix an issue with map type parameters raising uncaught
  exceptions in commands such as `sns create-platform-application`
  (`issue 407 <https://github.com/aws/aws-cli/issues/407>`__)
* Fix an issue when both ``--private-ip-address`` and
  ``--associate-public-ip-address`` are specified in the
  ``ec2 run-instances`` command
  (`issue 520 <https://github.com/aws/aws-cli/issues/520>`__)
* Fix an issue where ``--output text`` was not providing
  a starting identifier for certain rows
  (`issue 516 <https://github.com/aws/aws-cli/pull/516>`__)
* Update the ``support`` command to the latest version
* Update the ``--query`` syntax to support flattening sublists
  (`boto/jmespath#20 <https://github.com/boto/jmespath/pull/20>`__)


1.2.6
=====

* Allow ``--endpoint-url`` to work with the ``aws s3`` command
  (`issue 469 <https://github.com/aws/aws-cli/pull/469>`__)
* Fix issue with ``aws cloudtrail [create|update]-subscription`` not
  honoring the ``--profile`` argument
  (`issue 494 <https://github.com/aws/aws-cli/issues/494>`__)
* Fix issue with ``--associate-public-ip-address`` when a ``--subnet-id``
  is provided (`issue 501 <https://github.com/aws/aws-cli/issues/501>`__)
* Don't require key names for structures of single scalar values
  (`issue 484 <https://github.com/aws/aws-cli/issues/484>`__)
* Fix issue with symlinks silently failing during ``s3 sync/cp``
  (`issue 425 <https://github.com/aws/aws-cli/issues/425>`__
   and `issue 487 <https://github.com/aws/aws-cli/issues/487>`__)
* Add a ``aws configure list`` command to show where the configuration
  values are sourced from
  (`issue 513 <https://github.com/aws/aws-cli/pull/513>`__)
* Update ``cloudwatch`` command to use Signature Version 4
* Update ``ec2`` command to support enhanced network capabilities and
  pagination controls for ``describe-instances`` and ``describe-tags``
* Add support in ``rds`` command for copying DB snapshots from
  one AWS region to another


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
