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
    'Shuts down one or more clusters, each specified by cluster ID. '
    'Use this command only on clusters that do not have termination '
    'protection enabled. Clusters with termination protection enabled '
    'are not terminated. When a cluster is shut '
    'down, any step not yet completed is canceled and the '
    'Amazon EC2 instances in the cluster are terminated. '
    'Any log files not already saved are uploaded to '
    'Amazon S3 if a --log-uri was specified when the cluster was created. '
    'The maximum number of clusters allowed in the list is 10. '
    'The command is asynchronous. Depending on the '
    'configuration of the cluster, it may take from 5 to 20 minutes for the '
    'cluster to terminate completely and release allocated resources such as '
    'Amazon EC2 instances.')

CLUSTER_ID = (
    '<p>A unique string that identifies a cluster. The '
    '<code>create-cluster</code> command returns this identifier. You can '
    'use the <code>list-clusters</code> command to get cluster IDs.</p>')

HBASE_BACKUP_DIR = (
    '<p>The Amazon S3 location of the Hbase backup. Example: '
    '<code>s3://mybucket/mybackup</code>, where <code>mybucket</code> is the '
    'specified Amazon S3 bucket and mybackup is the specified backup '
    'location. The path argument must begin with s3://, which '
    'refers to an Amazon S3 bucket.</p>')

HBASE_BACKUP_VERSION = (
    '<p>The backup version to restore from. If not specified, the latest backup '
    'in the specified location is used.</p>')

# create-cluster options help text

CREATE_CLUSTER_DESCRIPTION = (
    'Creates an Amazon EMR cluster with the specified configurations.')

DESCRIBE_CLUSTER_DESCRIPTION = (
    'Provides  cluster-level details including status, hardware '
    'and software configuration, VPC settings, bootstrap '
    'actions, instance groups and so on. '
    'Permissions needed for describe-cluster include '
    'elasticmapreduce:ListBootstrapActions, '
    'elasticmapreduce:ListInstanceFleets, '
    'elasticmapreduce:DescribeCluster, '
    'and elasticmapreduce:ListInstanceGroups.')

CLUSTER_NAME = (
    '<p>The name of the cluster. If not provided, the default is "Development Cluster".</p>')

LOG_URI = (
    '<p>Specifies the location in Amazon S3 to which log files '
    'are periodically written. If a value is not provided, '
    'logs files are not written to Amazon S3 from the master node '
    'and are lost if the master node terminates.</p>')

LOG_ENCRYPTION_KMS_KEY_ID = (
    '<p> Specifies the KMS Id utilized for log encryption. If a value is '
    'not provided, log files will be encrypted by default encryption method '
    'AES-256. This attribute is only available with EMR version 5.30.0 and later, '
    'excluding EMR 6.0.0.</p>')

SERVICE_ROLE = (
    '<p>Specifies an IAM service role, which Amazon EMR requires to call other AWS services '
    'on your behalf during cluster operation. This parameter '
    'is usually specified when a customized service role is used. '
    'To specify the default service role, as well as the default instance '
    'profile, use the <code>--use-default-roles</code> parameter. '
    'If the role and instance profile do not already exist, use the '
    '<code>aws emr create-default-roles</code> command to create them.</p>')

AUTOSCALING_ROLE = (
    '<p>Specify <code>--auto-scaling-role EMR_AutoScaling_DefaultRole</code>'
    ' if an automatic scaling policy is specified for an instance group'
    ' using the <code>--instance-groups</code> parameter. This default'
    ' IAM role allows the automatic scaling feature'
    ' to launch and terminate Amazon EC2 instances during scaling operations.</p>')

USE_DEFAULT_ROLES = (
    '<p>Specifies that the cluster should use the default'
    ' service role (EMR_DefaultRole) and instance profile (EMR_EC2_DefaultRole)'
    ' for permissions to access other AWS services.</p>'
    '<p>Make sure that the role and instance profile exist first. To create them,'
    ' use the <code>create-default-roles</code> command.</p>')

