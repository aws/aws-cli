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

from awscli.customizations.emr.createdefaultroles import EMR_ROLE_NAME
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

SERVICE_ROLE = (
    '<p>Allows EMR to call other AWS Services such as EC2 on your behalf.</p>'
    'To create the default Service Role <code>' + EMR_ROLE_NAME + '</code>,'
    ' use <code>aws emr create-default-roles</code> command. </p>'
    'This command will also create the default EC2 instance profile '
    '<code>' + EC2_ROLE_NAME + '</code>.')

USE_DEFAULT_ROLES = (
    '<p>Uses --service-role=<code>' + EMR_ROLE_NAME + '</code>, and '
    '--ec2-attributes InstanceProfile=<code>' + EC2_ROLE_NAME + '</code>'
    'To create the default service role and instance profile'
    ' use <code>aws emr create-default-roles</code> command. </p>')

AMI_VERSION = (
    '<p>The version number of the Amazon Machine Image (AMI) '
    'to use for Amazon EC2 instances in the cluster. '
    'For example,--ami-version 3.1.0  You cannot specify both a release label'
    ' (emr-4.0.0 and later) and an AMI version (3.x or 2.x) on a cluster</p>'
    '<p>For details about the AMIs currently supported by Amazon '
    'Elastic MapReduce, go to AMI Versions Supported in Amazon Elastic '
    'MapReduce in the Amazon Elastic MapReduce Developer\'s Guide.</p>'
    '<p>http://docs.aws.amazon.com/ElasticMapReduce/latest/DeveloperGuide/'
    'ami-versions-supported.html</p>')

RELEASE_LABEL = (
    '<p>The identifier for the EMR release, which includes a set of software,'
    ' to use with Amazon EC2 instances that are part of an Amazon EMR cluster.'
    ' For example, --release-label emr-4.0.0  You cannot specify both a'
    ' release label (emr-4.0.0 and later) and AMI version (3.x or 2.x) on a'
    ' cluster.</p>'
    '<p>For details about the releases available in Amazon Elastic MapReduce,'
    ' go to Releases Available in Amazon Elastic MapReduce in the'
    ' Amazon Elastic MapReduce Documentation.</p>'
    '<p>http://docs.aws.amazon.com/ElasticMapReduce/latest/Applications/'
    'emr-release.html</p><p>Please use ami-version if you want to specify AMI'
    ' Versions for your Amazon EMR cluster (3.x and 2.x)</p>')

CONFIGURATIONS = (
    '<p>Specifies new configuration values for applications installed on your'
    ' cluster when using an EMR release (emr-4.0.0 and later). The'
    ' configuration files available for editing in each application (for'
    ' example: yarn-site for YARN) can be found in the Amazon EMR Developer\'s'
    ' Guide in the respective application\'s section. Currently on the CLI,'
    ' you can only specify these values in a JSON file stored locally or in'
    ' Amazon S3, and you supply the path to this file to this parameter.</p>'
    '<p> For example:</p>'
    '<li>To specify configurations from a local file <code>--configurations'
    ' file://configurations.json</code></li>'
    ' <li>To specify configurations from a file in Amazon S3 <code>'
    '--configurations https://s3.amazonaws.com/myBucket/configurations.json'
    '</code></li>'
    '<p>For more information about configuring applications in EMR release,'
    ' go to the Amazon EMR Documentation: </p>'
    '<p>http://docs.aws.amazon.com/ElasticMapReduce/latest/Applications/'
    'emr-configure-apps.html</p>'
)

INSTANCE_GROUPS = (
    '<p>A specification of the number and type'
    ' of Amazon EC2 instances to create instance groups in a cluster.</p>'
    '<p> Each instance group takes the following parameters: '
    '<code>[Name], InstanceGroupType, InstanceType, InstanceCount,'
    ' [BidPrice], [EbsConfiguration]</code>. [EbsConfiguration] is optional.'
    ' EbsConfiguration takes the following parameters: <code>EbsOptimized</code>'
    ' and <code>EbsBlockDeviceConfigs</code>. EbsBlockDeviceConfigs is an array of EBS volume'
    ' specifications, which takes the following parameters : <code>([VolumeType], '
    ' [SizeInGB], Iops)</code> and VolumesPerInstance which is the count of EBS volumes'
    ' per instance with this specification.</p>')

INSTANCE_TYPE = (
    '<p>Shortcut option for --instance-groups. A specification of the '
    'type of Amazon EC2 instances used together with --instance-count '
    '(optional) to create instance groups in a cluster. '
    'Specifying the --instance-type argument without '
    'also specifying --instance-count launches a single-node cluster.</p>')

