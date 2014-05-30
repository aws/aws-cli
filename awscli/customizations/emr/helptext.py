# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.customizations.emr.createdefaultroles import EC2_ROLE_NAME

TERMINATE_CLUSTERS = (
    'Shuts down a list of clusters. When a cluster is shut'
    ' down, any step not yet completed is canceled and the '
    'Amazon EC2 instances in the cluster are terminated. '
    'Any log files not already saved are uploaded to'
    ' Amazon S3 if a LogUri was specified when the cluster was created.'
    " 'terminate-clusters' is asynchronous. Depending on the"
    ' configuration of the cluster, it may take from 5 to 20 minutes for the'
    ' cluster to completely terminate and release allocated resources such as'
    ' Amazon EC2 instances.')

CLUSTER_ID = (
    '<p>A unique string that identifies the cluster. This'
    ' identifier is returned by <code>create-cluster</code> and can also be'
    ' obtained from <code>list-clusters</code>.</p>')

HBASE_BACKUP_DIR = (
    '<p>Amazon S3 location of the Hbase backup.</p> Example:<p>'
    '<code>s3://mybucket/mybackup</code></p><p> where mybucket is the'
    ' specified Amazon S3 bucket and mybackup is the specified backup'
    ' location. The path argument must begin with s3:// in order to denote'
    ' that the path argument refers to an Amazon S3 folder.</p>')

HBASE_BACKUP_VERSION = (
    '<p>Backup version to restore from. If not specified the latest backup '
    'in the specified location will be used.</p>')

# create-cluster options help text
CLUSTER_NAME = (
    '<p>The name of the cluster. The default is "Development Cluster".</p>')

LOG_URI = (
    '<p>The location in Amazon S3 to write the log files '
    'of the cluster. If a value is not provided, '
    'logs are not created.</p>')

AMI_VERSION = (
    '<p>The version number of the Amazon Machine Image (AMI) '
    'to use for Amazon EC2 instances in the cluster. '
    'For example,--ami-version 3.1.0 </p>'
    '<p>For details about the AMIs currently supported by Amazon '
    'Elastic MapReduce, go to AMI Versions Supported in Amazon Elastic '
    'MapReduce in the Amazon Elastic MapReduce Developer\'s Guide.</p>'
    '<p>http://docs.aws.amazon.com/ElasticMapReduce/latest/DeveloperGuide/'
    'ami-versions-supported.html</p>')

INSTANCE_GROUPS = (
    '<p>A specification of the number and type'
    ' of Amazon EC2 instances to create instance groups in a cluster.</p>'
    '<p> Each instance group takes the following parameters: '
    '<code>[Name], InstanceGroupType, InstanceType, InstanceCount,'
    ' [BidPrice]</code></p>')

ADDITIONAL_INFO = (
    '<p>Specifies additional information during cluster creation</p>')

EC2_ATTRIBUTES = (
    '<p>Specifies the following Amazon EC2 attributes: KeyName,'
    ' AvailabilityZone, SubnetId, and InstanceProfile. AvailabilityZone and '
    'Subnet cannot be specified together. To create the default '
    'instance profile <code>' + EC2_ROLE_NAME + '</code>,'
    ' use <code>aws emr create-default-roles</code> command. </p>'
    '<li>KeyName - the name of the AWS EC2 key pair you are using '
    'to launch the cluster.</li>'
    '<li>AvailabilityZone - An isolated resource '
    'location within a region.</li>'
    '<li>SubnetId- Assign the EMR cluster to this Amazon VPC Subnet. </li>'
    '<li>InstanceProfile - A container for the EC2 IAM Role. </li>'
    )

AUTO_TERMINATE = (
    '<p>Specifies whether the cluster should terminate after'
    ' completing all the steps.</p>')

TERMINATION_PROTECTED = (
    '<p>Specifies whether to lock the cluster to prevent the'
    ' Amazon EC2 instances from being terminated by API call, '
    'user intervention, or in the event of an error.</p>')

VISIBILITY = (
    '<p>Specifies whether the cluster is visible to all IAM users of'
    ' the AWS account associated with the cluster. If set to '
    '<code>--visible-to-all-users</code>, all IAM users of that AWS account'
    ' can view and (if they have the proper policy permisions set) manage'
    ' the cluster. If it is set to <code>--no-visible-to-all-users</code>,'
    ' only the IAM user that created the cluster can view and manage it.</p>')

DEBUGGING = (
    '<p>Enables debugging for the cluster. The debugging tool is a'
    ' graphical user interface that you can use to browse the log files from'
    ' the console (<link>https://console.aws.amazon.com/elasticmapreduce/'
    '</link> ). When you enable debugging on a cluster, Amazon EMR archives'
    ' the log files to Amazon S3 and then indexes those files. You can then'
    ' use the graphical interface to browse the step, job, task, and task'
    ' attempt logs for the cluster in an intuitive way.</p><p>Requires'
    ' <code>--log-uri</code> to be specified</p>')

TAGS = (
    '<p>A list of tags to associate with a cluster and propagate to'
    ' each Amazon EC2 instance in the cluster. '
    'They are user-defined key/value pairs that'
    ' consist of a required key string with a maximum of 128 characters'
    ' and an optional value string with a maximum of 256 characters.</p>'
    '<p>You can specify tags in <code>key=value</code> format or to add a'
    ' tag without value just write key name, <code>key</code>.</p>'
    '<p>Syntax:</p><p>Multiple tags separated by a space. </p>'
    '<p>--tags key1=value1 key2=value2</p>')

BOOTSTRAP_ACTIONS = (
    '<p>Specifies a list of bootstrap actions to run when creating a'
    ' cluster. You can use bootstrap actions to install additional software'
    ' and to change the configuration of applications on the cluster.'
    ' Bootstrap actions are scripts that are run on the cluster nodes when'
    ' Amazon EMR launches the cluster. They run before Hadoop starts and'
    ' before the node begins processing data.</p>'
    '<p>Each bootstrap action takes the following parameters: '
    '<code>Path</code>, <code>[Name]</code> and <code>[Args]</code>.</p>')

APPLICATIONS = (
    '<p>Installs applications such as Hive, Pig, HBase, Ganglia and'
    ' Impala  or the MapR distribution when creating a cluster. '
    'Each application takes the following'
    ' parameters: <code>Name</code>, <code>[Version]</code> and <code>[Args]'
    '</code>. </p>')

RESTORE_FROM_HBASE = (
    '<p>Launches a new HBase cluster and populates it with'
    ' data from a previous backup of an HBase cluster. You must install HBase'
    ' using the <code>--applications</code> option. </p>')


STEPS = (
    '<p>A list of steps to be executed by the cluster. A step can be'
    ' specified either using the shorthand syntax, JSON file or as a JSON'
    ' string. </p>')

INSTALL_APPLICATIONS = (
    '<p>The applications to be installed.'
    ' Takes the following parameters: <code>Name</code>, <code>Version</code>'
    ' and <code>Args</code>.')