AMI_VERSION = (
    '<p>Applies only to Amazon EMR release versions earlier than 4.0. Use'
    ' <code>--release-label</code> for 4.0 and later. Specifies'
    ' the version of Amazon Linux Amazon Machine Image (AMI)'
    ' to use when launching Amazon EC2 instances in the cluster.'
    ' For example, <code>--ami-version 3.1.0</code>.')

RELEASE_LABEL = (
    '<p>Specifies the Amazon EMR release version, which determines'
    ' the versions of application software that are installed on the cluster.'
    ' For example, <code>--release-label emr-5.15.0</code> installs'
    ' the application versions and features available in that version.'
    ' For details about application versions and features available'
    ' in each release, see the Amazon EMR Release Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ReleaseGuide</p>'
    '<p>Use <code>--release-label</code> only for Amazon EMR release version 4.0'
    ' and later. Use <code>--ami-version</code> for earlier versions.'
    ' You cannot specify both a release label and AMI version.</p>')

OS_RELEASE_LABEL = (
    '<p>Specifies a particular Amazon Linux release for all nodes in a cluster'
    ' launch request. If a release is not specified, EMR uses the latest validated' 
    ' Amazon Linux release for cluster launch.</p>')

CONFIGURATIONS = (
    '<p>Specifies a JSON file that contains configuration classifications,'
    ' which you can use to customize applications that Amazon EMR installs'
    ' when cluster instances launch. Applies only to Amazon EMR 4.0 and later.'
    ' The file referenced can either be stored locally (for example,'
    ' <code>--configurations file://configurations.json</code>)'
    ' or stored in Amazon S3 (for example, <code>--configurations'
    ' https://s3.amazonaws.com/myBucket/configurations.json</code>).'
    ' Each classification usually corresponds to the xml configuration'
    ' file for an application, such as <code>yarn-site</code> for YARN. For a list of'
    ' available configuration classifications and example JSON, see'
    ' the following topic in the Amazon EMR Release Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-configure-apps.html</p>')

INSTANCE_GROUPS = (
    '<p>Specifies the number and type of Amazon EC2 instances'
    ' to create for each node type in a cluster, using uniform instance groups.'
    ' You can specify either <code>--instance-groups</code> or'
    ' <code>--instance-fleets</code> but not both.'
    ' For more information, see the following topic in the EMR Management Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-instance-group-configuration.html</p>'
    '<p>You can specify arguments individually using multiple'
    ' <code>InstanceGroupType</code> argument blocks, one for the <code>MASTER</code>'
    ' instance group, one for a <code>CORE</code> instance group,'
    ' and optional, multiple <code>TASK</code> instance groups.</p>'
    '<p>If you specify inline JSON structures, enclose the entire'
    ' <code>InstanceGroupType</code> argument block in single quotation marks.'
    '<p>Each <code>InstanceGroupType</code> block takes the following inline arguments.'
    ' Optional arguments are shown in [square brackets].</p>'
    '<li><code>[Name]</code> - An optional friendly name for the instance group.</li>'
    '<li><code>InstanceGroupType</code> - <code>MASTER</code>, <code>CORE</code>, or <code>TASK</code>.</li>'
    '<li><code>InstanceType</code> - The type of EC2 instance, for'
    ' example <code>m4.large</code>,'
    ' to use for all nodes in the instance group.</li>'
    '<li><code>InstanceCount</code> - The number of EC2 instances to provision in the instance group.</li>'
    '<li><code>[BidPrice]</code> - If specified, indicates that the instance group uses Spot Instances.'
    ' This is the maximum price you are willing to pay for Spot Instances. Specify OnDemandPrice'
    ' to set the amount equal to the On-Demand price, or specify an amount in USD.</li>'
    '<li><code>[EbsConfiguration]</code> - Specifies additional Amazon EBS storage volumes attached'
    ' to EC2 instances using an inline JSON structure.</li>'
    '<li><code>[AutoScalingPolicy]</code> - Specifies an automatic scaling policy for the'
    ' instance group using an inline JSON structure.</li>')