INSTANCE_COUNT = (
    '<p>Shortcut option for --instance-groups. '
    'A specification of the number of Amazon EC2 instances used together with'
    ' --instance-type to create instance groups in a cluster. EMR will use one'
    ' node as the cluster\'s master node and use the remainder of the nodes as'
    ' core nodes. Specifying the --instance-type argument without '
    'also specifying --instance-count launches a single-node cluster.</p>')

ADDITIONAL_INFO = (
    '<p>Specifies additional information during cluster creation</p>')

EC2_ATTRIBUTES = (
    '<p>Specifies the following Amazon EC2 attributes: KeyName,'
    ' AvailabilityZone, SubnetId, InstanceProfile,'
    ' EmrManagedMasterSecurityGroup, EmrManagedSlaveSecurityGroup,'
    ' AdditionalMasterSecurityGroups and AdditionalSlaveSecurityGroups.'
    ' AvailabilityZone and Subnet cannot be specified together.'
    ' To create the default instance profile <code>' +
    EC2_ROLE_NAME + '</code>,'
    ' use <code>aws emr create-default-roles</code> command. </p>'
    'This command will also create the default EMR service role '
    '<code>' + EMR_ROLE_NAME + '</code>.'
    '<li>KeyName - the name of the AWS EC2 key pair you are using '
    'to launch the cluster.</li>'
    '<li>AvailabilityZone - An isolated resource '
    'location within a region.</li>'
    '<li>SubnetId - Assign the EMR cluster to this Amazon VPC Subnet. </li>'
    '<li>InstanceProfile - Provides access to other AWS services such as S3,'
    ' DynamoDB from EC2 instances that are launched by EMR.. </li>'
    '<li>EmrManagedMasterSecurityGroup - The identifier of the Amazon EC2'
    ' security group'
    ' for the master node. </li>'
    '<li>EmrManagedSlaveSecurityGroup - The identifier of the Amazon EC2'
    ' security group'
    ' for the slave nodes.</li>'
    '<li>ServiceAccessSecurityGroup - The identifier of the Amazon EC2 '
    'security group for the Amazon EMR service '
    'to access clusters in VPC private subnets </li>'
    '<li>AdditionalMasterSecurityGroups - A list of additional Amazon EC2'
    ' security group IDs for the master node</li>'
    '<li>AdditionalSlaveSecurityGroups - A list of additional Amazon EC2'
    ' security group IDs for the slave nodes.</li>')

AUTO_TERMINATE = (
    '<p>Specifies whether the cluster should terminate after'
    ' completing all the steps. Auto termination is off by default.</p>')

TERMINATION_PROTECTED = (
    '<p>Specifies whether to lock the cluster to prevent the'
    ' Amazon EC2 instances from being terminated by API call, '
    'user intervention, or in the event of an error. Termination protection '
    'is off by default.</p>')

VISIBILITY = (
    '<p>Specifies whether the cluster is visible to all IAM users of'
    ' the AWS account associated with the cluster. If set to '
    '<code>--visible-to-all-users</code>, all IAM users of that AWS account'
    ' can view and (if they have the proper policy permisions set) manage'
    ' the cluster. If it is set to <code>--no-visible-to-all-users</code>,'
    ' only the IAM user that created the cluster can view and manage it. '
    ' Clusters are visible by default. </p>')

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
    '<code>Path</code>, <code>[Name]</code> and <code>[Args]</code>. '
    'Note: Args should either be a comma-separated list of values  '
    '(e.g. Args=arg1,arg2,arg3) or a bracket-enclosed list of values '
    'and/or key-value pairs (e.g. Args=[arg1,arg2=arg3,arg4]).</p>')

APPLICATIONS = (
    '<p>Installs applications such as Hadoop, Spark, Hue, Hive, Pig, HBase,'
    ' Ganglia and Impala  or the MapR distribution when creating a cluster.'
    ' Available applications vary by EMR release, and the set of components'
    ' installed when specifying an Application Name can be found in the Amazon'
    ' EMR Developer\'s Guide. Note: If you are using an AMI version instead of'
    ' an EMR release, some applications take optional Args for configuration.'
    ' Args should either be a comma-separated list of values'
    ' (e.g. Args=arg1,arg2,arg3) or a bracket-enclosed list of values'
    ' and/or key-value pairs (e.g. Args=[arg1,arg2=arg3,arg4]).</p>')