INSTANCE_FLEETS = (
    '<p>Applies only to Amazon EMR release version 5.0 and later. Specifies'
    ' the number and type of Amazon EC2 instances to create'
    ' for each node type in a cluster, using instance fleets.'
    ' You can specify either <code>--instance-fleets</code> or'
    ' <code>--instance-groups</code> but not both.'
    ' For more information and examples, see the following topic in the Amazon EMR Management Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-instance-fleet.html</p>'
    '<p>You can specify arguments individually using multiple'
    ' <code>InstanceFleetType</code> argument blocks, one for the <code>MASTER</code>'
    ' instance fleet, one for a <code>CORE</code> instance fleet,'
    ' and an optional <code>TASK</code> instance fleet.</p>'
    '<p>The following arguments can be specified for each instance fleet. Optional arguments are shown in [square brackets].</p>'
    '<li><code>[Name]</code> - An optional friendly name for the instance fleet.</li>'
    '<li><code>InstanceFleetType</code> - <code>MASTER</code>, <code>CORE</code>, or <code>TASK</code>.</li>'
    '<li><code>TargetOnDemandCapacity</code> - The target capacity of On-Demand units'
    ' for the instance fleet, which determines how many On-Demand Instances to provision.'
    ' The <code>WeightedCapacity</code> specified for an instance type within'
    ' <code>InstanceTypeConfigs</code> counts toward this total when an instance type'
    ' with the On-Demand purchasing option launches.</li>'
    '<li><code>TargetSpotCapacity</code> - The target capacity of Spot units'
    ' for the instance fleet, which determines how many Spot Instances to provision.'
    ' The <code>WeightedCapacity</code> specified for an instance type within'
    ' <code>InstanceTypeConfigs</code> counts toward this total when an instance'
    ' type with the Spot purchasing option launches.</li>'
    '<li><code>[LaunchSpecifications]</code> - When <code>TargetSpotCapacity</code> is specified,'
    ' specifies the block duration and timeout action for Spot Instances.'
    '<li><code>InstanceTypeConfigs</code> - Specify up to five EC2 instance types to'
    ' use in the instance fleet, including details such as Spot price and Amazon EBS configuration.'
    ' When you use an On-Demand or Spot Instance allocation strategy,'
    ' you can specify up to 30 instance types per instance fleet.</li>')

INSTANCE_TYPE = (
    '<p>Shortcut parameter as an alternative to <code>--instance-groups</code>.'
    ' Specifies the type of Amazon EC2 instance to use in a cluster.'
    ' If used without the <code>--instance-count</code> parameter,'
    ' the cluster consists of a single master node running on the EC2 instance type'
    ' specified. When used together with <code>--instance-count</code>,'
    ' one instance is used for the master node, and the remainder'
    ' are used for the core node type.</p>')

INSTANCE_COUNT = (
    '<p>Shortcut parameter as an alternative to <code>--instance-groups</code>'
    ' when used together with <code>--instance-type</code>. Specifies the'
    ' number of Amazon EC2 instances to create for a cluster.'
    ' One instance is used for the master node, and the remainder'
    ' are used for the core node type.</p>')

ADDITIONAL_INFO = (
    '<p>Specifies additional information during cluster creation. To set development mode when starting your EMR cluster,'
    ' set this parameter to <code>{"clusterType":"development"}</code>.</p>')

EC2_ATTRIBUTES = (
    '<p>Configures cluster and Amazon EC2 instance configurations. Accepts'
    ' the following arguments:</p>'
    '<li><code>KeyName</code> - Specifies the name of the AWS EC2 key pair that will be used for'
    ' SSH connections to the master node and other instances on the cluster.</li>'
    '<li><code>AvailabilityZone</code> - Applies to clusters that use the uniform instance group configuration.'
    ' Specifies the availability zone in which to launch the cluster.'
    ' For example, <code>us-west-1b</code>. <code>AvailabilityZone</code> is used for uniform instance groups,'
    ' while <code>AvailabilityZones</code> (plural) is used for instance fleets.</li>'
    '<li><code>AvailabilityZones</code> - Applies to clusters that use the instance fleet configuration.'
    ' When multiple Availability Zones are specified, Amazon EMR evaluates them and launches instances' 
    ' in the optimal Availability Zone. <code>AvailabilityZone</code> is used for uniform instance groups,'
    ' while <code>AvailabilityZones</code> (plural) is used for instance fleets.</li>'
    '<li><code>SubnetId</code> - Applies to clusters that use the uniform instance group configuration.' 
    ' Specify the VPC subnet in which to create the cluster. <code>SubnetId</code> is used for uniform instance groups,'
    ' while <code>SubnetIds</code> (plural) is used for instance fleets.</li>'
    '<li><code>SubnetIds</code> - Applies to clusters that use the instance fleet configuration.'
    ' When multiple EC2 subnet IDs are specified, Amazon EMR evaluates them and launches instances in the optimal subnet.'
    ' <code>SubnetId</code> is used for uniform instance groups,'
    ' while <code>SubnetIds</code> (plural) is used for instance fleets.</li>'
    '<li><code>InstanceProfile</code> - An IAM role that allows EC2 instances to'
    ' access other AWS services, such as Amazon S3, that'
    ' are required for operations.</li>'
    '<li><code>EmrManagedMasterSecurityGroup</code> - The security group ID of the Amazon EC2'
    ' security group for the master node.</li>'
    '<li><code>EmrManagedSlaveSecurityGroup</code> - The security group ID of the Amazon EC2'
    ' security group for the slave nodes.</li>'
    '<li><code>ServiceAccessSecurityGroup</code> - The security group ID of the Amazon EC2 '
    'security group for Amazon EMR access to clusters in VPC private subnets.</li>'
    '<li><code>AdditionalMasterSecurityGroups</code> - A list of additional Amazon EC2'
    ' security group IDs for the master node.</li>'
    '<li><code>AdditionalSlaveSecurityGroups</code> - A list of additional Amazon EC2'
    ' security group IDs for the slave nodes.</li>')

AUTO_TERMINATE = (
    '<p>Specifies whether the cluster should terminate after'
    ' completing all the steps. Auto termination is off by default.</p>')

TERMINATION_PROTECTED = (
    '<p>Specifies whether to lock the cluster to prevent the'
    ' Amazon EC2 instances from being terminated by API call,'
    ' user intervention, or an error.</p>')

SCALE_DOWN_BEHAVIOR = (
    '<p>Specifies the way that individual Amazon EC2 instances terminate'
    ' when an automatic scale-in activity occurs or an instance group is resized.</p>'
    '<p>Accepted values:</p>'
    '<li><code>TERMINATE_AT_TASK_COMPLETION</code> - Specifies that Amazon EMR'
    ' blacklists and drains tasks from nodes before terminating the instance.</li>'
    '<li><code>TERMINATE_AT_INSTANCE_HOUR</code> - Specifies that Amazon EMR'
    ' terminate EC2 instances at the instance-hour boundary, regardless of when'
    ' the request to terminate was submitted.</li>'
)

VISIBILITY = (
    '<p>Specifies whether the cluster is visible to all IAM users'
    ' of the AWS account associated with the cluster. If a user'
    ' has the proper policy permissions set, they can also manage the cluster.</p>'
    '<p>Visibility is on by default. The <code>--no-visible-to-all-users</code> option'
    ' is no longer supported. To restrict cluster visibility, use an IAM policy.</p>')