EMR_FS = (
    '<p>Configures certain features in EMRFS like consistent'
    ' view, Amazon S3 client-side and server-side encryption.</p>'
    '<li>Encryption - enables Amazon S3 server-side encryption or'
    ' Amazon S3 client-side encryption and takes the mutually exclusive'
    ' values, ServerSide or ClientSide.</li>'
    '<li>ProviderType - the encryption ProviderType, which is either Custom'
    ' or KMS</li> '
    '<li>KMSKeyId - the AWS KMS KeyId, the alias'
    ' you mapped to the KeyId, or the full ARN of the key that'
    ' includes the region, account ID, and the KeyId.</li>'
    '<li>CustomProviderLocation - the S3 URI of'
    ' the custom EncryptionMaterialsProvider class.</li>'
    '<li>CustomProviderClass - the name of the'
    ' custom EncryptionMaterialsProvider class you are using.</li>'
    '<li>Consistent - setting to true enables consistent view.</li>'
    '<li>RetryCount - the number of times EMRFS consistent view will check'
    ' for list consistency before returning an error.</li>'
    '<li>RetryPeriod - the interval at which EMRFS consistent view will'
    ' recheck for consistency of objects it tracks.</li>'
    '<li>SSE - deprecated in favor of Encryption=ServerSide</li>'
    '<li>Args - optional arguments you can supply in configuring EMRFS.</li>')

RESTORE_FROM_HBASE = (
    '<p>Launches a new HBase cluster and populates it with'
    ' data from a previous backup of an HBase cluster. You must install HBase'
    ' using the <code>--applications</code> option.'
    ' Note: this is only supported by AMI versions (3.x and 2.x).</p>')


STEPS = (
    '<p>A list of steps to be executed by the cluster. A step can be'
    ' specified either using the shorthand syntax, JSON file or as a JSON'
    ' string. Note: [Args] supplied with steps should either be a'
    ' comma-separated list of values (e.g. Args=arg1,arg2,arg3) or'
    ' a bracket-enclosed list of values and/or key-value pairs'
    ' (e.g. Args=[arg1,arg2=arg3,arg4]).</p>')

INSTALL_APPLICATIONS = (
    '<p>The applications to be installed.'
    ' Takes the following parameters: '
    '<code>Name</code> and <code>Args</code>.')

LIST_CLUSTERS_CLUSTER_STATES = (
    '<p>The cluster state filters to apply when listing clusters.</p>'
    '<p>Syntax:'
    '"string" "string" ...</p>'
    '<p>Where valid values are:</p>'
    '<li>STARTING</li>'
    '<li>BOOTSTRAPPING</li>'
    '<li>RUNNING</li>'
    '<li>WAITING</li>'
    '<li>TERMINATING</li>'
    '<li>TERMINATED</li>'
    '<li>TERMINATED_WITH_ERRORS</li></p>')

LIST_CLUSTERS_STATE_FILTERS = (
    '<p>Shortcut option for --cluster-states. </p>'
    '<li>--active filters clusters in \'STARTING\','
    '\'BOOTSTRAPPING\',\'RUNNING\','
    '\'WAITING\', or \'TERMINATING\' states. </li>'
    '<li>--terminated filters clusters in \'TERMINATED\' state. </li>'
    '<li>--failed filters clusters in \'TERMINATED_WITH_ERRORS\' state. </li>')

LIST_CLUSTERS_CREATED_AFTER = (
    '<p>The creation date and time beginning value filter for '
    'listing clusters. For example, 2014-07-15T00:01:30. </p>')

LIST_CLUSTERS_CREATED_BEFORE = (
    '<p>The creation date and time end value filter for '
    'listing clusters. For example, 2014-07-15T00:01:30. </p>')

EMR_MANAGED_MASTER_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for the master node.</p>')

EMR_MANAGED_SLAVE_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for the slave nodes.</p>')

SERVICE_ACCESS_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for the Amazon EMR service to access '
    'clusters in VPC private subnets.</p>')

ADDITIONAL_MASTER_SECURITY_GROUPS = (
    '<p> A list of additional Amazon EC2 security group IDs for '
    'the master node</p>')

ADDITIONAL_SLAVE_SECURITY_GROUPS = (
    '<p>A list of additional Amazon EC2 security group IDs for '
    'the slave nodes.</p>')

AVAILABLE_ONLY_FOR_AMI_VERSIONS = (
    'This command is only available for AMI Versions (3.x and 2.x).')

CREATE_CLUSTER_DESCRIPTION = (
    'Creates an Amazon EMR cluster with specified software.\n'
    '\nQuick start:\n\naws emr create-cluster --release-label <release-label>'
    ' --instance-type <instance-type> [--instance-count <instance-count>]\n\n'
    'Values for variables Instance Profile (under EC2 Attributes),'
    ' Service Role, Log URI, and Key Name (under EC2 Attributes) can be set in'
    ' the AWS CLI config file using the "aws configure set" command.\n')

SECURITY_CONFIG = (
    '<p>The name of a security configuration in the AWS account. '
    'Use <code>list-security-configurations</code> to get a list of available '
    'security configurations.</p>')