DEBUGGING = (
    '<p>Specifies that the debugging tool is enabled for the cluster,'
    ' which allows you to browse log files using the Amazon EMR console.'
    ' Turning debugging on requires that you specify <code>--log-uri</code>'
    ' because log files must be stored in Amazon S3 so that'
    ' Amazon EMR can index them for viewing in the console.'
    ' Effective January 23, 2023, Amazon EMR will discontinue the debugging tool for all versions.</p>')

TAGS = (
    '<p>A list of tags to associate with a cluster, which apply to'
    ' each Amazon EC2 instance in the cluster. Tags are key-value pairs that'
    ' consist of a required key string'
    ' with a maximum of 128 characters, and an optional value string'
    ' with a maximum of 256 characters.</p>'
    '<p>You can specify tags in <code>key=value</code> format or you can add a'
    ' tag without a value using only the key name, for example <code>key</code>.'
    ' Use a space to separate multiple tags.</p>')

BOOTSTRAP_ACTIONS = (
    '<p>Specifies a list of bootstrap actions to run on each EC2 instance when'
    ' a cluster is created. Bootstrap actions run on each instance'
    ' immediately after Amazon EMR provisions the EC2 instance and'
    ' before Amazon EMR installs specified applications.</p>'
    '<p>You can specify a bootstrap action as an inline JSON structure'
    ' enclosed in single quotation marks, or you can use a shorthand'
    ' syntax, specifying multiple bootstrap actions, each separated'
    ' by a space. When using the shorthand syntax, each bootstrap'
    ' action takes the following parameters, separated by'
    ' commas with no trailing space. Optional parameters'
    ' are shown in [square brackets].</p>'
    '<li><code>Path</code> - The path and file name of the script'
    ' to run, which must be accessible to each instance in the cluster.'
    ' For example, <code>Path=s3://mybucket/myscript.sh</code>.</li>'
    '<li><code>[Name]</code> - A friendly name to help you identify'
    ' the bootstrap action. For example, <code>Name=BootstrapAction1</code></li>'
    '<li><code>[Args]</code> - A comma-separated list of arguments'
    ' to pass to the bootstrap action script. Arguments can be'
    ' either a list of values (<code>Args=arg1,arg2,arg3</code>)'
    ' or a list of key-value pairs, as well as optional values,'
    ' enclosed in square brackets (<code>Args=[arg1,arg2=arg2value,arg3])</li>.')

APPLICATIONS = (
    '<p>Specifies the applications to install on the cluster.'
    ' Available applications and their respective versions vary'
    ' by Amazon EMR release. For more information, see the'
    ' Amazon EMR Release Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ReleaseGuide/</p>'
    '<p>When using versions of Amazon EMR earlier than 4.0,'
    ' some applications take optional arguments for configuration.'
    ' Arguments should either be a comma-separated list of values'
    ' (<code>Args=arg1,arg2,arg3</code>) or a bracket-enclosed list of values'
    ' and key-value pairs (<code>Args=[arg1,arg2=arg3,arg4]</code>).</p>')

EMR_FS = (
    '<p>Specifies EMRFS configuration options, such as consistent view'
    ' and Amazon S3 encryption parameters.</p>'
    '<p>When you use Amazon EMR release version 4.8.0 or later, we recommend'
    ' that you use the <code>--configurations</code> option together'
    ' with the <code>emrfs-site</code> configuration classification'
    ' to configure EMRFS, and use security configurations'
    ' to configure encryption for EMRFS data in Amazon S3 instead.'
    ' For more information, see the following topic in the Amazon EMR Management Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ManagementGuide/emrfs-configure-consistent-view.html</p>')

RESTORE_FROM_HBASE = (
    '<p>Applies only when using Amazon EMR release versions earlier than 4.0.'
    ' Launches a new HBase cluster and populates it with'
    ' data from a previous backup of an HBase cluster. HBase'
    ' must be installed using the <code>--applications</code> option.</p>')

STEPS = (
    '<p>Specifies a list of steps to be executed by the cluster. Steps run'
    ' only on the master node after applications are installed'
    ' and are used to submit work to a cluster. A step can be'
    ' specified using the shorthand syntax, by referencing a JSON file'
    ' or by specifying an inline JSON structure. <code>Args</code> supplied with steps'
    ' should be a comma-separated list of values (<code>Args=arg1,arg2,arg3</code>) or'
    ' a bracket-enclosed list of values and key-value'
    ' pairs (<code>Args=[arg1,arg2=value,arg4</code>).</p>')

INSTALL_APPLICATIONS = (
    '<p>The applications to be installed.'
    ' Takes the following parameters: '
    '<code>Name</code> and <code>Args</code>.</p>')

EBS_ROOT_VOLUME_SIZE = (
    '<p>This option is available only with Amazon EMR version 4.x and later. Specifies the size,'
    ' in GiB, of the EBS root device volume of the Amazon Linux AMI'
    ' that is used for each EC2 instance in the cluster. </p>')

SECURITY_CONFIG = (
    '<p>Specifies the name of a security configuration to use for the cluster.'
    ' A security configuration defines data encryption settings and'
    ' other security options. For more information, see'
    ' the following topic in the Amazon EMR Management Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-encryption-enable-security-configuration.html</p>'
    '<p>Use <code>list-security-configurations</code> to get a list of available'
    ' security configurations in the active account.</p>')

CUSTOM_AMI_ID = (
    '<p>Applies only to Amazon EMR release version 5.7.0 and later.'
    ' Specifies the AMI ID of a custom AMI to use'
    ' when Amazon EMR provisions EC2 instances. A custom'
    ' AMI can be used to encrypt the Amazon EBS root volume. It'
    ' can also be used instead of bootstrap actions to customize'
    ' cluster node configurations. For more information, see'
    ' the following topic in the Amazon EMR Management Guide:</p>'
    '<p>https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-custom-ami.html</p>')

REPO_UPGRADE_ON_BOOT = (
    '<p>Applies only when a <code>--custom-ami-id</code> is'
    ' specified. On first boot, by default, Amazon Linux AMIs'
    ' connect to package repositories to install security updates'
    ' before other services start. You can set this parameter'
    ' using <code>--rep-upgrade-on-boot NONE</code> to'
    ' disable these updates. CAUTION: This creates additional'
    ' security risks.</p>')

KERBEROS_ATTRIBUTES = (
     '<p>Specifies required cluster attributes for Kerberos when Kerberos authentication'
     ' is enabled in the specified <code>--security-configuration</code>.'
     ' Takes the following arguments:</p>'
     ' <li><code>Realm</code> - Specifies the name of the Kerberos'
     ' realm to which all nodes in a cluster belong. For example,'
     ' <code>Realm=EC2.INTERNAL</code>.</li>'
     ' <li><code>KdcAdminPassword</code> - Specifies the password used within the cluster'
     ' for the kadmin service, which maintains Kerberos principals, password'
     ' policies, and keytabs for the cluster.</li>'
     ' <li><code>CrossRealmTrustPrincipalPassword</code> - Required when establishing a cross-realm trust'
     ' with a KDC in a different realm. This is the cross-realm principal password,'
     ' which must be identical across realms.</li>'
     ' <li><code>ADDomainJoinUser</code> - Required when establishing trust with an Active Directory'
     ' domain. This is the User logon name of an AD account with sufficient privileges to join resources to the domain.</li>'
     ' <li><code>ADDomainJoinPassword</code> - The AD password for <code>ADDomainJoinUser</code>.</li>')

# end create-cluster options help descriptions

LIST_CLUSTERS_CLUSTER_STATES = (
    '<p>Specifies that only clusters in the states specified are'
    ' listed. Alternatively, you can use the shorthand'
    ' form for single states or a group of states.</p>'
    '<p>Takes the following state values:</p>'
    '<li><code>STARTING</code></li>'
    '<li><code>BOOTSTRAPPING</code></li>'
    '<li><code>RUNNING</code></li>'
    '<li><code>WAITING</code></li>'
    '<li><code>TERMINATING</code></li>'
    '<li><code>TERMINATED</code></li>'
    '<li><code>TERMINATED_WITH_ERRORS</code></li>')

LIST_CLUSTERS_STATE_FILTERS = (
    '<p>Shortcut options for --cluster-states. The'
    ' following shortcut options can be specified:</p>'
    '<li><code>--active</code> - list only clusters that'
    ' are <code>STARTING</code>,<code>BOOTSTRAPPING</code>,'
    ' <code>RUNNING</code>, <code>WAITING</code>, or <code>TERMINATING</code>. </li>'
    '<li><code>--terminated</code> - list only clusters that are <code>TERMINATED</code>. </li>'
    '<li><code>--failed</code> - list only clusters that are <code>TERMINATED_WITH_ERRORS</code>.</li>')

LIST_CLUSTERS_CREATED_AFTER = (
    '<p>List only those clusters created after the date and time'
    ' specified in the format yyyy-mm-ddThh:mm:ss. For example,'
    ' <code>--created-after 2017-07-04T00:01:30.</p>')

LIST_CLUSTERS_CREATED_BEFORE = (
    '<p>List only those clusters created before the date and time'
    ' specified in the format yyyy-mm-ddThh:mm:ss. For example,'
    ' <code>--created-before 2017-07-04T00:01:30.</p>')

EMR_MANAGED_MASTER_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for the master node.</p>')

EMR_MANAGED_SLAVE_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for the slave nodes.</p>')

SERVICE_ACCESS_SECURITY_GROUP = (
    '<p>The identifier of the Amazon EC2 security group '
    'for Amazon EMR to access clusters in VPC private subnets.</p>')

ADDITIONAL_MASTER_SECURITY_GROUPS = (
    '<p> A list of additional Amazon EC2 security group IDs for '
    'the master node</p>')

ADDITIONAL_SLAVE_SECURITY_GROUPS = (
    '<p>A list of additional Amazon EC2 security group IDs for '
    'the slave nodes.</p>')

AVAILABLE_ONLY_FOR_AMI_VERSIONS = (
    'This command is only available when using Amazon EMR versions'
    'earlier than 4.0.')

STEP_CONCURRENCY_LEVEL = (
    'This command specifies the step concurrency level of the cluster.'
    'Default is 1 which is non-concurrent.'
)

MANAGED_SCALING_POLICY = (
    '<p>Managed scaling policy for an Amazon EMR cluster. The policy '
    'specifies the limits for resources that can be added or terminated '
    'from a cluster. You can specify the ComputeLimits which include '
    'the MaximumCapacityUnits, MaximumCoreCapacityUnits, MinimumCapacityUnits, '
    'MaximumOnDemandCapacityUnits and UnitType. For an '
    'InstanceFleet cluster, the UnitType must be InstanceFleetUnits. For '
    'InstanceGroup clusters, the UnitType can be either VCPU or Instances.</p>'
)

PLACEMENT_GROUP_CONFIGS = (
    '<p>Placement group configuration for an Amazon EMR ' 
    'cluster. The configuration specifies the EC2 placement group ' 
    'strategy associated with each EMR Instance Role.</p> ' 
    '<p>Currently, we support placement group only for <code>MASTER</code> ' 
    'role with <code>SPREAD</code> strategy by default. You can opt-in by '
    'passing <code>--placement-group-configs InstanceRole=MASTER</code> '
    'during cluster creation.</p>'
)

AUTO_TERMINATION_POLICY = (
    '<p>Auto termination policy for an Amazon EMR cluster. '
    'The configuration specifies the termination idle timeout'
    'threshold for an cluster.</p> '
)

EXECUTION_ROLE_ARN = (
    '<p>You must grant the execution role the permissions needed '
    'to access the same IAM resources that the step can access. '
    'The execution role can be a cross-account IAM Role.</p> '
)
