=========
CHANGELOG
=========

1.27.114
========

* api-change:``ecs``: This release supports  ephemeral storage for AWS Fargate Windows containers.
* api-change:``lambda``: This release adds SnapStart related exceptions to InvokeWithResponseStream API. IAM access related documentation is also added for this API.
* api-change:``migration-hub-refactor-spaces``: Doc only update for Refactor Spaces environments without network bridge feature.
* api-change:``rds``: This release adds support of modifying the engine mode of database clusters.


1.27.113
========

* api-change:``chime-sdk-voice``: This release adds tagging support for Voice Connectors and SIP Media Applications
* api-change:``mediaconnect``: Gateway is a new feature of AWS Elemental MediaConnect. Gateway allows the deployment of on-premises resources for the purpose of transporting live video to and from the AWS Cloud.


1.27.112
========

* api-change:``groundstation``: AWS Ground Station Wideband DigIF GA Release
* api-change:``managedblockchain``: Removal of the Ropsten network. The Ethereum foundation ceased support of Ropsten on December 31st, 2022..


1.27.111
========

* api-change:``ecr-public``: This release will allow using registry alias as registryId in BatchDeleteImage request.
* api-change:``emr-serverless``: This release extends GetJobRun API to return job run timeout (executionTimeoutMinutes) specified during StartJobRun call (or default timeout of 720 minutes if none was specified).
* api-change:``events``: Update events command to latest version
* api-change:``iot-data``: This release adds support for MQTT5 user properties when calling the AWS IoT GetRetainedMessage API
* api-change:``wafv2``: For web ACLs that protect CloudFront protections, the default request body inspection size is now 16 KB, and you can use the new association configuration to increase the inspection size further, up to 64 KB. Sizes over 16 KB can incur additional costs.


1.27.110
========

* api-change:``connect``: This release adds the ability to configure an agent's routing profile to receive contacts from multiple channels at the same time via extending the UpdateRoutingProfileConcurrency, CreateRoutingProfile and DescribeRoutingProfile APIs.
* api-change:``ecs``: This release adds support for enabling FIPS compliance on Amazon ECS Fargate tasks
* api-change:``marketplace-catalog``: Added three new APIs to support resource sharing: GetResourcePolicy, PutResourcePolicy, and DeleteResourcePolicy. Added new OwnershipType field to ListEntities request to let users filter on entities that are shared with them. Increased max page size of ListEntities response from 20 to 50 results.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK now supports conversion of 608 paint-on captions to pop-on captions for SCC sources.
* api-change:``omics``: Remove unexpected API changes.
* api-change:``rekognition``: This release adds support for Face Liveness APIs in Amazon Rekognition. Updates UpdateStreamProcessor to return ResourceInUseException Exception. Minor updates to API documentation.


1.27.109
========

* api-change:``dlm``: Updated timestamp format for GetLifecyclePolicy API
* api-change:``docdb``: This release adds a new parameter 'DBClusterParameterGroupName' to 'RestoreDBClusterFromSnapshot' API to associate the name of the DB cluster parameter group while performing restore.
* api-change:``fsx``: Amazon FSx for Lustre now supports creating data repository associations on Persistent_1 and Scratch_2 file systems.
* api-change:``lambda``: This release adds a new Lambda InvokeWithResponseStream API to support streaming Lambda function responses. The release also adds a new InvokeMode parameter to Function Url APIs to control whether the response will be streamed or buffered.
* api-change:``quicksight``: This release has two changes: adding the OR condition to tag-based RLS rules in CreateDataSet and UpdateDataSet; adding RefreshSchedule and Incremental RefreshProperties operations for users to programmatically configure SPICE dataset ingestions.
* api-change:``redshift-data``: Update documentation of API descriptions as needed in support of temporary credentials with IAM identity.
* api-change:``servicecatalog``: Updates description for property


1.27.108
========

* api-change:``cloudformation``: Including UPDATE_COMPLETE as a failed status for DeleteStack waiter.
* api-change:``greengrassv2``: Add support for SUCCEEDED value in coreDeviceExecutionStatus field. Documentation updates for Greengrass V2.
* api-change:``proton``: This release adds support for the AWS Proton service sync feature. Service sync enables managing an AWS Proton service (creating and updating instances) and all of it's corresponding service instances from a Git repository.
* api-change:``rds``: Adds and updates the SDK examples


1.27.107
========

* bugfix:eks: Fix eks kubeconfig validations closes `#6564 <https://github.com/aws/aws-cli/issues/6564>`__, fixes `#4843 <https://github.com/aws/aws-cli/issues/4843>`__, fixes `#5532 <https://github.com/aws/aws-cli/issues/5532>`__
* api-change:``apprunner``: App Runner adds support for seven new vCPU and memory configurations.
* api-change:``config``: This release adds resourceType enums for types released in March 2023.
* api-change:``ecs``: This is a document only updated to add information about Amazon Elastic Inference (EI).
* api-change:``identitystore``: Documentation updates for Identity Store CLI command reference.
* api-change:``ivs-realtime``: Fix ParticipantToken ExpirationTime format
* api-change:``network-firewall``: AWS Network Firewall now supports IPv6-only subnets.
* api-change:``servicecatalog``: removed incorrect product type value
* api-change:``vpc-lattice``: This release removes the entities in the API doc model package for auth policies.


1.27.106
========

* api-change:``amplifyuibuilder``: Support StorageField and custom displays for data-bound options in form builder. Support non-string operands for predicates in collections. Support choosing client to get token from.
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling
* api-change:``dataexchange``: This release updates the value of MaxResults.
* api-change:``ec2``: C6in, M6in, M6idn, R6in and R6idn bare metal instances are powered by 3rd Generation Intel Xeon Scalable processors and offer up to 200 Gbps of network bandwidth.
* api-change:``elastic-inference``: Updated public documentation for the Describe and Tagging APIs.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: Amazon SageMaker Asynchronous Inference now allows customer's to receive failure model responses in S3 and receive success/failure model responses in SNS notifications.
* api-change:``wafv2``: This release rolls back association config feature for webACLs that protect CloudFront protections.


1.27.105
========

* api-change:``glue``: Add support for database-level federation
* api-change:``lakeformation``: Add support for database-level federation
* api-change:``license-manager``: This release adds grant override options to the CreateGrantVersion API. These options can be used to specify grant replacement behavior during grant activation.
* api-change:``mwaa``: This Amazon MWAA release adds the ability to customize the Apache Airflow environment by launching a shell script at startup. This shell script is hosted in your environment's Amazon S3 bucket. Amazon MWAA runs the script before installing requirements and initializing the Apache Airflow process.
* api-change:``servicecatalog``: This release introduces Service Catalog support for Terraform open source. It enables 1. The notify* APIs to Service Catalog. These APIs are used by the terraform engine to notify the result of the provisioning engine execution. 2. Adds a new TERRAFORM_OPEN_SOURCE product type in CreateProduct API.
* api-change:``wafv2``: For web ACLs that protect CloudFront protections, the default request body inspection size is now 16 KB, and you can use the new association configuration to increase the inspection size further, up to 64 KB. Sizes over 16 KB can incur additional costs.


1.27.104
========

* api-change:``ec2``: Documentation updates for EC2 On Demand Capacity Reservations
* api-change:``internetmonitor``: This release adds a new feature for Amazon CloudWatch Internet Monitor that enables customers to deliver internet measurements to Amazon S3 buckets as well as CloudWatch Logs.
* api-change:``resiliencehub``: Adding EKS related documentation for appTemplateBody
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``sagemaker-featurestore-runtime``: In this release, you can now chose between soft delete and hard delete when calling the DeleteRecord API, so you have more flexibility when it comes to managing online store data.
* api-change:``sms``: Deprecating AWS Server Migration Service.


1.27.103
========

* api-change:``athena``: Make DefaultExecutorDpuSize and CoordinatorDpuSize  fields optional  in StartSession
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now supports Elastic Load Balancing traffic sources with the AttachTrafficSources, DetachTrafficSources, and DescribeTrafficSources APIs. This release also introduces a new activity status, "WaitingForConnectionDraining", for VPC Lattice to the DescribeScalingActivities API.
* api-change:``batch``: This feature allows Batch on EKS to support configuration of Pod Labels through Metadata for Batch on EKS Jobs.
* api-change:``compute-optimizer``: This release adds support for HDD EBS volume types and io2 Block Express. We are also adding support for 61 new instance types and instances that have non consecutive runtime.
* api-change:``drs``: Adding a field to the replication configuration APIs to support the auto replicate new disks feature. We also deprecated RetryDataReplication.
* api-change:``ec2``: This release adds support for Tunnel Endpoint Lifecycle control, a new feature that provides Site-to-Site VPN customers with better visibility and control of their VPN tunnel maintenance updates.
* api-change:``emr``: Update emr command to latest version
* api-change:``glue``: This release adds support for AWS Glue Data Quality, which helps you evaluate and monitor the quality of your data and includes the API for creating, deleting, or updating data quality rulesets, runs and evaluations.
* api-change:``guardduty``: Added EKS Runtime Monitoring feature support to existing detector, finding APIs and introducing new Coverage APIs
* api-change:``imagebuilder``: Adds support for new image workflow details and image vulnerability detection.
* api-change:``ivs``: Amazon Interactive Video Service (IVS) now offers customers the ability to configure IVS channels to allow insecure RTMP ingest.
* api-change:``kendra``: AWS Kendra now supports featured results for a query.
* api-change:``network-firewall``: AWS Network Firewall added TLS inspection configurations to allow TLS traffic inspection.
* api-change:``sagemaker-geospatial``: Amazon SageMaker geospatial capabilities now supports server-side encryption with customer managed KMS key and SageMaker notebooks with a SageMaker geospatial image in a Amazon SageMaker Domain with VPC only mode.
* api-change:``vpc-lattice``: General Availability (GA) release of Amazon VPC Lattice
* api-change:``wellarchitected``: AWS Well-Architected SDK now supports getting consolidated report metrics and generating a consolidated report PDF.


1.27.102
========

* api-change:``opensearchserverless``: This release includes two new exception types "ServiceQuotaExceededException" and "OcuLimitExceededException".
* api-change:``rds``: Add support for creating a read replica DB instance from a Multi-AZ DB cluster.


1.27.101
========

* api-change:``iot-data``: Add endpoint ruleset support for cn-north-1.
* api-change:``ssm-contacts``: This release adds 12 new APIs as part of Oncall Schedule feature release, adds support for a new contact type: ONCALL_SCHEDULE. Check public documentation for AWS ssm-contacts for more information
* api-change:``ssm-incidents``: Increased maximum length of "TriggerDetails.rawData" to 10K characters and "IncidentSummary" to 8K characters.


1.27.100
========

* api-change:``athena``: Enforces a minimal level of encryption for the workgroup for query and calculation results that are written to Amazon S3. When enabled, workgroup users can set encryption only to the minimum level set by the administrator or higher when they submit queries.
* api-change:``chime-sdk-voice``: Documentation updates for Amazon Chime SDK Voice.
* api-change:``connect``: This release introduces support for RelatedContactId in the StartChatContact API. Interactive message and interactive message response have been added to the list of supported message content types for this API as well.
* api-change:``connectparticipant``: This release provides an update to the SendMessage API to handle interactive message response content-types.
* api-change:``iotwireless``: Introducing new APIs that enable Sidewalk devices to communicate with AWS IoT Core through Sidewalk gateways. This will empower AWS customers to connect Sidewalk devices with other AWS IoT Services, creating  possibilities for seamless integration and advanced device management.
* api-change:``medialive``: AWS Elemental MediaLive now supports ID3 tag insertion for audio only HLS output groups. AWS Elemental Link devices now support tagging.
* api-change:``sagemaker``: Fixed some improperly rendered links in SDK documentation.
* api-change:``securityhub``: Added new resource detail objects to ASFF, including resources for AwsEksCluster, AWSS3Bucket, AwsEc2RouteTable and AwsEC2Instance.
* api-change:``servicecatalog-appregistry``: In this release, we started supporting ARN in applicationSpecifier and attributeGroupSpecifier. GetAttributeGroup, ListAttributeGroups and ListAttributeGroupsForApplication APIs will now have CreatedBy field in the response.
* api-change:``voice-id``: Amazon Connect Voice ID now supports multiple fraudster watchlists. Every domain has a default watchlist where all existing fraudsters are placed by default. Custom watchlists may now be created, managed, and evaluated against for known fraudster detection.


1.27.99
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``comprehend``: This release adds a new field (FlywheelArn) to the EntitiesDetectionJobProperties object. The FlywheelArn field is returned in the DescribeEntitiesDetectionJob and ListEntitiesDetectionJobs responses when the EntitiesDetection job is started with a FlywheelArn instead of an EntityRecognizerArn .
* api-change:``rds``: Added error code CreateCustomDBEngineVersionFault for when the create custom engine version for Custom engines fails.


1.27.98
=======

* enhancement:eks: Add user-alias argument to update-kubeconfig command. Implements `#5164 <https://github.com/aws/aws-cli/issues/5164>`__
* api-change:``batch``: This feature allows Batch to support configuration of ephemeral storage size for jobs running on FARGATE
* api-change:``chime-sdk-identity``: AppInstanceBots can be used to add a bot powered by Amazon Lex to chat channels.  ExpirationSettings provides automatic resource deletion for AppInstanceUsers.
* api-change:``chime-sdk-media-pipelines``: This release adds Amazon Chime SDK call analytics. Call analytics include voice analytics, which provides speaker search and voice tone analysis. These capabilities can be used with Amazon Transcribe and Transcribe Call Analytics to generate machine-learning-powered insights from real-time audio.
* api-change:``chime-sdk-messaging``: ExpirationSettings provides automatic resource deletion for Channels.
* api-change:``chime-sdk-voice``: This release adds Amazon Chime SDK call analytics. Call analytics include voice analytics, which provides speaker search and voice tone analysis. These capabilities can be used with Amazon Transcribe and Transcribe Call Analytics to generate machine-learning-powered insights from real-time audio.
* api-change:``codeartifact``: Repository CreationTime is added to the CreateRepository and ListRepositories API responses.
* api-change:``guardduty``: Adds AutoEnableOrganizationMembers attribute to DescribeOrganizationConfiguration and UpdateOrganizationConfiguration APIs.
* api-change:``ivs-realtime``: Initial release of the Amazon Interactive Video Service RealTime API.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK now supports passthrough of ID3v2 tags for audio inputs to audio-only HLS outputs.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds two new APIs - CreateAutoMLJobV2 and DescribeAutoMLJobV2. Amazon SageMaker Notebook Instances now supports the ml.geospatial.interactive instance type.
* api-change:``servicediscovery``: Reverted the throttling exception RequestLimitExceeded for AWS Cloud Map APIs introduced in SDK version 1.12.424 2023-03-09 to previous exception specified in the ErrorCode.
* api-change:``textract``: The AnalyzeDocument - Tables feature adds support for new elements in the API: table titles, footers, section titles, summary cells/tables, and table type.


1.27.97
=======

* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``iottwinmaker``: This release adds support of adding metadata when creating a new scene or updating an existing scene.
* api-change:``networkmanager``: This release includes an update to create-transit-gateway-route-table-attachment, showing example usage for TransitGatewayRouteTableArn.
* api-change:``pipes``: This release improves validation on the ARNs in the API model
* api-change:``resiliencehub``: This release provides customers with the ability to import resources from within an EKS cluster and assess the resiliency of EKS cluster workloads.
* api-change:``ssm``: This Patch Manager release supports creating, updating, and deleting Patch Baselines for AmazonLinux2023, AlmaLinux.


1.27.96
=======

* api-change:``chime-sdk-messaging``: Amazon Chime SDK messaging customers can now manage streaming configuration for messaging data for archival and analysis.
* api-change:``cleanrooms``: GA Release of AWS Clean Rooms, Added Tagging Functionality
* api-change:``ec2``: This release adds support for AWS Network Firewall, AWS PrivateLink, and Gateway Load Balancers to Amazon VPC Reachability Analyzer, and it makes the path destination optional as long as a destination address in the filter at source is provided.
* api-change:``iotsitewise``: Provide support for tagging of data streams and enabling tag based authorization for property alias
* api-change:``mgn``: This release introduces the Import and export feature and expansion of the post-launch actions


1.27.95
=======

* api-change:``application-autoscaling``: With this release customers can now tag their Application Auto Scaling registered targets with key-value pairs and manage IAM permissions for all the tagged resources centrally.
* api-change:``neptune``: This release makes following few changes. db-cluster-identifier is now a required parameter of create-db-instance. describe-db-cluster will now return PendingModifiedValues and GlobalClusterIdentifier fields in the response.
* api-change:``s3outposts``: S3 On Outposts added support for endpoint status, and a failed endpoint reason, if any
* api-change:``workdocs``: This release adds a new API, SearchResources, which enable users to search through metadata and content of folders, documents, document versions and comments in a WorkDocs site.


1.27.94
=======

* api-change:``billingconductor``: This release adds a new filter to ListAccountAssociations API and a new filter to ListBillingGroups API.
* api-change:``config``: This release adds resourceType enums for types released from October 2022 through February 2023.
* api-change:``dms``: S3 setting to create AWS Glue Data Catalog. Oracle setting to control conversion of timestamp column. Support for Kafka SASL Plain authentication. Setting to map boolean from PostgreSQL to Redshift. SQL Server settings to force lob lookup on inline LOBs and to control access of database logs.


1.27.93
=======

* api-change:``guardduty``: Updated 9 APIs for feature enablement to reflect expansion of GuardDuty to features. Added new APIs and updated existing APIs to support RDS Protection GA.
* api-change:``resource-explorer-2``: Documentation updates for APIs.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version


1.27.92
=======

* api-change:``migrationhubstrategy``: This release adds the binary analysis that analyzes IIS application DLLs on Windows and Java applications on Linux to provide anti-pattern report without configuring access to the source code.
* api-change:``s3control``: Added support for S3 Object Lambda aliases.
* api-change:``securitylake``: Make Create/Get/ListSubscribers APIs return resource share ARN and name so they can be used to validate the RAM resource share to accept. GetDatalake can be used to track status of UpdateDatalake and DeleteDatalake requests.


1.27.91
=======

* api-change:``application-autoscaling``: Application Auto Scaling customers can now use mathematical functions to customize the metric used with Target Tracking policies within the policy configuration itself, saving the cost and effort of publishing the customizations as a separate metric.
* api-change:``dataexchange``: This release enables data providers to license direct access to S3 objects encrypted with Customer Managed Keys (CMK) in AWS KMS through AWS Data Exchange. Subscribers can use these keys to decrypt, then use the encrypted S3 objects shared with them, without creating or managing copies.
* api-change:``directconnect``: describe-direct-connect-gateway-associations includes a new status, updating, indicating that the association is currently in-process of updating.
* api-change:``ec2``: This release adds a new DnsOptions key (PrivateDnsOnlyForInboundResolverEndpoint) to CreateVpcEndpoint and ModifyVpcEndpoint APIs.
* api-change:``iam``: Documentation only updates to correct customer-reported issues
* api-change:``keyspaces``: Adding support for client-side timestamps


1.27.90
=======

* bugfix:``codeartifact login``: Prevent AWS CodeArtifact login command from hanging unexpectedly.
* api-change:``appintegrations``: Adds FileConfiguration to Amazon AppIntegrations CreateDataIntegration supporting scheduled downloading of third party files into Amazon Connect from sources such as Microsoft SharePoint.
* api-change:``lakeformation``: This release updates the documentation regarding Get/Update DataCellsFilter
* api-change:``s3control``: Added support for cross-account Multi-Region Access Points. Added support for S3 Replication for S3 on Outposts.
* api-change:``tnb``: This release adds tagging support to the following Network Instance APIs : Instantiate, Update, Terminate.
* api-change:``wisdom``: This release extends Wisdom CreateKnowledgeBase API to support SharePoint connector type by removing the @required trait for objectField


1.27.89
=======

* api-change:``ivschat``: This release adds a new exception returned when calling AWS IVS chat UpdateLoggingConfiguration. Now UpdateLoggingConfiguration can return ConflictException when invalid updates are made in sequence to Logging Configurations.
* api-change:``secretsmanager``: The type definitions of SecretString and SecretBinary now have a minimum length of 1 in the model to match the exception thrown when you pass in empty values.


1.27.88
=======

* api-change:``codeartifact``: This release introduces the generic package format, a mechanism for storing arbitrary binary assets. It also adds a new API, PublishPackageVersion, to allow for publishing generic packages.
* api-change:``connect``: This release adds a new API, GetMetricDataV2, which returns metric data for Amazon Connect.
* api-change:``evidently``: Updated entity override documentation
* api-change:``networkmanager``: This update provides example usage for TransitGatewayRouteTableArn.
* api-change:``quicksight``: This release has two changes: add state persistence feature for embedded dashboard and console in GenerateEmbedUrlForRegisteredUser API; add properties for hidden collapsed row dimensions in PivotTableOptions.
* api-change:``redshift-data``: Added support for Redshift Serverless workgroup-arn wherever the WorkgroupName parameter is available.
* api-change:``sagemaker``: Amazon SageMaker Inference now allows SSM access to customer's model container by setting the "EnableSSMAccess" parameter for a ProductionVariant in CreateEndpointConfig API.
* api-change:``servicediscovery``: Updated all AWS Cloud Map APIs to provide consistent throttling exception (RequestLimitExceeded)
* api-change:``sesv2``: This release introduces a new recommendation in Virtual Deliverability Manager Advisor, which detects missing or misconfigured Brand Indicator for Message Identification (BIMI) DNS records for customer sending identities.


1.27.87
=======

* api-change:``athena``: A new field SubstatementType is added to GetQueryExecution API, so customers have an error free way to detect the query type and interpret the result.
* api-change:``dynamodb``: Adds deletion protection support to DynamoDB tables. Tables with deletion protection enabled cannot be deleted. Deletion protection is disabled by default, can be enabled via the CreateTable or UpdateTable APIs, and is visible in TableDescription. This setting is not replicated for Global Tables.
* api-change:``ec2``: Introducing Amazon EC2 C7g, M7g and R7g instances, powered by the latest generation AWS Graviton3 processors and deliver up to 25% better performance over Graviton2-based instances.
* api-change:``lakeformation``: This release adds two new API support "GetDataCellsFiler" and "UpdateDataCellsFilter", and also updates the corresponding documentation.
* api-change:``mediapackage-vod``: This release provides the date and time VOD resources were created.
* api-change:``mediapackage``: This release provides the date and time live resources were created.
* api-change:``route53resolver``: Add dual-stack and IPv6 support for Route 53 Resolver Endpoint,Add IPv6 target IP in Route 53 Resolver Forwarding Rule
* api-change:``sagemaker``: There needs to be a user identity to specify the SageMaker user who perform each action regarding the entity. However, these is a not a unified concept of user identity across SageMaker service that could be used today.


1.27.86
=======

* bugfix:eks: Output JSON only for user entry in kubeconfig fixes `#7719 <https://github.com/aws/aws-cli/issues/7719>`__, fixes `#7723 <https://github.com/aws/aws-cli/issues/7723>`__, fixes `#7724 <https://github.com/aws/aws-cli/issues/7724>`__
* api-change:``dms``: This release adds DMS Fleet Advisor Target Recommendation APIs and exposes functionality for DMS Fleet Advisor. It adds functionality to start Target Recommendation calculation.
* api-change:``location``: Documentation update for the release of 3 additional map styles for use with Open Data Maps: Open Data Standard Dark, Open Data Visualization Light & Open Data Visualization Dark.


1.27.85
=======

* api-change:``account``: AWS Account alternate contact email addresses can now have a length of 254 characters and contain the character "|".
* api-change:``ivs``: Updated text description in DeleteChannel, Stream, and StreamSummary.


1.27.84
=======

* api-change:``dynamodb``: Documentation updates for DynamoDB.
* api-change:``ec2``: This release adds support for a new boot mode for EC2 instances called 'UEFI Preferred'.
* api-change:``macie2``: Documentation updates for Amazon Macie
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has improved handling for different input and output color space combinations.
* api-change:``medialive``: AWS Elemental MediaLive adds support for Nielsen watermark timezones.
* api-change:``transcribe``: Amazon Transcribe now supports role access for these API operations: CreateVocabulary, UpdateVocabulary, CreateVocabularyFilter, and UpdateVocabularyFilter.


1.27.83
=======

* api-change:``iot``: A recurring maintenance window is an optional configuration used for rolling out the job document to all devices in the target group observing a predetermined start time, duration, and frequency that the maintenance window occurs.
* api-change:``migrationhubstrategy``: This release updates the File Import API to allow importing servers already discovered by customers with reduced pre-requisites.
* api-change:``organizations``: This release introduces a new reason code, ACCOUNT_CREATION_NOT_COMPLETE, to ConstraintViolationException in CreateOrganization API.
* api-change:``pi``: This release adds a new field PeriodAlignment to allow the customer specifying the returned timestamp of time periods to be either the start or end time.
* api-change:``pipes``: This release fixes some input parameter range and patterns.
* api-change:``sagemaker``: Add a new field "EndpointMetrics" in SageMaker Inference Recommender "ListInferenceRecommendationsJobSteps" API response.


1.27.82
=======

* api-change:``codecatalyst``: Published Dev Environments StopDevEnvironmentSession API
* api-change:``pricing``: This release adds 2 new APIs - ListPriceLists which returns a list of applicable price lists, and GetPriceListFileUrl which outputs a URL to retrieve your price lists from the generated file from ListPriceLists
* api-change:``s3outposts``: S3 on Outposts introduces a new API ListOutpostsWithS3, with this API you can list all your Outposts with S3 capacity.


1.27.81
=======

* api-change:``comprehend``: Amazon Comprehend now supports flywheels to help you train and manage new model versions for custom models.
* api-change:``ec2``: This release allows IMDS support to be set to v2-only on an existing AMI, so that all future instances launched from that AMI will use IMDSv2 by default.
* api-change:``kms``: AWS KMS is deprecating the RSAES_PKCS1_V1_5 wrapping algorithm option in the GetParametersForImport API that is used in the AWS KMS Import Key Material feature. AWS KMS will end support for this wrapping algorithm by October 1, 2023.
* api-change:``lightsail``: This release adds Lightsail for Research feature support, such as GUI session access, cost estimates, stop instance on idle, and disk auto mount.
* api-change:``managedblockchain``: This release adds support for tagging to the accessor resource in Amazon Managed Blockchain
* api-change:``omics``: Minor model changes to accomodate batch imports feature


1.27.80
=======

* api-change:``devops-guru``: This release adds the description field on ListAnomaliesForInsight and DescribeAnomaly API responses for proactive anomalies.
* api-change:``drs``: New fields were added to reflect availability zone data in source server and recovery instance description commands responses, as well as source server launch status.
* api-change:``internetmonitor``: CloudWatch Internet Monitor is a a new service within CloudWatch that will help application developers and network engineers continuously monitor internet performance metrics such as availability and performance between their AWS-hosted applications and end-users of these applications
* api-change:``lambda``: This release adds the ability to create ESMs with Document DB change streams as event source. For more information see  https://docs.aws.amazon.com/lambda/latest/dg/with-documentdb.html.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for HDR10 to SDR tone mapping, and animated GIF video input sources.
* api-change:``timestream-write``: This release adds the ability to ingest batched historical data or migrate data in bulk from S3 into Timestream using CSV files.


1.27.79
=======

* api-change:``connect``: StartTaskContact API now supports linked task creation with a new optional RelatedContactId parameter
* api-change:``connectcases``: This release adds the ability to delete domains through the DeleteDomain API. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``redshift``: Documentation updates for Redshift API bringing it in line with IAM best practices.
* api-change:``securityhub``: New Security Hub APIs and updates to existing APIs that help you consolidate control findings and enable and disable controls across all supported standards
* api-change:``servicecatalog``: Documentation updates for Service Catalog


1.27.78
=======

* api-change:``appflow``: This release enables the customers to choose whether to use Private Link for Metadata and Authorization call when using a private Salesforce connections
* api-change:``ecs``: This release supports deleting Amazon ECS task definitions that are in the INACTIVE state.
* api-change:``grafana``: Doc-only update. Updated information on attached role policies for customer provided roles
* api-change:``guardduty``: Updated API and data types descriptions for CreateFilter, UpdateFilter, and TriggerDetails.
* api-change:``iotwireless``: In this release, we add additional capabilities for the FUOTA which allows user to configure the fragment size, the sending interval and the redundancy ratio of the FUOTA tasks
* api-change:``location``: This release adds support for using Maps APIs with an API Key in addition to AWS Cognito. This includes support for adding, listing, updating and deleting API Keys.
* api-change:``macie2``: This release adds support for a new finding type, Policy:IAMUser/S3BucketSharedWithCloudFront, and S3 bucket metadata that indicates if a bucket is shared with an Amazon CloudFront OAI or OAC.
* api-change:``wafv2``: You can now associate an AWS WAF v2 web ACL with an AWS App Runner service.


1.27.77
=======

* api-change:``chime-sdk-voice``: This release introduces support for Voice Connector media metrics in the Amazon Chime SDK Voice namespace
* api-change:``cloudfront``: CloudFront now supports block lists in origin request policies so that you can forward all headers, cookies, or query string from viewer requests to the origin *except* for those specified in the block list.
* api-change:``datasync``: AWS DataSync has relaxed the minimum length constraint of AccessKey for Object Storage locations to 1.
* api-change:``opensearch``: This release lets customers configure Off-peak window and software update related properties for a new/existing domain. It enhances the capabilities of StartServiceSoftwareUpdate API; adds 2 new APIs - ListScheduledActions & UpdateScheduledAction; and allows Auto-tune to make use of Off-peak window.
* api-change:``rum``: CloudWatch RUM now supports CloudWatch Custom Metrics
* api-change:``ssm``: Document only update for Feb 2023


1.27.76
=======

* api-change:``quicksight``: S3 data sources now accept a custom IAM role.
* api-change:``resiliencehub``: In this release we improved resilience hub application creation and maintenance by introducing new resource and app component crud APIs, improving visibility and maintenance of application input sources and added support for additional information attributes to be provided by customers.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``tnb``: This is the initial SDK release for AWS Telco Network Builder (TNB). AWS Telco Network Builder is a network automation service that helps you deploy and manage telecom networks.


1.27.75
=======

* api-change:``auditmanager``: This release introduces a ServiceQuotaExceededException to the UpdateAssessmentFrameworkShare API operation.
* api-change:``connect``: Reasons for failed diff has been approved by SDK Reviewer


1.27.74
=======

* api-change:``apprunner``: This release supports removing MaxSize limit for AutoScalingConfiguration.
* api-change:``glue``: Release of Delta Lake Data Lake Format for Glue Studio Service


1.27.73
=======

* api-change:``emr``: Update emr command to latest version
* api-change:``grafana``: With this release Amazon Managed Grafana now supports inbound Network Access Control that helps you to restrict user access to your Grafana workspaces
* api-change:``ivs``: Doc-only update. Updated text description in DeleteChannel, Stream, and StreamSummary.
* api-change:``wafv2``: Added a notice for account takeover prevention (ATP). The interface incorrectly lets you to configure ATP response inspection in regional web ACLs in Region US East (N. Virginia), without returning an error. ATP response inspection is only available in web ACLs that protect CloudFront distributions.


1.27.72
=======

* api-change:``cloudtrail``: This release adds an InsufficientEncryptionPolicyException type to the StartImport endpoint
* api-change:``efs``: Update efs command to latest version
* api-change:``frauddetector``: This release introduces Lists feature which allows customers to reference a set of values in Fraud Detector's rules. With Lists, customers can dynamically manage these attributes in real time. Lists can be created/deleted and its contents can be modified using the Fraud Detector API.
* api-change:``glue``: Fix DirectJDBCSource not showing up in CLI code gen
* api-change:``privatenetworks``: This release introduces a new StartNetworkResourceUpdate API, which enables return/replacement of hardware from a NetworkSite.
* api-change:``rds``: Database Activity Stream support for RDS for SQL Server.
* api-change:``wafv2``: For protected CloudFront distributions, you can now use the AWS WAF Fraud Control account takeover prevention (ATP) managed rule group to block new login attempts from clients that have recently submitted too many failed login attempts.


1.27.71
=======

* api-change:``appconfig``: AWS AppConfig now offers the option to set a version label on hosted configuration versions. Version labels allow you to identify specific hosted configuration versions based on an alternate versioning scheme that you define.
* api-change:``datasync``: With this launch, we are giving customers the ability to use older SMB protocol versions, enabling them to use DataSync to copy data to and from their legacy storage arrays.
* api-change:``ec2``: With this release customers can turn host maintenance on or off when allocating or modifying a supported dedicated host. Host maintenance is turned on by default for supported hosts.


1.27.70
=======

* api-change:``account``: This release of the Account Management API enables customers to view and manage whether AWS Opt-In Regions are enabled or disabled for their Account. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html
* api-change:``appconfigdata``: AWS AppConfig now offers the option to set a version label on hosted configuration versions. If a labeled hosted configuration version is deployed, its version label is available in the GetLatestConfiguration response.
* api-change:``snowball``: Adds support for EKS Anywhere on Snowball. AWS Snow Family customers can now install EKS Anywhere service on Snowball Edge Compute Optimized devices.


1.27.69
=======

* api-change:``autoscaling``: You can now either terminate/replace, ignore, or wait for EC2 Auto Scaling instances on standby or protected from scale in. Also, you can also roll back changes from a failed instance refresh.
* api-change:``connect``: This update provides the Wisdom session ARN for contacts enabled for Wisdom in the chat channel.
* api-change:``ec2``: Adds support for waiters that automatically poll for an imported snapshot until it reaches the completed state.
* api-change:``polly``: Amazon Polly adds two new neural Japanese voices - Kazuha, Tomoko
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for selecting algorithms in CreateAutoMLJob API.
* api-change:``sns``: This release adds support for SNS X-Ray active tracing as well as other updates.


1.27.68
=======

* api-change:``chime-sdk-meetings``: Documentation updates for Chime Meetings SDK
* api-change:``emr-containers``: EMR on EKS allows configuring retry policies for job runs through the StartJobRun API. Using retry policies, a job cause a driver pod to be restarted automatically if it fails or is deleted. The job's status can be seen in the DescribeJobRun and ListJobRun APIs and monitored using CloudWatch events.
* api-change:``evidently``: Updated entity overrides parameter to accept up to 2500 overrides or a total of 40KB.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``migration-hub-refactor-spaces``: This release adds support for creating environments with a network fabric type of NONE
* api-change:``workdocs``: Doc only update for the WorkDocs APIs.
* api-change:``workspaces``: Removed Windows Server 2016 BYOL and made changes based on IAM campaign.


1.27.67
=======

* api-change:``backup``: This release added one attribute (resource name) in the output model of our 9 existing APIs in AWS backup so that customers will see the resource name at the output. No input required from Customers.
* api-change:``cloudfront``: CloudFront Origin Access Control extends support to AWS Elemental MediaStore origins.
* api-change:``glue``: DirectJDBCSource + Glue 4.0 streaming options
* api-change:``lakeformation``: This release removes the LFTagpolicyResource expression limits.


1.27.66
=======

* api-change:``transfer``: Updated the documentation for the ImportCertificate API call, and added examples.


1.27.65
=======

* api-change:``compute-optimizer``: AWS Compute optimizer can now infer if Kafka is running on an instance.
* api-change:``customer-profiles``: This release deprecates the PartyType and Gender enum data types from the Profile model and replaces them with new PartyTypeString and GenderString attributes, which accept any string of length up to 255.
* api-change:``frauddetector``: My AWS Service (Amazon Fraud Detector) - This release introduces Cold Start Model Training which optimizes training for small datasets and adds intelligent methods for treating unlabeled data. You can now train Online Fraud Insights or Transaction Fraud Insights models with minimal historical-data.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added improved scene change detection capabilities and a bandwidth reduction filter, along with video quality enhancements, to the AVC encoder.
* api-change:``outposts``: Adds OrderType to Order structure. Adds PreviousOrderId and PreviousLineItemId to LineItem structure. Adds new line item status REPLACED. Increases maximum length of pagination token.


1.27.64
=======

* api-change:``proton``: Add new GetResourcesSummary API
* api-change:``redshift``: Corrects descriptions of the parameters for the API operations RestoreFromClusterSnapshot, RestoreTableFromClusterSnapshot, and CreateCluster.


1.27.63
=======

* api-change:``appconfig``: AWS AppConfig introduces KMS customer-managed key (CMK) encryption of configuration data, along with AWS Secrets Manager as a new configuration data source. S3 objects using SSE-KMS encryption and SSM Parameter Store SecureStrings are also now supported.
* api-change:``connect``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``keyspaces``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``quicksight``: QuickSight support for Radar Chart and Dashboard Publish Options
* api-change:``redshift``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``sso-admin``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.


1.27.62
=======

* api-change:``devops-guru``: This release adds filter support ListAnomalyForInsight API.
* api-change:``forecast``: This release will enable customer select INCREMENTAL as ImportModel in Forecast's CreateDatasetImportJob API. Verified latest SDK containing required attribute, following https://w.amazon.com/bin/view/AWS-Seer/Launch/Trebuchet/
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``mediatailor``: The AWS Elemental MediaTailor SDK for Channel Assembly has added support for program updates, and the ability to clip the end of VOD sources in programs.
* api-change:``sns``: Additional attributes added for set-topic-attributes.


1.27.61
=======

* api-change:``accessanalyzer``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``appsync``: This release introduces the feature to support EventBridge as AppSync data source.
* api-change:``cloudtrail-data``: Add CloudTrail Data Service to enable users to ingest activity events from non-AWS sources into CloudTrail Lake.
* api-change:``cloudtrail``: Add new "Channel" APIs to enable users to manage channels used for CloudTrail Lake integrations, and "Resource Policy" APIs to enable users to manage the resource-based permissions policy attached to a channel.
* api-change:``codeartifact``: This release introduces a new DeletePackage API, which enables deletion of a package and all of its versions from a repository.
* api-change:``connectparticipant``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``ec2``: This launch allows customers to associate up to 8 IP addresses to their NAT Gateways to increase the limit on concurrent connections to a single destination by eight times from 55K to 440K.
* api-change:``groundstation``: DigIF Expansion changes to the Customer APIs.
* api-change:``iot``: Added support for IoT Rules Engine Cloudwatch Logs action batch mode.
* api-change:``kinesis``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``opensearch``: Amazon OpenSearch Service adds the option for a VPC endpoint connection between two domains when the local domain uses OpenSearch version 1.3 or 2.3. You can now use remote reindex to copy indices from one VPC domain to another without a reverse proxy.
* api-change:``outposts``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``polly``: Amazon Polly adds two new neural American English voices - Ruth, Stephen
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports more completion criteria for Hyperparameter Optimization.
* api-change:``securityhub``: New fields have been added to the AWS Security Finding Format. Compliance.SecurityControlId is a unique identifier for a security control across standards. Compliance.AssociatedStandards contains all enabled standards in which a security control is enabled.
* api-change:``support``: This fixes incorrect endpoint construction when a customer is explicitly setting a region.


1.27.60
=======

* api-change:``clouddirectory``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``cloudformation``: This feature provides a method of obtaining which regions a stackset has stack instances deployed in.
* api-change:``discovery``: Update ImportName validation to 255 from the current length of 100
* api-change:``dlm``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``ec2``: We add Prefix Lists as a new route destination option for LocalGatewayRoutes. This will allow customers to create routes to Prefix Lists. Prefix List routes will allow customers to group individual CIDR routes with the same target into a single route.
* api-change:``imagebuilder``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``kafka``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``mediaconvert``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``swf``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.


1.27.59
=======

* api-change:``application-autoscaling``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``appstream``: Fixing the issue where Appstream waiters hang for fleet_started and fleet_stopped.
* api-change:``elasticbeanstalk``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``fis``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``glacier``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``greengrass``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``greengrassv2``: Enabled FIPS endpoints for GovCloud (US) in SDK.
* api-change:``mediatailor``: This release introduces the As Run logging type, along with API and documentation updates.
* api-change:``outposts``: Adding support for payment term in GetOrder, CreateOrder responses.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: This release supports running SageMaker Training jobs with container images that are in a private Docker registry.
* api-change:``serverlessrepo``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.


1.27.58
=======

* api-change:``events``: Update events command to latest version
* api-change:``iotfleetwise``: Add model validation to BatchCreateVehicle and BatchUpdateVehicle operations that invalidate requests with an empty vehicles list.
* api-change:``s3``: Allow FIPS to be used with path-style URLs.


1.27.57
=======

* enhancement:ec2 customization: Update --cidr parameter description to indicate the address range must be IPv4
* api-change:``cloudformation``: Enabled FIPS aws-us-gov endpoints in SDK.
* api-change:``ec2``: This release adds new functionality that allows customers to provision IPv6 CIDR blocks through Amazon VPC IP Address Manager (IPAM) as well as allowing customers to utilize IPAM Resource Discovery APIs.
* api-change:``m2``: Add returnCode, batchJobIdentifier in GetBatchJobExecution response, for user to view the batch job execution result & unique identifier from engine. Also removed unused headers from REST APIs
* api-change:``polly``: Add 5 new neural voices - Sergio (es-ES), Andres (es-MX), Remi (fr-FR), Adriano (it-IT) and Thiago (pt-BR).
* api-change:``redshift-serverless``: Added query monitoring rules as possible parameters for create and update workgroup operations.
* api-change:``s3control``: Add additional endpoint tests for S3 Control. Fix missing endpoint parameters for PutBucketVersioning and GetBucketVersioning. Prior to this fix, those operations may have resulted in an invalid endpoint being resolved.
* api-change:``sagemaker``: SageMaker Inference Recommender now decouples from Model Registry and could accept Model Name to invoke inference recommendations job; Inference Recommender now provides CPU/Memory Utilization metrics data in recommendation output.
* api-change:``sts``: Doc only change to update wording in a key topic


1.27.56
=======

* api-change:``databrew``: Enabled FIPS us-gov-west-1 endpoints in SDK.
* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Melbourne) Region (ap-southeast-4) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``ssm-sap``: This release provides updates to documentation and support for listing operations performed by AWS Systems Manager for SAP.


1.27.55
=======

* enhancement:``gamelift upload-build``: Add ``--server-sdk-version`` parameter to the ``upload-build`` command
* api-change:``lambda``: Release Lambda RuntimeManagementConfig, enabling customers to better manage runtime updates to their Lambda functions. This release adds two new APIs, GetRuntimeManagementConfig and PutRuntimeManagementConfig, as well as support on existing Create/Get/Update function APIs.
* api-change:``sagemaker``: Amazon SageMaker Inference now supports P4de instance types.


1.27.54
=======

* api-change:``ec2``: C6in, M6in, M6idn, R6in and R6idn instances are powered by 3rd Generation Intel Xeon Scalable processors (code named Ice Lake) with an all-core turbo frequency of 3.5 GHz.
* api-change:``ivs``: API and Doc update. Update to arns field in BatchGetStreamKey. Also updates to operations and structures.
* api-change:``quicksight``: This release adds support for data bars in QuickSight table and increases pivot table field well limit.


1.27.53
=======

* api-change:``appflow``: Adding support for Salesforce Pardot connector in Amazon AppFlow.
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``connect``: Amazon Connect Chat introduces Persistent Chat, allowing customers to resume previous conversations with context and transcripts carried over from previous chats, eliminating the need to repeat themselves and allowing agents to provide personalized service with access to entire conversation history.
* api-change:``connectparticipant``: This release updates Amazon Connect Participant's GetTranscript api to provide transcripts of past chats on a persistent chat session.
* api-change:``ec2``: Adds SSM Parameter Resource Aliasing support to EC2 Launch Templates. Launch Templates can now store parameter aliases in place of AMI Resource IDs. CreateLaunchTemplateVersion and DescribeLaunchTemplateVersions now support a convenience flag, ResolveAlias, to return the resolved parameter value.
* api-change:``glue``: Release Glue Studio Hudi Data Lake Format for SDK/CLI
* api-change:``groundstation``: Add configurable prepass and postpass times for DataflowEndpointGroup. Add Waiter to allow customers to wait for a contact that was reserved through ReserveContact
* api-change:``logs``: Bug fix - Removed the regex pattern validation from CoralModel to avoid potential security issue.
* api-change:``medialive``: AWS Elemental MediaLive adds support for SCTE 35 preRollMilliSeconds.
* api-change:``opensearch``: This release adds the enhanced dry run option, that checks for validation errors that might occur when deploying configuration changes and provides a summary of these errors, if any. The feature will also indicate whether a blue/green deployment will be required to apply a change.
* api-change:``panorama``: Added AllowMajorVersionUpdate option to OTAJobConfig to make appliance software major version updates opt-in.
* api-change:``sagemaker``: HyperParameterTuningJobs now allow passing environment variables into the corresponding TrainingJobs


1.27.52
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``ivschat``: Updates the range for a Chat Room's maximumMessageRatePerSecond field.
* api-change:``wafv2``: Improved the visibility of the guidance for updating AWS WAF resources, such as web ACLs and rule groups.


1.27.51
=======

* api-change:``billingconductor``: This release adds support for SKU Scope for pricing plans.
* api-change:``cloud9``: Added minimum value to AutomaticStopTimeMinutes parameter.
* api-change:``imagebuilder``: Add support for AWS Marketplace product IDs as input during CreateImageRecipe for the parent-image parameter. Add support for listing third-party components.
* api-change:``network-firewall``: Network Firewall now allows creation of dual stack endpoints, enabling inspection of IPv6 traffic.


1.27.50
=======

* api-change:``connect``: This release updates the responses of UpdateContactFlowContent, UpdateContactFlowMetadata, UpdateContactFlowName and DeleteContactFlow API with empty responses.
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``outposts``: This release adds POWER_30_KVA as an option for PowerDrawKva. PowerDrawKva is part of the RackPhysicalProperties structure in the CreateSite request.
* api-change:``resource-groups``: AWS Resource Groups customers can now turn on Group Lifecycle Events in their AWS account. When you turn this on, Resource Groups monitors your groups for changes to group state or membership. Those changes are sent to Amazon EventBridge as events that you can respond to using rules you create.


1.27.49
=======

* api-change:``cleanrooms``: Initial release of AWS Clean Rooms
* api-change:``lambda``: Add support for MaximumConcurrency parameter for SQS event source. Customers can now limit the maximum concurrent invocations for their SQS Event Source Mapping.
* api-change:``logs``: Bug fix: logGroupName is now not a required field in GetLogEvents, FilterLogEvents, GetLogGroupFields, and DescribeLogStreams APIs as logGroupIdentifier can be provided instead
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for compact DASH manifest generation, audio normalization using TruePeak measurements, and the ability to clip the sample range in the color corrector.
* api-change:``secretsmanager``: Update documentation for new ListSecrets and DescribeSecret parameters


1.27.48
=======

* api-change:``kendra``: This release adds support to new document types - RTF, XML, XSLT, MS_EXCEL, CSV, JSON, MD


1.27.47
=======

* api-change:``location``: This release adds support for two new route travel models, Bicycle and Motorcycle which can be used with Grab data source.
* api-change:``rds``: This release adds support for configuring allocated storage on the CreateDBInstanceReadReplica, RestoreDBInstanceFromDBSnapshot, and RestoreDBInstanceToPointInTime APIs.


1.27.46
=======

* bugfix:``codeartifact login``: Fix parsing of dotnet output for aws codeartifact login command; fixes `#6197 <https://github.com/aws/aws-cli/issues/6197>`__
* api-change:``ecr-public``: This release for Amazon ECR Public makes several change to bring the SDK into sync with the API.
* api-change:``kendra-ranking``: Introducing Amazon Kendra Intelligent Ranking, a new set of Kendra APIs that leverages Kendra semantic ranking capabilities to improve the quality of search results from other search services (i.e. OpenSearch, ElasticSearch, Solr).
* api-change:``network-firewall``: Network Firewall now supports the Suricata rule action reject, in addition to the actions pass, drop, and alert.
* api-change:``ram``: Enabled FIPS aws-us-gov endpoints in SDK.
* api-change:``workspaces-web``: This release adds support for a new portal authentication type: AWS IAM Identity Center (successor to AWS Single Sign-On).


1.27.45
=======

* api-change:``acm-pca``: Added revocation parameter validation: bucket names must match S3 bucket naming rules and CNAMEs conform to RFC2396 restrictions on the use of special characters in URIs.
* api-change:``auditmanager``: This release introduces a new data retention option in your Audit Manager settings. You can now use the DeregistrationPolicy parameter to specify if you want to delete your data when you deregister Audit Manager.


1.27.44
=======

* api-change:``amplifybackend``: Updated GetBackendAPIModels response to include ModelIntrospectionSchema json string
* api-change:``apprunner``: This release adds support of securely referencing secrets and configuration data that are stored in Secrets Manager and SSM Parameter Store by adding them as environment secrets in your App Runner service.
* api-change:``connect``: Documentation update for a new Initiation Method value in DescribeContact API
* api-change:``emr-serverless``: Adds support for customized images. You can now provide runtime images when creating or updating EMR Serverless Applications.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``mwaa``: MWAA supports Apache Airflow version 2.4.3.
* api-change:``rds``: This release adds support for specifying which certificate authority (CA) to use for a DB instance's server certificate during DB instance creation, as well as other CA enhancements.


1.27.43
=======

* api-change:``application-autoscaling``: Customers can now use the existing DescribeScalingActivities API to also see the detailed and machine-readable reasons for Application Auto Scaling not scaling their resources and, if needed, take the necessary corrective actions.
* api-change:``logs``: Update to remove sequenceToken as a required field in PutLogEvents calls.
* api-change:``ssm``: Adding support for QuickSetup Document Type in Systems Manager


1.27.42
=======

* api-change:``securitylake``: Allow CreateSubscriber API to take string input that allows setting more descriptive SubscriberDescription field. Make souceTypes field required in model level for UpdateSubscriberRequest as it is required for every API call on the backend. Allow ListSubscribers take any String as nextToken param.


1.27.41
=======

* api-change:``cloudfront``: Extend response headers policy to support removing headers from viewer responses
* api-change:``iotfleetwise``: Update documentation - correct the epoch constant value of default value for expiryTime field in CreateCampaign request.


1.27.40
=======

* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``emr``: Update emr command to latest version
* api-change:``secretsmanager``: Added owning service filter, include planned deletion flag, and next rotation date response parameter in ListSecrets.
* api-change:``wisdom``: This release extends Wisdom CreateContent and StartContentUpload APIs to support PDF and MicrosoftWord docx document uploading.


1.27.39
=======

* api-change:``elasticache``: This release allows you to modify the encryption in transit setting, for existing Redis clusters. You can now change the TLS configuration of your Redis clusters without the need to re-build or re-provision the clusters or impact application availability.
* api-change:``network-firewall``: AWS Network Firewall now provides status messages for firewalls to help you troubleshoot when your endpoint fails.
* api-change:``rds``: This release adds support for Custom Engine Version (CEV) on RDS Custom SQL Server.
* api-change:``route53-recovery-control-config``: Added support for Python paginators in the route53-recovery-control-config List* APIs.


1.27.38
=======

* api-change:``memorydb``: This release adds support for MemoryDB Reserved nodes which provides a significant discount compared to on-demand node pricing. Reserved nodes are not physical nodes, but rather a billing discount applied to the use of on-demand nodes in your account.
* api-change:``transfer``: Add additional operations to throw ThrottlingExceptions


1.27.37
=======

* api-change:``connect``: Support for Routing Profile filter, SortCriteria, and grouping by Routing Profiles for GetCurrentMetricData API. Support for RoutingProfiles, UserHierarchyGroups, and Agents as filters, NextStatus and AgentStatusName for GetCurrentUserData. Adds ApproximateTotalCount to both APIs.
* api-change:``connectparticipant``: Amazon Connect Chat introduces the Message Receipts feature. This feature allows agents and customers to receive message delivered and read receipts after they send a chat message.
* api-change:``detective``: This release adds a missed AccessDeniedException type to several endpoints.
* api-change:``fsx``: Fix a bug where a recent release might break certain existing SDKs.
* api-change:``inspector2``: Amazon Inspector adds support for scanning NodeJS 18.x and Go 1.x AWS Lambda function runtimes.


1.27.36
=======

* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate optimization recommendations for ecs services running on Fargate.
* api-change:``connect``: Amazon Connect Chat introduces the Idle Participant/Autodisconnect feature, which allows users to set timeouts relating to the activity of chat participants, using the new UpdateParticipantRoleConfig API.
* api-change:``iotdeviceadvisor``: This release adds the following new features: 1) Documentation updates for IoT Device Advisor APIs. 2) Updated required request parameters for IoT Device Advisor APIs. 3) Added new service feature: ability to provide the test endpoint when customer executing the StartSuiteRun API.
* api-change:``kinesis-video-webrtc-storage``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``rds``: Add support for managing master user password in AWS Secrets Manager for the DBInstance and DBCluster.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager


1.27.35
=======

* api-change:``connect``: Amazon Connect Chat now allows for JSON (application/json) message types to be sent as part of the initial message in the StartChatContact API.
* api-change:``connectparticipant``: Amazon Connect Chat now allows for JSON (application/json) message types to be sent in the SendMessage API.
* api-change:``license-manager-linux-subscriptions``: AWS License Manager now offers cross-region, cross-account tracking of commercial Linux subscriptions on AWS. This includes subscriptions purchased as part of EC2 subscription-included AMIs, on the AWS Marketplace, or brought to AWS via Red Hat Cloud Access Program.
* api-change:``macie2``: This release adds support for analyzing Amazon S3 objects that use the S3 Glacier Instant Retrieval (Glacier_IR) storage class.
* api-change:``sagemaker``: This release enables adding RStudio Workbench support to an existing Amazon SageMaker Studio domain. It allows setting your RStudio on SageMaker environment configuration parameters and also updating the RStudioConnectUrl and RStudioPackageManagerUrl parameters for existing domains
* api-change:``scheduler``: Updated the ListSchedules and ListScheduleGroups APIs to allow the NamePrefix field to start with a number. Updated the validation for executionRole field to support any role name.
* api-change:``ssm``: Doc-only updates for December 2022.
* api-change:``support``: Documentation updates for the AWS Support API
* api-change:``transfer``: This release adds support for Decrypt as a workflow step type.


1.27.34
=======

* api-change:``batch``: Adds isCancelled and isTerminated to DescribeJobs response.
* api-change:``ec2``: Adds support for pagination in the EC2 DescribeImages API.
* api-change:``lookoutequipment``: This release adds support for listing inference schedulers by status.
* api-change:``medialive``: This release adds support for two new features to AWS Elemental MediaLive. First, you can now burn-in timecodes to your MediaLive outputs. Second, we now now support the ability to decode Dolby E audio when it comes in on an input.
* api-change:``nimble``: Amazon Nimble Studio now supports configuring session storage volumes and persistence, as well as backup and restore sessions through launch profiles.
* api-change:``resource-explorer-2``: Documentation updates for AWS Resource Explorer.
* api-change:``route53domains``: Use Route 53 domain APIs to change owner, create/delete DS record, modify IPS tag, resend authorization. New: AssociateDelegationSignerToDomain, DisassociateDelegationSignerFromDomain, PushDomain, ResendOperationAuthorization. Updated: UpdateDomainContact, ListOperations, CheckDomainTransferability.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for new objective metrics in CreateAutoMLJob API.
* api-change:``transcribe``: Enable our batch transcription jobs for Swedish and Vietnamese.


1.27.33
=======

* api-change:``athena``: Add missed InvalidRequestException in GetCalculationExecutionCode,StopCalculationExecution APIs. Correct required parameters (Payload and Type) in UpdateNotebook API. Change Notebook size from 15 Mb to 10 Mb.
* api-change:``ecs``: This release adds support for alarm-based rollbacks in ECS, a new feature that allows customers to add automated safeguards for Amazon ECS service rolling updates.
* api-change:``kinesisvideo``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``kinesis-video-webrtc-storage``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``rds``: Add support for --enable-customer-owned-ip to RDS create-db-instance-read-replica API for RDS on Outposts.
* api-change:``sagemaker``: AWS Sagemaker - Sagemaker Images now supports Aliases as secondary identifiers for ImageVersions. SageMaker Images now supports additional metadata for ImageVersions for better images management.


1.27.32
=======

* api-change:``appflow``: This release updates the ListConnectorEntities API action so that it returns paginated responses that customers can retrieve with next tokens.
* api-change:``cloudfront``: Updated documentation for CloudFront
* api-change:``datasync``: AWS DataSync now supports the use of tags with task executions. With this new feature, you can apply tags each time you execute a task, giving you greater control and management over your task executions.
* api-change:``efs``: Update efs command to latest version
* api-change:``guardduty``: This release provides the valid characters for the Description and Name field.
* api-change:``iotfleetwise``: Updated error handling for empty resource names in "UpdateSignalCatalog" and "GetModelManifest" operations.
* api-change:``sagemaker``: AWS sagemaker - Features: This release adds support for random seed, it's an integer value used to initialize a pseudo-random number generator. Setting a random seed will allow the hyperparameter tuning search strategies to produce more consistent configurations for the same tuning job.


1.27.31
=======

* api-change:``backup-gateway``: This release adds support for VMware vSphere tags, enabling customer to protect VMware virtual machines using tag-based policies for AWS tags mapped from vSphere tags. This release also adds support for customer-accessible gateway-hypervisor interaction log and upload bandwidth rate limit schedule.
* api-change:``connect``: Added support for "English - New Zealand" and "English - South African" to be used with Amazon Connect Custom Vocabulary APIs.
* api-change:``ecs``: This release adds support for container port ranges in ECS, a new capability that allows customers to provide container port ranges to simplify use cases where multiple ports are in use in a container. This release updates TaskDefinition mutation APIs and the Task description APIs.
* api-change:``eks``: Add support for Windows managed nodes groups.
* api-change:``glue``: This release adds support for AWS Glue Crawler with native DeltaLake tables, allowing Crawlers to classify Delta Lake format tables and catalog them for query engines to query against.
* api-change:``kinesis``: Added StreamARN parameter for Kinesis Data Streams APIs. Added a new opaque pagination token for ListStreams. SDKs will auto-generate Account Endpoint when accessing Kinesis Data Streams.
* api-change:``location``: This release adds support for a new style, "VectorOpenDataStandardLight" which can be used with the new data source, "Open Data Maps (Preview)".
* api-change:``m2``: Adds an optional create-only `KmsKeyId` property to Environment and Application resources.
* api-change:``sagemaker``: SageMaker Inference Recommender now allows customers to load tests their models on various instance types using private VPC.
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for AwsEc2LaunchTemplate, AwsSageMakerNotebookInstance, AwsWafv2WebAcl and AwsWafv2RuleGroup.
* api-change:``translate``: Raised the input byte size limit of the Text field in the TranslateText API to 10000 bytes.


1.27.30
=======

* api-change:``ce``: This release supports percentage-based thresholds on Cost Anomaly Detection alert subscriptions.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``networkmanager``: Appliance Mode support for AWS Cloud WAN.
* api-change:``redshift-data``: This release adds a new --client-token field to ExecuteStatement and BatchExecuteStatement operations. Customers can now run queries with the additional client token parameter to ensures idempotency.
* api-change:``sagemaker-metrics``: Update SageMaker Metrics documentation.


1.27.29
=======

* api-change:``cloudtrail``: Merging mainline branch for service model into mainline release branch. There are no new APIs.
* api-change:``rds``: This deployment adds ClientPasswordAuthType field to the Auth structure of the DBProxy.


1.27.28
=======

* api-change:``customer-profiles``: This release allows custom strings in PartyType and Gender through 2 new attributes in the CreateProfile and UpdateProfile APIs: PartyTypeString and GenderString.
* api-change:``ec2``: This release updates DescribeFpgaImages to show supported instance types of AFIs in its response.
* api-change:``kinesisvideo``: This release adds support for public preview of Kinesis Video Stream at Edge enabling customers to provide configuration for the Kinesis Video Stream EdgeAgent running on an on-premise IoT device. Customers can now locally record from cameras and stream videos to the cloud on configured schedule.
* api-change:``lookoutvision``: This documentation update adds kms:GenerateDataKey as a required permission to StartModelPackagingJob.
* api-change:``migration-hub-refactor-spaces``: This release adds support for Lambda alias service endpoints. Lambda alias ARNs can now be passed into CreateService.
* api-change:``rds``: Update the RDS API model to support copying option groups during the CopyDBSnapshot operation
* api-change:``rekognition``: Adds support for "aliases" and "categories", inclusion and exclusion filters for labels and label categories, and aggregating labels by video segment timestamps for Stored Video Label Detection APIs.
* api-change:``sagemaker-metrics``: This release introduces support SageMaker Metrics APIs.
* api-change:``wafv2``: Documents the naming requirement for logging destinations that you use with web ACLs.


1.27.27
=======

* api-change:``iotfleetwise``: Deprecated assignedValue property for actuators and attributes.  Added a message to invalid nodes and invalid decoder manifest exceptions.
* api-change:``logs``: Doc-only update for CloudWatch Logs, for Tagging Permissions clarifications
* api-change:``medialive``: Link devices now support buffer size (latency) configuration. A higher latency value means a longer delay in transmitting from the device to MediaLive, but improved resiliency. A lower latency value means a shorter delay, but less resiliency.
* api-change:``mediapackage-vod``: This release provides the approximate number of assets in a packaging group.


1.27.26
=======

* api-change:``autoscaling``: Adds support for metric math for target tracking scaling policies, saving you the cost and effort of publishing a custom metric to CloudWatch. Also adds support for VPC Lattice by adding the Attach/Detach/DescribeTrafficSources APIs and a new health check type to the CreateAutoScalingGroup API.
* api-change:``iottwinmaker``: This release adds the following new features: 1) New APIs for managing a continuous sync of assets and asset models from AWS IoT SiteWise. 2) Support user friendly names for component types (ComponentTypeName) and properties (DisplayName).
* api-change:``migrationhubstrategy``: This release adds known application filtering, server selection for assessments, support for potential recommendations, and indications for configuration and assessment status. For more information, see the AWS Migration Hub documentation at https://docs.aws.amazon.com/migrationhub/index.html


1.27.25
=======

* api-change:``ce``: This release adds the LinkedAccountName field to the GetAnomalies API response under RootCause
* api-change:``cloudfront``: Introducing UpdateDistributionWithStagingConfig that can be used to promote the staging configuration to the production.
* api-change:``eks``: Adds support for EKS add-ons configurationValues fields and DescribeAddonConfiguration function
* api-change:``kms``: Updated examples and exceptions for External Key Store (XKS).


1.27.24
=======

* api-change:``billingconductor``: This release adds the Tiering Pricing Rule feature.
* api-change:``connect``: This release provides APIs that enable you to programmatically manage rules for Contact Lens conversational analytics and third party applications. For more information, see   https://docs.aws.amazon.com/connect/latest/APIReference/rules-api.html
* api-change:``dynamodb``: Endpoint Ruleset update: Use http instead of https for the "local" region.
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``rds``: This release adds the BlueGreenDeploymentNotFoundFault to the AddTagsToResource, ListTagsForResource, and RemoveTagsFromResource operations.
* api-change:``sagemaker-featurestore-runtime``: For online + offline Feature Groups, added ability to target PutRecord and DeleteRecord actions to only online store, or only offline store. If target store parameter is not specified, actions will apply to both stores.


1.27.23
=======

* bugfix:``codeartifact login``: Ignore always-auth errors for CodeArtifact login command; fixes `#7434 <https://github.com/aws/aws-cli/issues/7434>`__
* api-change:``ce``: This release introduces two new APIs that offer a 1-click experience to refresh Savings Plans recommendations. The two APIs are StartSavingsPlansPurchaseRecommendationGeneration and ListSavingsPlansPurchaseRecommendationGeneration.
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``ivschat``: Adds PendingVerification error type to messaging APIs to block the resource usage for accounts identified as being fraudulent.
* api-change:``rds``: This release adds the InvalidDBInstanceStateFault to the RestoreDBClusterFromSnapshot operation.
* api-change:``transcribe``: Amazon Transcribe now supports creating custom language models in the following languages: Japanese (ja-JP) and German (de-DE).


1.27.22
=======

* api-change:``appsync``: Fixes the URI for the evaluatecode endpoint to include the /v1 prefix (ie. "/v1/dataplane-evaluatecode").
* api-change:``ecs``: Documentation updates for Amazon ECS
* api-change:``fms``: AWS Firewall Manager now supports Fortigate Cloud Native Firewall as a Service as a third-party policy type.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for configurable ID3 eMSG box attributes and the ability to signal them with InbandEventStream tags in DASH and CMAF outputs.
* api-change:``medialive``: Updates to Event Signaling and Management (ESAM) API and documentation.
* api-change:``polly``: Add language code for Finnish (fi-FI)
* api-change:``proton``: CreateEnvironmentAccountConnection RoleArn input is now optional
* api-change:``redshift-serverless``: Add Table Level Restore operations for Amazon Redshift Serverless. Add multi-port support for Amazon Redshift Serverless endpoints. Add Tagging support to Snapshots and Recovery Points in Amazon Redshift Serverless.
* api-change:``sns``: This release adds the message payload-filtering feature to the SNS Subscribe, SetSubscriptionAttributes, and GetSubscriptionAttributes API actions


1.27.21
=======

* api-change:``codecatalyst``: This release adds operations that support customers using the AWS Toolkits and Amazon CodeCatalyst, a unified software development service that helps developers develop, deploy, and maintain applications in the cloud. For more information, see the documentation.
* api-change:``comprehend``: Comprehend now supports semi-structured documents (such as PDF files or image files) as inputs for custom analysis using the synchronous APIs (ClassifyDocument and DetectEntities).
* api-change:``gamelift``: GameLift introduces a new feature, GameLift Anywhere. GameLift Anywhere allows you to integrate your own compute resources with GameLift. You can also use GameLift Anywhere to iteratively test your game servers without uploading the build to GameLift for every iteration.
* api-change:``pipes``: AWS introduces new Amazon EventBridge Pipes which allow you to connect sources (SQS, Kinesis, DDB, Kafka, MQ) to Targets (14+ EventBridge Targets) without any code, with filtering, batching, input transformation, and an optional Enrichment stage (Lambda, StepFunctions, ApiGateway, ApiDestinations)
* api-change:``stepfunctions``: Update stepfunctions command to latest version


1.27.20
=======

* api-change:``accessanalyzer``: This release adds support for S3 cross account access points. IAM Access Analyzer will now produce public or cross account findings when it detects bucket delegation to external account access points.
* api-change:``athena``: This release includes support for using Apache Spark in Amazon Athena.
* api-change:``dataexchange``: This release enables data providers to license direct access to data in their Amazon S3 buckets or AWS Lake Formation data lakes through AWS Data Exchange. Subscribers get read-only access to the data and can use it in downstream AWS services, like Amazon Athena, without creating or managing copies.
* api-change:``docdb-elastic``: Launched Amazon DocumentDB Elastic Clusters. You can now use the SDK to create, list, update and delete Amazon DocumentDB Elastic Cluster resources
* api-change:``glue``: This release adds support for AWS Glue Data Quality, which helps you evaluate and monitor the quality of your data and includes the API for creating, deleting, or updating data quality rulesets, runs and evaluations.
* api-change:``s3control``: Amazon S3 now supports cross-account access points. S3 bucket owners can now allow trusted AWS accounts to create access points associated with their bucket.
* api-change:``sagemaker-geospatial``: This release provides Amazon SageMaker geospatial APIs to build, train, deploy and visualize geospatial models.
* api-change:``sagemaker``: Added Models as part of the Search API. Added Model shadow deployments in realtime inference, and shadow testing in managed inference. Added support for shared spaces, geospatial APIs, Model Cards, AutoMLJobStep in pipelines, Git repositories on user profiles and domains, Model sharing in Jumpstart.


1.27.19
=======

* api-change:``ec2``: This release adds support for AWS Verified Access and the Hpc6id Amazon EC2 compute optimized instance type, which features 3rd generation Intel Xeon Scalable processors.
* api-change:``firehose``: Allow support for the Serverless offering for Amazon OpenSearch Service as a Kinesis Data Firehose delivery destination.
* api-change:``kms``: AWS KMS introduces the External Key Store (XKS), a new feature for customers who want to protect their data with encryption keys stored in an external key management system under their control.
* api-change:``omics``: Amazon Omics is a new, purpose-built service that can be used by healthcare and life science organizations to store, query, and analyze omics data. The insights from that data can be used to accelerate scientific discoveries and improve healthcare.
* api-change:``opensearchserverless``: Publish SDK for Amazon OpenSearch Serverless
* api-change:``securitylake``: Amazon Security Lake automatically centralizes security data from cloud, on-premises, and custom sources into a purpose-built data lake stored in your account. Security Lake makes it easier to analyze security data, so you can improve the protection of your workloads, applications, and data
* api-change:``simspaceweaver``: AWS SimSpace Weaver is a new service that helps customers build spatial simulations at new levels of scale - resulting in virtual worlds with millions of dynamic entities. See the AWS SimSpace Weaver developer guide for more details on how to get started. https://docs.aws.amazon.com/simspaceweaver


1.27.18
=======

* api-change:``arc-zonal-shift``: Amazon Route 53 Application Recovery Controller Zonal Shift is a new service that makes it easy to shift traffic away from an Availability Zone in a Region. See the developer guide for more information: https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html
* api-change:``compute-optimizer``: Adds support for a new recommendation preference that makes it possible for customers to optimize their EC2 recommendations by utilizing an external metrics ingestion service to provide metrics.
* api-change:``config``: With this release, you can use AWS Config to evaluate your resources for compliance with Config rules before they are created or updated. Using Config rules in proactive mode enables you to test and build compliant resource templates or check resource configurations at the time they are provisioned.
* api-change:``ec2``: Introduces ENA Express, which uses AWS SRD and dynamic routing to increase throughput and minimize latency, adds support for trust relationships between Reachability Analyzer and AWS Organizations to enable cross-account analysis, and adds support for Infrastructure Performance metric subscriptions.
* api-change:``eks``: Adds support for additional EKS add-ons metadata and filtering fields
* api-change:``fsx``: This release adds support for 4GB/s / 160K PIOPS FSx for ONTAP file systems and 10GB/s / 350K PIOPS FSx for OpenZFS file systems (Single_AZ_2). For FSx for ONTAP, this also adds support for DP volumes, snapshot policy, copy tags to backups, and Multi-AZ route table updates.
* api-change:``glue``: This release allows the creation of Custom Visual Transforms (Dynamic Transforms) to be created via AWS Glue CLI/SDK.
* api-change:``inspector2``: This release adds support for Inspector to scan AWS Lambda.
* api-change:``lambda``: Adds support for Lambda SnapStart, which helps improve the startup performance of functions. Customers can now manage SnapStart based functions via CreateFunction and UpdateFunctionConfiguration APIs
* api-change:``license-manager-user-subscriptions``: AWS now offers fully-compliant, Amazon-provided licenses for Microsoft Office Professional Plus 2021 Amazon Machine Images (AMIs) on Amazon EC2. These AMIs are now available on the Amazon EC2 console and on AWS Marketplace to launch instances on-demand without any long-term licensing commitments.
* api-change:``macie2``: Added support for configuring Macie to continually sample objects from S3 buckets and inspect them for sensitive data. Results appear in statistics, findings, and other data that Macie provides.
* api-change:``quicksight``: This release adds new Describe APIs and updates Create and Update APIs to support the data model for Dashboards, Analyses, and Templates.
* api-change:``s3control``: Added two new APIs to support Amazon S3 Multi-Region Access Point failover controls: GetMultiRegionAccessPointRoutes and SubmitMultiRegionAccessPointRoutes. The failover control APIs are supported in the following Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2, and ap-northeast-1.
* api-change:``securityhub``: Adding StandardsManagedBy field to DescribeStandards API response


1.27.17
=======

* api-change:``backup``: AWS Backup introduces support for legal hold and application stack backups. AWS Backup Audit Manager introduces support for cross-Region, cross-account reports.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``drs``: Non breaking changes to existing APIs, and additional APIs added to support in-AWS failing back using AWS Elastic Disaster Recovery.
* api-change:``ecs``: This release adds support for ECS Service Connect, a new capability that simplifies writing and operating resilient distributed applications. This release updates the TaskDefinition, Cluster, Service mutation APIs with Service connect constructs and also adds a new ListServicesByNamespace API.
* api-change:``efs``: Update efs command to latest version
* api-change:``iot-data``: This release adds support for MQTT5 properties to AWS IoT HTTP Publish API.
* api-change:``iot``: Job scheduling enables the scheduled rollout of a Job with start and end times and a customizable end behavior when end time is reached. This is available for continuous and snapshot jobs. Added support for MQTT5 properties to AWS IoT TopicRule Republish Action.
* api-change:``iotwireless``: This release includes a new feature for customers to calculate the position of their devices by adding three new APIs: UpdateResourcePosition, GetResourcePosition, and GetPositionEstimate.
* api-change:``kendra``: Amazon Kendra now supports preview of table information from HTML tables in the search results. The most relevant cells with their corresponding rows, columns are displayed as a preview in the search result. The most relevant table cell or cells are also highlighted in table preview.
* api-change:``logs``: Updates to support CloudWatch Logs data protection and CloudWatch cross-account observability
* api-change:``mgn``: This release adds support for Application and Wave management. We also now support custom post-launch actions.
* api-change:``oam``: Amazon CloudWatch Observability Access Manager is a new service that allows configuration of the CloudWatch cross-account observability feature.
* api-change:``organizations``: This release introduces delegated administrator for AWS Organizations, a new feature to help you delegate the management of your Organizations policies, enabling you to govern your AWS organization in a decentralized way. You can now allow member accounts to manage Organizations policies.
* api-change:``rds``: This release enables new Aurora and RDS feature called Blue/Green Deployments that makes updates to databases safer, simpler and faster.
* api-change:``textract``: This release adds support for classifying and splitting lending documents by type, and extracting information by using the Analyze Lending APIs. This release also includes support for summarized information of the processed lending document package, in addition to per document results.
* api-change:``transcribe``: This release adds support for 'inputType' for post-call and real-time (streaming) Call Analytics within Amazon Transcribe.


1.27.16
=======

* api-change:``grafana``: This release includes support for configuring a Grafana workspace to connect to a datasource within a VPC as well as new APIs for configuring Grafana settings.
* api-change:``rbin``: This release adds support for Rule Lock for Recycle Bin, which allows you to lock retention rules so that they can no longer be modified or deleted.


1.27.15
=======

* api-change:``appflow``: Adding support for Amazon AppFlow to transfer the data to Amazon Redshift databases through Amazon Redshift Data API service. This feature will support the Redshift destination connector on both public and private accessible Amazon Redshift Clusters and Amazon Redshift Serverless.
* api-change:``kinesisanalyticsv2``: Support for Apache Flink 1.15 in Kinesis Data Analytics.


1.27.14
=======

* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Hyderabad) Region (ap-south-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.


1.27.13
=======

* api-change:``appflow``: AppFlow provides a new API called UpdateConnectorRegistration to update a custom connector that customers have previously registered. With this API, customers no longer need to unregister and then register a connector to make an update.
* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Evidence finder. You can now use evidence finder to quickly query your evidence, and add the matching evidence results to an assessment report.
* api-change:``chime-sdk-voice``: Amazon Chime Voice Connector, Voice Connector Group and PSTN Audio Service APIs are now available in the Amazon Chime SDK Voice namespace. See https://docs.aws.amazon.com/chime-sdk/latest/dg/sdk-available-regions.html for more details.
* api-change:``cloudfront``: CloudFront API support for staging distributions and associated traffic management policies.
* api-change:``connect``: Added AllowedAccessControlTags and TagRestrictedResource for Tag Based Access Control on Amazon Connect Webpage
* api-change:``dynamodb``: Updated minor fixes for DynamoDB documentation.
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``ec2``: This release adds support for copying an Amazon Machine Image's tags when copying an AMI.
* api-change:``glue``: AWSGlue Crawler - Adding support for Table and Column level Comments with database level datatypes for JDBC based crawler.
* api-change:``iot-roborunner``: AWS IoT RoboRunner is a new service that makes it easy to build applications that help multi-vendor robots work together seamlessly. See the IoT RoboRunner developer guide for more details on getting started. https://docs.aws.amazon.com/iotroborunner/latest/dev/iotroborunner-welcome.html
* api-change:``quicksight``: This release adds the following: 1) Asset management for centralized assets governance 2) QuickSight Q now supports public embedding 3) New Termination protection flag to mitigate accidental deletes 4) Athena data sources now accept a custom IAM role 5) QuickSight supports connectivity to Databricks
* api-change:``sagemaker``: Added DisableProfiler flag as a new field in ProfilerConfig
* api-change:``servicecatalog``: This release 1. adds support for Principal Name Sharing with Service Catalog portfolio sharing. 2. Introduces repo sourced products which are created and managed with existing SC APIs. These products are synced to external repos and auto create new product versions based on changes in the repo.
* api-change:``ssm-sap``: AWS Systems Manager for SAP provides simplified operations and management of SAP applications such as SAP HANA. With this release, SAP customers and partners can automate and simplify their SAP system administration tasks such as backup/restore of SAP HANA.
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``transfer``: Adds a NONE encryption algorithm type to AS2 connectors, providing support for skipping encryption of the AS2 message body when a HTTPS URL is also specified.


1.27.12
=======

* api-change:``amplify``: Adds a new value (WEB_COMPUTE) to the Platform enum that allows customers to create Amplify Apps with Server-Side Rendering support.
* api-change:``appflow``: AppFlow simplifies the preparation and cataloging of SaaS data into the AWS Glue Data Catalog where your data can be discovered and accessed by AWS analytics and ML services. AppFlow now also supports data field partitioning and file size optimization to improve query performance and reduce cost.
* api-change:``appsync``: This release introduces the APPSYNC_JS runtime, and adds support for JavaScript in AppSync functions and AppSync pipeline resolvers.
* api-change:``dms``: Adds support for Internet Protocol Version 6 (IPv6) on DMS Replication Instances
* api-change:``ec2``: This release adds a new optional parameter "privateIpAddress" for the CreateNatGateway API. PrivateIPAddress will allow customers to select a custom Private IPv4 address instead of having it be auto-assigned.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``emr-serverless``: Adds support for AWS Graviton2 based applications. You can now select CPU architecture when creating new applications or updating existing ones.
* api-change:``ivschat``: Adds LoggingConfiguration APIs for IVS Chat - a feature that allows customers to store and record sent messages in a chat room to S3 buckets, CloudWatch logs, or Kinesis firehose.
* api-change:``lambda``: Add Node 18 (nodejs18.x) support to AWS Lambda.
* api-change:``personalize``: This release provides support for creation and use of metric attributions in AWS Personalize
* api-change:``polly``: Add two new neural voices - Ola (pl-PL) and Hala (ar-AE).
* api-change:``rum``: CloudWatch RUM now supports custom events. To use custom events, create an app monitor or update an app monitor with CustomEvent Status as ENABLED.
* api-change:``s3control``: Added 34 new S3 Storage Lens metrics to support additional customer use cases.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager.
* api-change:``securityhub``: Added SourceLayerArn and SourceLayerHash field for security findings.  Updated AwsLambdaFunction Resource detail
* api-change:``servicecatalog-appregistry``: This release adds support for tagged resource associations, which allows you to associate a group of resources with a defined resource tag key and value to the application.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``textract``: This release adds support for specifying and extracting information from documents using the Signatures feature within Analyze Document API
* api-change:``workspaces``: The release introduces CreateStandbyWorkspaces, an API that allows you to create standby WorkSpaces associated with a primary WorkSpace in another Region. DescribeWorkspaces now includes related WorkSpaces properties. DescribeWorkspaceBundles and CreateWorkspaceBundle now return more bundle details.


1.27.11
=======

* api-change:``batch``: Documentation updates related to Batch on EKS
* api-change:``billingconductor``: This release adds a new feature BillingEntity pricing rule.
* api-change:``cloudformation``: Added UnsupportedTarget HandlerErrorCode for use with CFN Resource Hooks
* api-change:``comprehendmedical``: This release supports new set of entities and traits. It also adds new category (BEHAVIORAL_ENVIRONMENTAL_SOCIAL).
* api-change:``connect``: This release adds a new MonitorContact API for initiating monitoring of ongoing Voice and Chat contacts.
* api-change:``eks``: Adds support for customer-provided placement groups for Kubernetes control plane instances when creating local EKS clusters on Outposts
* api-change:``elasticache``: for Redis now supports AWS Identity and Access Management authentication access to Redis clusters starting with redis-engine version 7.0
* api-change:``iottwinmaker``: This release adds the following: 1) ExecuteQuery API allows users to query their AWS IoT TwinMaker Knowledge Graph 2) Pricing plan APIs allow users to configure and manage their pricing mode 3) Support for property groups and tabular property values in existing AWS IoT TwinMaker APIs.
* api-change:``personalize-events``: This release provides support for creation and use of metric attributions in AWS Personalize
* api-change:``proton``: Add support for sorting and filtering in ListServiceInstances
* api-change:``rds``: This release adds support for container databases (CDBs) to Amazon RDS Custom for Oracle. A CDB contains one PDB at creation. You can add more PDBs using Oracle SQL. You can also customize your database installation by setting the Oracle base, Oracle home, and the OS user name and group.
* api-change:``ssm-incidents``: Add support for PagerDuty integrations on ResponsePlan, IncidentRecord, and RelatedItem APIs
* api-change:``ssm``: This release adds support for cross account access in CreateOpsItem, UpdateOpsItem and GetOpsItem. It introduces new APIs to setup resource policies for SSM resources: PutResourcePolicy, GetResourcePolicies and DeleteResourcePolicy.
* api-change:``transfer``: Allow additional operations to throw ThrottlingException
* api-change:``xray``: This release adds new APIs - PutResourcePolicy, DeleteResourcePolicy, ListResourcePolicies for supporting resource based policies for AWS X-Ray.


1.27.10
=======

* api-change:``connect``: This release updates the APIs: UpdateInstanceAttribute, DescribeInstanceAttribute, and ListInstanceAttributes. You can use it to programmatically enable/disable enhanced contact monitoring using attribute type ENHANCED_CONTACT_MONITORING on the specified Amazon Connect instance.
* api-change:``greengrassv2``: Adds new parent target ARN paramater to CreateDeployment, GetDeployment, and ListDeployments APIs for the new subdeployments feature.
* api-change:``route53``: Amazon Route 53 now supports the Europe (Spain) Region (eu-south-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``ssmsap``: AWS Systems Manager for SAP provides simplified operations and management of SAP applications such as SAP HANA. With this release, SAP customers and partners can automate and simplify their SAP system administration tasks such as backup/restore of SAP HANA.
* api-change:``workspaces``: This release introduces ModifyCertificateBasedAuthProperties, a new API that allows control of certificate-based auth properties associated with a WorkSpaces directory. The DescribeWorkspaceDirectories API will now additionally return certificate-based auth properties in its responses.


1.27.9
======

* api-change:``customer-profiles``: This release enhances the SearchProfiles API by providing functionality to search for profiles using multiple keys and logical operators.
* api-change:``lakeformation``: This release adds a new parameter "Parameters" in the DataLakeSettings.
* api-change:``managedblockchain``: Updating the API docs data type: NetworkEthereumAttributes, and the operations DeleteNode, and CreateNode to also include the supported Goerli network.
* api-change:``proton``: Add support for CodeBuild Provisioning
* api-change:``rds``: This release adds support for restoring an RDS Multi-AZ DB cluster snapshot to a Single-AZ deployment or a Multi-AZ DB instance deployment.
* api-change:``workdocs``: Added 2 new document related operations, DeleteDocumentVersion and RestoreDocumentVersions.
* api-change:``xray``: This release enhances GetServiceGraph API to support new type of edge to represent links between SQS and Lambda in event-driven applications.


1.27.8
======

* api-change:``glue``: Added links related to enabling job bookmarks.
* api-change:``iot``: This release add new api listRelatedResourcesForAuditFinding and new member type IssuerCertificates for Iot device device defender Audit.
* api-change:``license-manager``: AWS License Manager now supports onboarded Management Accounts or Delegated Admins to view granted licenses aggregated from all accounts in the organization.
* api-change:``marketplace-catalog``: Added three new APIs to support tagging and tag-based authorization: TagResource, UntagResource, and ListTagsForResource. Added optional parameters to the StartChangeSet API to support tagging a resource while making a request to create it.
* api-change:``rekognition``: Adding support for ImageProperties feature to detect dominant colors and image brightness, sharpness, and contrast, inclusion and exclusion filters for labels and label categories, new fields to the API response, "aliases" and "categories"
* api-change:``securityhub``: Documentation updates for Security Hub
* api-change:``ssm-incidents``: RelatedItems now have an ID field which can be used for referencing them else where. Introducing event references in TimelineEvent API and increasing maximum length of "eventData" to 12K characters.


1.27.7
======

* api-change:``autoscaling``: This release adds a new price capacity optimized allocation strategy for Spot Instances to help customers optimize provisioning of Spot Instances via EC2 Auto Scaling, EC2 Fleet, and Spot Fleet. It allocates Spot Instances based on both spare capacity availability and Spot Instance price.
* api-change:``ec2``: This release adds a new price capacity optimized allocation strategy for Spot Instances to help customers optimize provisioning of Spot Instances via EC2 Auto Scaling, EC2 Fleet, and Spot Fleet. It allocates Spot Instances based on both spare capacity availability and Spot Instance price.
* api-change:``ecs``: This release adds support for task scale-in protection with updateTaskProtection and getTaskProtection APIs. UpdateTaskProtection API can be used to protect a service managed task from being terminated by scale-in events and getTaskProtection API to get the scale-in protection status of a task.
* api-change:``es``: Amazon OpenSearch Service now offers managed VPC endpoints to connect to your Amazon OpenSearch Service VPC-enabled domain in a Virtual Private Cloud (VPC). This feature allows you to privately access OpenSearch Service domain without using public IPs or requiring traffic to traverse the Internet.
* api-change:``resource-explorer-2``: Text only updates to some Resource Explorer descriptions.
* api-change:``scheduler``: AWS introduces the new Amazon EventBridge Scheduler. EventBridge Scheduler is a serverless scheduler that allows you to create, run, and manage tasks from one central, managed service.


1.27.6
======

* enhancement:docs: Fixes `#6918 <https://github.com/aws/aws-cli/issues/6918>`__ and `#7400 <https://github.com/aws/aws-cli/issues/7400>`__. The CLI falls back on mandoc if groff isn't available.
* api-change:``connect``: This release adds new fields SignInUrl, UserArn, and UserId to GetFederationToken response payload.
* api-change:``connectcases``: This release adds the ability to disable templates through the UpdateTemplate API. Disabling templates prevents customers from creating cases using the template. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``ec2``: Amazon EC2 Trn1 instances, powered by AWS Trainium chips, are purpose built for high-performance deep learning training. u-24tb1.112xlarge and u-18tb1.112xlarge High Memory instances are purpose-built to run large in-memory databases.
* api-change:``groundstation``: This release adds the preview of customer-provided ephemeris support for AWS Ground Station, allowing space vehicle owners to provide their own position and trajectory information for a satellite.
* api-change:``mediapackage-vod``: This release adds "IncludeIframeOnlyStream" for Dash endpoints.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


1.27.5
======

* api-change:``acm``: Support added for requesting elliptic curve certificate key algorithm types P-256 (EC_prime256v1) and P-384 (EC_secp384r1).
* api-change:``billingconductor``: This release adds the Recurring Custom Line Item feature along with a new API ListCustomLineItemVersions.
* api-change:``ec2``: This release enables sharing of EC2 Placement Groups across accounts and within AWS Organizations using Resource Access Manager
* api-change:``fms``: AWS Firewall Manager now supports importing existing AWS Network Firewall firewalls into Firewall Manager policies.
* api-change:``lightsail``: This release adds support for Amazon Lightsail to automate the delegation of domains registered through Amazon Route 53 to Lightsail DNS management and to automate record creation for DNS validation of Lightsail SSL/TLS certificates.
* api-change:``opensearch``: Amazon OpenSearch Service now offers managed VPC endpoints to connect to your Amazon OpenSearch Service VPC-enabled domain in a Virtual Private Cloud (VPC). This feature allows you to privately access OpenSearch Service domain without using public IPs or requiring traffic to traverse the Internet.
* api-change:``polly``: Amazon Polly adds new voices: Elin (sv-SE), Ida (nb-NO), Laura (nl-NL) and Suvi (fi-FI). They are available as neural voices only.
* api-change:``resource-explorer-2``: This is the initial SDK release for AWS Resource Explorer. AWS Resource Explorer lets your users search for and discover your AWS resources across the AWS Regions in your account.
* api-change:``route53``: Amazon Route 53 now supports the Europe (Zurich) Region (eu-central-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


1.27.4
======

* api-change:``athena``: Adds support for using Query Result Reuse
* api-change:``autoscaling``: This release adds support for two new attributes for attribute-based instance type selection - NetworkBandwidthGbps and AllowedInstanceTypes.
* api-change:``cloudtrail``: This release includes support for configuring a delegated administrator to manage an AWS Organizations organization CloudTrail trails and event data stores, and AWS Key Management Service encryption of CloudTrail Lake event data stores.
* api-change:``ec2``: This release adds support for two new attributes for attribute-based instance type selection - NetworkBandwidthGbps and AllowedInstanceTypes.
* api-change:``elasticache``: Added support for IPv6 and dual stack for Memcached and Redis clusters. Customers can now launch new Redis and Memcached clusters with IPv6 and dual stack networking support.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for setting the SDR reference white point for HDR conversions and conversion of HDR10 to DolbyVision without mastering metadata.
* api-change:``ssm``: This release includes support for applying a CloudWatch alarm to multi account multi region Systems Manager Automation
* api-change:``wafv2``: The geo match statement now adds labels for country and region. You can match requests at the region level by combining a geo match statement with label match statements.
* api-change:``wellarchitected``: This release adds support for integrations with AWS Trusted Advisor and AWS Service Catalog AppRegistry to improve workload discovery and speed up your workload reviews.
* api-change:``workspaces``: This release adds protocols attribute to workspaces properties data type. This enables customers to migrate workspaces from PC over IP (PCoIP) to WorkSpaces Streaming Protocol (WSP) using create and modify workspaces public APIs.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


1.27.3
======

* api-change:``ec2``: This release adds API support for the recipient of an AMI account share to remove shared AMI launch permissions.
* api-change:``emr-containers``: Adding support for Job templates. Job templates allow you to create and store templates to configure Spark applications parameters. This helps you ensure consistent settings across applications by reusing and enforcing configuration overrides in data pipelines.
* api-change:``logs``: Doc-only update for bug fixes and support of export to buckets encrypted with SSE-KMS
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


1.27.2
======

* api-change:``memorydb``: Adding support for r6gd instances for MemoryDB Redis with data tiering. In a cluster with data tiering enabled, when available memory capacity is exhausted, the least recently used data is automatically tiered to solid state drives for cost-effective capacity scaling with minimal performance impact.
* api-change:``sagemaker``: Amazon SageMaker now supports running training jobs on ml.trn1 instance types.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


1.27.1
======

* api-change:``iotsitewise``: This release adds the ListAssetModelProperties and ListAssetProperties APIs. You can list all properties that belong to a single asset model or asset using these two new APIs.
* api-change:``s3control``: S3 on Outposts launches support for Lifecycle configuration for Outposts buckets. With S3 Lifecycle configuration, you can mange objects so they are stored cost effectively. You can manage objects using size-based rules and specify how many noncurrent versions bucket will retain.
* api-change:``sagemaker``: This release updates Framework model regex for ModelPackage to support new Framework version xgboost, sklearn.
* api-change:``ssm-incidents``: Adds support for tagging replication-set on creation.


1.27.0
======

* api-change:``rds``: Relational Database Service - This release adds support for configuring Storage Throughput on RDS database instances.
* api-change:``textract``: Add ocr results in AnalyzeIDResponse as blocks
* feature:Endpoints: Migrate all services to use new AWS Endpoint Resolution framework


1.26.5
======

* api-change:``apprunner``: This release adds support for private App Runner services. Services may now be configured to be made private and only accessible from a VPC. The changes include a new VpcIngressConnection resource and several new and modified APIs.
* api-change:``connect``: Amazon connect now support a new API DismissUserContact to dismiss or remove terminated contacts in Agent CCP
* api-change:``ec2``: Elastic IP transfer is a new Amazon VPC feature that allows you to transfer your Elastic IP addresses from one AWS Account to another.
* api-change:``iot``: This release adds the Amazon Location action to IoT Rules Engine.
* api-change:``logs``: SDK release to support tagging for destinations and log groups with TagResource. Also supports tag on create with PutDestination.
* api-change:``sesv2``: This release includes support for interacting with the Virtual Deliverability Manager, allowing you to opt in/out of the feature and to retrieve recommendations and metric data.
* api-change:``textract``: This release introduces additional support for 30+ normalized fields such as vendor address and currency. It also includes OCR output in the response and accuracy improvements for the already supported fields in previous version


1.26.4
======

* api-change:``apprunner``: AWS App Runner adds .NET 6, Go 1, PHP 8.1 and Ruby 3.1 runtimes.
* api-change:``appstream``: This release includes CertificateBasedAuthProperties in CreateDirectoryConfig and UpdateDirectoryConfig.
* api-change:``cloud9``: Update to the documentation section of the Cloud9 API Reference guide.
* api-change:``cloudformation``: This release adds more fields to improves visibility of AWS CloudFormation StackSets information in following APIs: ListStackInstances, DescribeStackInstance, ListStackSetOperationResults, ListStackSetOperations, DescribeStackSetOperation.
* api-change:``gamesparks``: Add LATEST as a possible GameSDK Version on snapshot
* api-change:``mediatailor``: This release introduces support for SCTE-35 segmentation descriptor messages which can be sent within time signal messages.


1.26.3
======

* api-change:``ec2``: Feature supports the replacement of instance root volume using an updated AMI without requiring customers to stop their instance.
* api-change:``fms``: Add support NetworkFirewall Managed Rule Group Override flag in GetViolationDetails API
* api-change:``glue``: Added support for custom datatypes when using custom csv classifier.
* api-change:``redshift``: This release clarifies use for the ElasticIp parameter of the CreateCluster and RestoreFromClusterSnapshot APIs.
* api-change:``sagemaker``: This change allows customers to provide a custom entrypoint script for the docker container to be run while executing training jobs, and provide custom arguments to the entrypoint script.
* api-change:``wafv2``: This release adds the following: Challenge rule action, to silently verify client browsers; rule group rule action override to any valid rule action, not just Count; token sharing between protected applications for challenge/CAPTCHA token; targeted rules option for Bot Control managed rule group.


1.26.2
======

* api-change:``iam``: Doc only update that corrects instances of CLI not using an entity.
* api-change:``kafka``: This release adds support for Tiered Storage. UpdateStorage allows you to control the Storage Mode for supported storage tiers.
* api-change:``neptune``: Added a new cluster-level attribute to set the capacity range for Neptune Serverless instances.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying Grid Search strategy for tuning jobs, which evaluates all hyperparameter combinations exhaustively based on the categorical hyperparameters provided.


1.26.1
======

* api-change:``accessanalyzer``: This release adds support for six new resource types in IAM Access Analyzer to help you easily identify public and cross-account access to your AWS resources. Updated service API, documentation, and paginators.
* api-change:``location``: Added new map styles with satellite imagery for map resources using HERE as a data provider.
* api-change:``mediatailor``: This release is a documentation update
* api-change:``rds``: Relational Database Service - This release adds support for exporting DB cluster data to Amazon S3.
* api-change:``workspaces``: This release adds new enums for supporting Workspaces Core features, including creating Manual running mode workspaces, importing regular Workspaces Core images and importing g4dn Workspaces Core images.


1.26.0
======

* api-change:``acm-pca``: AWS Private Certificate Authority (AWS Private CA) now offers usage modes which are combination of features to address specific use cases.
* api-change:``batch``: This release adds support for AWS Batch on Amazon EKS.
* api-change:``datasync``: Added support for self-signed certificates when using object storage locations; added BytesCompressed to the TaskExecution response.
* api-change:``sagemaker``: SageMaker Inference Recommender now supports a new API ListInferenceRecommendationJobSteps to return the details of all the benchmark we create for an inference recommendation job.
* feature:Endpoints: Implemented new endpoint ruleset system to dynamically derive endpoints and settings for services


1.25.97
=======

* api-change:``cognito-idp``: This release adds a new "DeletionProtection" field to the UserPool in Cognito. Application admins can configure this value with either ACTIVE or INACTIVE value. Setting this field to ACTIVE will prevent a user pool from accidental deletion.
* api-change:``sagemaker``: CreateInferenceRecommenderjob API now supports passing endpoint details directly, that will help customers to identify the max invocation and max latency they can achieve for their model and the associated endpoint along with getting recommendations on other instances.


1.25.96
=======

* api-change:``devops-guru``: This release adds information about the resources DevOps Guru is analyzing.
* api-change:``globalaccelerator``: Global Accelerator now supports AddEndpoints and RemoveEndpoints operations for standard endpoint groups.
* api-change:``resiliencehub``: In this release, we are introducing support for regional optimization for AWS Resilience Hub applications. It also includes a few documentation updates to improve clarity.
* api-change:``rum``: CloudWatch RUM now supports Extended CloudWatch Metrics with Additional Dimensions


1.25.95
=======

* api-change:``chime-sdk-messaging``: Documentation updates for Chime Messaging SDK
* api-change:``cloudtrail``: This release includes support for exporting CloudTrail Lake query results to an Amazon S3 bucket.
* api-change:``config``: This release adds resourceType enums for AppConfig, AppSync, DataSync, EC2, EKS, Glue, GuardDuty, SageMaker, ServiceDiscovery, SES, Route53 types.
* api-change:``connect``: This release adds API support for managing phone numbers that can be used across multiple AWS regions through telephony traffic distribution.
* api-change:``events``: Update events command to latest version
* api-change:``managedblockchain``: Adding new Accessor APIs for Amazon Managed Blockchain
* api-change:``s3``: Updates internal logic for constructing API endpoints. We have added rule-based endpoints and internal model parameters.
* api-change:``s3control``: Updates internal logic for constructing API endpoints. We have added rule-based endpoints and internal model parameters.
* api-change:``support-app``: This release adds the RegisterSlackWorkspaceForOrganization API. You can use the API to register a Slack workspace for an AWS account that is part of an organization.
* api-change:``workspaces-web``: WorkSpaces Web now supports user access logging for recording session start, stop, and URL navigation.


1.25.94
=======

* api-change:``frauddetector``: Documentation Updates for Amazon Fraud Detector
* api-change:``sagemaker``: This change allows customers to enable data capturing while running a batch transform job, and configure monitoring schedule to monitoring the captured data.
* api-change:``servicediscovery``: Updated the ListNamespaces API to support the NAME and HTTP_NAME filters, and the BEGINS_WITH filter condition.
* api-change:``sesv2``: This release allows subscribers to enable Dedicated IPs (managed) to send email via a fully managed dedicated IP experience. It also adds identities' VerificationStatus in the response of GetEmailIdentity and ListEmailIdentities APIs, and ImportJobs counts in the response of ListImportJobs API.


1.25.93
=======

* api-change:``greengrass``: This change allows customers to specify FunctionRuntimeOverride in FunctionDefinitionVersion. This configuration can be used if the runtime on the device is different from the AWS Lambda runtime specified for that function.
* api-change:``sagemaker``: This release adds support for C7g, C6g, C6gd, C6gn, M6g, M6gd, R6g, and R6gn Graviton instance types in Amazon SageMaker Inference.


1.25.92
=======

* bugfix:docs: Fixes `#7338 <https://github.com/aws/aws-cli/issues/7338>`__. Remove global options from topic tags.
* api-change:``mediaconvert``: MediaConvert now supports specifying the minimum percentage of the HRD buffer available at the end of each encoded video segment.


1.25.91
=======

* api-change:``amplifyuibuilder``: We are releasing the ability for fields to be configured as arrays.
* api-change:``appflow``: With this update, you can choose which Salesforce API is used by Amazon AppFlow to transfer data to or from your Salesforce account. You can choose the Salesforce REST API or Bulk API 2.0. You can also choose for Amazon AppFlow to pick the API automatically.
* api-change:``connect``: This release adds support for a secondary email and a mobile number for Amazon Connect instance users.
* api-change:``ds``: This release adds support for describing and updating AWS Managed Microsoft AD set up.
* api-change:``ecs``: Documentation update to address tickets.
* api-change:``guardduty``: Add UnprocessedDataSources to CreateDetectorResponse which specifies the data sources that couldn't be enabled during the CreateDetector request. In addition, update documentations.
* api-change:``iam``: Documentation updates for the AWS Identity and Access Management API Reference.
* api-change:``iotfleetwise``: Documentation update for AWS IoT FleetWise
* api-change:``medialive``: AWS Elemental MediaLive now supports forwarding SCTE-35 messages through the Event Signaling and Management (ESAM) API, and can read those SCTE-35 messages from an inactive source.
* api-change:``mediapackage-vod``: This release adds SPEKE v2 support for MediaPackage VOD. Speke v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, based on an encryption contract selected by the customer.
* api-change:``panorama``: Pause and resume camera stream processing with SignalApplicationInstanceNodeInstances. Reboot an appliance with CreateJobForDevices. More application state information in DescribeApplicationInstance response.
* api-change:``rds-data``: Doc update to reflect no support for schema parameter on BatchExecuteStatement API
* api-change:``ssm-incidents``: Update RelatedItem enum to support Tasks
* api-change:``ssm``: Support of AmazonLinux2022 by Patch Manager
* api-change:``transfer``: This release adds an option for customers to configure workflows that are triggered when files are only partially received from a client due to premature session disconnect.
* api-change:``translate``: This release enables customers to specify multiple target languages in asynchronous batch translation requests.
* api-change:``wisdom``: This release updates the GetRecommendations API to include a trigger event list for classifying and grouping recommendations.


1.25.90
=======

* api-change:``codeguru-reviewer``: Documentation update to replace broken link.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``greengrassv2``: This release adds error status details for deployments and components that failed on a device and adds features to improve visibility into component installation.
* api-change:``quicksight``: Amazon QuickSight now supports SecretsManager Secret ARN in place of CredentialPair for DataSource creation and update. This release also has some minor documentation updates and removes CountryCode as a required parameter in GeoSpatialColumnGroup


1.25.89
=======

* api-change:``resiliencehub``: Documentation change for AWS Resilience Hub. Doc-only update to fix Documentation layout


1.25.88
=======

* api-change:``glue``: This SDK release adds support to sync glue jobs with source control provider. Additionally, a new parameter called SourceControlDetails will be added to Job model.
* api-change:``network-firewall``: StreamExceptionPolicy configures how AWS Network Firewall processes traffic when a network connection breaks midstream
* api-change:``outposts``: This release adds the Asset state information to the ListAssets response. The ListAssets request supports filtering on Asset state.


1.25.87
=======

* api-change:``connect``: Updated the CreateIntegrationAssociation API to support the CASES_DOMAIN IntegrationType.
* api-change:``connectcases``: This release adds APIs for Amazon Connect Cases. Cases allows your agents to quickly track and manage customer issues that require multiple interactions, follow-up tasks, and teams in your contact center.  For more information, see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``ec2``: Added EnableNetworkAddressUsageMetrics flag for ModifyVpcAttribute, DescribeVpcAttribute APIs.
* api-change:``ecs``: Documentation updates to address various Amazon ECS tickets.
* api-change:``s3control``: S3 Object Lambda adds support to allow customers to intercept HeadObject and ListObjects requests and introduce their own compute. These requests were previously proxied to S3.
* api-change:``workmail``: This release adds support for impersonation roles in Amazon WorkMail.


1.25.86
=======

* api-change:``accessanalyzer``: AWS IAM Access Analyzer policy validation introduces new checks for role trust policies. As customers author a policy, IAM Access Analyzer policy validation evaluates the policy for any issues to make it easier for customers to author secure policies.
* api-change:``ec2``: Adding an imdsSupport attribute to EC2 AMIs
* api-change:``snowball``: Adds support for V3_5C. This is a refreshed AWS Snowball Edge Compute Optimized device type with 28TB SSD, 104 vCPU and 416GB memory (customer usable).


1.25.85
=======

* api-change:``codedeploy``: This release allows you to override the alarm configurations when creating a deployment.
* api-change:``devops-guru``: This release adds filter feature on AddNotificationChannel API, enable customer to configure the SNS notification messages by Severity or MessageTypes
* api-change:``dlm``: This release adds support for archival of single-volume snapshots created by Amazon Data Lifecycle Manager policies
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: A new parameter called ExplainerConfig is added to CreateEndpointConfig API to enable SageMaker Clarify online explainability feature.
* api-change:``sso-oidc``: Documentation updates for the IAM Identity Center OIDC CLI Reference.


1.25.84
=======

* api-change:``acm``: This update returns additional certificate details such as certificate SANs and allows sorting in the ListCertificates API.
* api-change:``ec2``: u-3tb1 instances are powered by Intel Xeon Platinum 8176M (Skylake) processors and are purpose-built to run large in-memory databases.
* api-change:``emr-serverless``: This release adds API support to debug Amazon EMR Serverless jobs in real-time with live application UIs
* api-change:``fsx``: This release adds support for Amazon File Cache.
* api-change:``migrationhuborchestrator``: Introducing AWS MigrationHubOrchestrator. This is the first public release of AWS MigrationHubOrchestrator.
* api-change:``polly``: Added support for the new Cantonese voice - Hiujin. Hiujin is available as a Neural voice only.
* api-change:``proton``: This release adds an option to delete pipeline provisioning repositories using the UpdateAccountSettings API
* api-change:``sagemaker``: SageMaker Training Managed Warm Pools let you retain provisioned infrastructure to reduce latency for repetitive training workloads.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``translate``: This release enables customers to access control rights on Translate resources like Parallel Data and Custom Terminology using Tag Based Authorization.
* api-change:``workspaces``: This release includes diagnostic log uploading feature. If it is enabled, the log files of WorkSpaces Windows client will be sent to Amazon WorkSpaces automatically for troubleshooting. You can use modifyClientProperty api to enable/disable this feature.


1.25.83
=======

* api-change:``ce``: This release is to support retroactive Cost Categories. The new field will enable you to retroactively apply new and existing cost category rules to previous months.
* api-change:``kendra``: My AWS Service (placeholder) - Amazon Kendra now provides a data source connector for DropBox. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-dropbox.html
* api-change:``location``: This release adds place IDs, which are unique identifiers of places, along with a new GetPlace operation, which can be used with place IDs to find a place again later. UnitNumber and UnitType are also added as new properties of places.


1.25.82
=======

* api-change:``cur``: This release adds two new support regions(me-central-1/eu-south-2) for OSG.
* api-change:``iotfleetwise``: General availability (GA) for AWS IoT Fleetwise. It adds AWS IoT Fleetwise to AWS SDK. For more information, see https://docs.aws.amazon.com/iot-fleetwise/latest/APIReference/Welcome.html.
* api-change:``ssm``: This release includes support for applying a CloudWatch alarm to Systems Manager capabilities like Automation, Run Command, State Manager, and Maintenance Windows.


1.25.81
=======

* api-change:``apprunner``: AWS App Runner adds a Node.js 16 runtime.
* api-change:``ec2``: Letting external AWS customers provide ImageId as a Launch Template override in FleetLaunchTemplateOverridesRequest
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``lightsail``: This release adds Instance Metadata Service (IMDS) support for Lightsail instances.
* api-change:``nimble``: Amazon Nimble Studio adds support for on-demand Amazon Elastic Compute Cloud (EC2) G3 and G5 instances, allowing customers to utilize additional GPU instance types for their creative projects.
* api-change:``ssm``: This release adds new SSM document types ConformancePackTemplate and CloudFormation
* api-change:``wafv2``: Add the default specification for ResourceType in ListResourcesForWebACL.


1.25.80
=======

* api-change:``backup-gateway``: Changes include: new GetVirtualMachineApi to fetch a single user's VM, improving ListVirtualMachines to fetch filtered VMs as well as all VMs, and improving GetGatewayApi to now also return the gateway's MaintenanceStartTime.
* api-change:``devicefarm``: This release adds the support for VPC-ENI based connectivity for private devices on AWS Device Farm.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``glue``: Added support for S3 Event Notifications for Catalog Target Crawlers.
* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.


1.25.79
=======

* enhancement:Python: Add support for Python 3.11
* api-change:``comprehend``: Amazon Comprehend now supports synchronous mode for targeted sentiment API operations.
* api-change:``s3control``: S3 on Outposts launches support for object versioning for Outposts buckets. With S3 Versioning, you can preserve, retrieve, and restore every version of every object stored in your buckets. You can recover from both unintended user actions and application failures.
* api-change:``sagemaker``: SageMaker now allows customization on Canvas Application settings, including enabling/disabling time-series forecasting and specifying an Amazon Forecast execution role at both the Domain and UserProfile levels.


1.25.78
=======

* api-change:``ec2``: This release adds support for blocked paths to Amazon VPC Reachability Analyzer.


1.25.77
=======

* api-change:``cloudtrail``: This release includes support for importing existing trails into CloudTrail Lake.
* api-change:``ec2``: This release adds CapacityAllocations field to DescribeCapacityReservations
* api-change:``mediaconnect``: This change allows the customer to use the SRT Caller protocol as part of their flows
* api-change:``rds``: This release adds support for Amazon RDS Proxy with SQL Server compatibility.


1.25.76
=======

* api-change:``codestar-notifications``: This release adds tag based access control for the UntagResource API.
* api-change:``ecs``: This release supports new task definition sizes.


1.25.75
=======

* api-change:``dynamodb``: Increased DynamoDB transaction limit from 25 to 100.
* api-change:``ec2``: This feature allows customers to create tags for vpc-endpoint-connections and vpc-endpoint-service-permissions.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying Hyperband strategy for tuning jobs, which uses a multi-fidelity based tuning strategy to stop underperforming hyperparameter configurations early.


1.25.74
=======

* api-change:``amplifyuibuilder``: Amplify Studio UIBuilder is introducing forms functionality. Forms can be configured from Data Store models, JSON, or from scratch. These forms can then be generated in your project and used like any other React components.
* api-change:``ec2``: This update introduces API operations to manage and create local gateway route tables, CoIP pools, and VIF group associations.


1.25.73
=======

* api-change:``customer-profiles``: Added isUnstructured in response for Customer Profiles Integration APIs
* api-change:``drs``: Fixed the data type of lagDuration that is returned in Describe Source Server API
* api-change:``ec2``: Two new features for local gateway route tables: support for static routes targeting Elastic Network Interfaces and direct VPC routing.
* api-change:``evidently``: This release adds support for the client-side evaluation - powered by AWS AppConfig feature.
* api-change:``kendra``: This release enables our customer to choose the option of Sharepoint 2019 for the on-premise Sharepoint connector.
* api-change:``transfer``: This release introduces the ability to have multiple server host keys for any of your Transfer Family servers that use the SFTP protocol.


1.25.72
=======

* api-change:``eks``: Adding support for local Amazon EKS clusters on Outposts


1.25.71
=======

* api-change:``cloudtrail``: This release adds CloudTrail getChannel and listChannels APIs to allow customer to view the ServiceLinkedChannel configurations.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``pi``: Increases the maximum values of two RDS Performance Insights APIs. The maximum value of the Limit parameter of DimensionGroup is 25. The MaxResult maximum is now 25 for the following APIs: DescribeDimensionKeys, GetResourceMetrics, ListAvailableResourceDimensions, and ListAvailableResourceMetrics.
* api-change:``redshift``: This release updates documentation for AQUA features and other description updates.


1.25.70
=======

* api-change:``ec2``: This release adds support to send VPC Flow Logs to kinesis-data-firehose as new destination type
* api-change:``emr-containers``: EMR on EKS now allows running Spark SQL using the newly introduced Spark SQL Job Driver in the Start Job Run API
* api-change:``lookoutmetrics``: Release dimension value filtering feature to allow customers to define dimension filters for including only a subset of their dataset to be used by LookoutMetrics.
* api-change:``medialive``: This change exposes API settings which allow Dolby Atmos and Dolby Vision to be used when running a channel using Elemental Media Live
* api-change:``route53``: Amazon Route 53 now supports the Middle East (UAE) Region (me-central-1) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``sagemaker``: This release adds Mode to AutoMLJobConfig.
* api-change:``ssm``: This release adds support for Systems Manager State Manager Association tagging.


1.25.69
=======

* api-change:``dataexchange``: Documentation updates for AWS Data Exchange.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``eks``: Adds support for EKS Addons ResolveConflicts "preserve" flag. Also adds new update failed status for EKS Addons.
* api-change:``fsx``: Documentation update for Amazon FSx.
* api-change:``inspector2``: This release adds new fields like fixAvailable, fixedInVersion and remediation to the finding model. The requirement to have vulnerablePackages in the finding model has also been removed. The documentation has been updated to reflect these changes.
* api-change:``iotsitewise``: Allow specifying units in Asset Properties
* api-change:``sagemaker``: SageMaker Hosting now allows customization on ML instance storage volume size, model data download timeout and inference container startup ping health check timeout for each ProductionVariant in CreateEndpointConfig API.
* api-change:``sns``: Amazon SNS introduces the Data Protection Policy APIs, which enable customers to attach a data protection policy to an SNS topic. This allows topic owners to enable the new message data protection feature to audit and block sensitive data that is exchanged through their topics.


1.25.68
=======

* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.
* api-change:``sagemaker``: This release adds HyperParameterTuningJob type in Search API.


1.25.67
=======

* api-change:``cognito-idp``: This release adds a new "AuthSessionValidity" field to the UserPoolClient in Cognito. Application admins can configure this value for their users' authentication duration, which is currently fixed at 3 minutes, up to 15 minutes. Setting this field will also apply to the SMS MFA authentication flow.
* api-change:``connect``: This release adds search APIs for Routing Profiles and Queues, which can be used to search for those resources within a Connect Instance.
* api-change:``mediapackage``: Added support for AES_CTR encryption to CMAF origin endpoints
* api-change:``sagemaker``: This release enables administrators to attribute user activity and API calls from Studio notebooks, Data Wrangler and Canvas to specific users even when users share the same execution IAM role.  ExecutionRoleIdentityConfig at Sagemaker domain level enables this feature.


1.25.66
=======

* api-change:``codeguru-reviewer``: Documentation updates to fix formatting issues in CLI and SDK documentation.
* api-change:``controltower``: This release contains the first SDK for AWS Control Tower. It introduces  a new set of APIs: EnableControl, DisableControl, GetControlOperation, and ListEnabledControls.
* api-change:``route53``: Documentation updates for Amazon Route 53.


1.25.65
=======

* api-change:``cloudfront``: Update API documentation for CloudFront origin access control (OAC)
* api-change:``identitystore``: Expand IdentityStore API to support Create, Read, Update, Delete and Get operations for User, Group and GroupMembership resources.
* api-change:``iotthingsgraph``: This release deprecates all APIs of the ThingsGraph service
* api-change:``ivs``: IVS Merge Fragmented Streams. This release adds support for recordingReconnectWindow field in IVS recordingConfigurations. For more information see https://docs.aws.amazon.com/ivs/latest/APIReference/Welcome.html
* api-change:``rds-data``: Documentation updates for RDS Data API
* api-change:``sagemaker``: SageMaker Inference Recommender now accepts Inference Recommender fields: Domain, Task, Framework, SamplePayloadUrl, SupportedContentTypes, SupportedInstanceTypes, directly in our CreateInferenceRecommendationsJob API through ContainerConfig


1.25.64
=======

* api-change:``greengrassv2``: Adds topologyFilter to ListInstalledComponentsRequest which allows filtration of components by ROOT or ALL (including root and dependency components). Adds lastStatusChangeTimestamp to ListInstalledComponents response to show the last time a component changed state on a device.
* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.
* api-change:``lookoutequipment``: This release adds new apis for providing labels.
* api-change:``macie2``: This release of the Amazon Macie API adds support for using allow lists to define specific text and text patterns to ignore when inspecting data sources for sensitive data.
* api-change:``sso-admin``: Documentation updates for the AWS IAM Identity Center CLI Reference.
* api-change:``sso``: Documentation updates for the AWS IAM Identity Center Portal CLI Reference.


1.25.63
=======

* api-change:``fsx``: Documentation updates for Amazon FSx for NetApp ONTAP.
* api-change:``voice-id``: Amazon Connect Voice ID now detects voice spoofing.  When a prospective fraudster tries to spoof caller audio using audio playback or synthesized speech, Voice ID will return a risk score and outcome to indicate the how likely it is that the voice is spoofed.


1.25.62
=======

* enhancement:docs: Generate a usage note for Tagged Union structures.
* api-change:``mediapackage``: This release adds Ads AdTriggers and AdsOnDeliveryRestrictions to describe calls for CMAF endpoints on MediaPackage.
* api-change:``rds``: Removes support for RDS Custom from DBInstanceClass in ModifyDBInstance


1.25.61
=======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``gamelift``: This release adds support for eight EC2 local zones as fleet locations; Atlanta, Chicago, Dallas, Denver, Houston, Kansas City (us-east-1-mci-1a), Los Angeles, and Phoenix. It also adds support for C5d, C6a, C6i, and R5d EC2 instance families.
* api-change:``iotwireless``: This release includes a new feature for the customers to enable the LoRa gateways to send out beacons for Class B devices and an option to select one or more gateways for Class C devices when sending the LoRaWAN downlink messages.
* api-change:``ivschat``: Documentation change for IVS Chat API Reference. Doc-only update to add a paragraph on ARNs to the Welcome section.
* api-change:``panorama``: Support sorting and filtering in ListDevices API, and add more fields to device listings and single device detail
* api-change:``sso-oidc``: Updated required request parameters on IAM Identity Center's OIDC CreateToken action.


1.25.60
=======

* api-change:``cloudfront``: Adds support for CloudFront origin access control (OAC), making it possible to restrict public access to S3 bucket origins in all AWS Regions, those with SSE-KMS, and more.
* api-change:``config``: AWS Config now supports ConformancePackTemplate documents in SSM Docs for the deployment and update of conformance packs.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``ivs``: Documentation Change for IVS API Reference - Doc-only update to type field description for CreateChannel and UpdateChannel actions and for Channel data type. Also added Amazon Resource Names (ARNs) paragraph to Welcome section.
* api-change:``quicksight``: Added a new optional property DashboardVisual under ExperienceConfiguration parameter of GenerateEmbedUrlForAnonymousUser and GenerateEmbedUrlForRegisteredUser API operations. This supports embedding of specific visuals in QuickSight dashboards.
* api-change:``transfer``: Documentation updates for AWS Transfer Family


1.25.59
=======

* api-change:``rds``: RDS for Oracle supports Oracle Data Guard switchover and read replica backups.
* api-change:``sso-admin``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)


1.25.58
=======

* api-change:``docdb``: Update document for volume clone
* api-change:``ec2``: R6a instances are powered by 3rd generation AMD EPYC (Milan) processors delivering all-core turbo frequency of 3.6 GHz. C6id, M6id, and R6id instances are powered by 3rd generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz.
* api-change:``forecast``: releasing What-If Analysis APIs and update ARN regex pattern to be more strict in accordance with security recommendation
* api-change:``forecastquery``: releasing What-If Analysis APIs
* api-change:``iotsitewise``: Enable non-unique asset names under different hierarchies
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for AwsBackupBackupVault, AwsBackupBackupPlan and AwsBackupRecoveryPoint. Added FixAvailable, FixedInVersion and Remediation  to Vulnerability.
* api-change:``support-app``: This is the initial SDK release for the AWS Support App in Slack.


1.25.57
=======

* enhancement:docs: Differentiate between regular and streaming blobs and generate a usage note when a parameter is of streaming blob type.
* enhancement:docs: Improve AWS CLI docs to include global options available to service commands.
* api-change:``connect``: This release adds SearchSecurityProfiles API which can be used to search for Security Profile resources within a Connect Instance.
* api-change:``ivschat``: Documentation Change for IVS Chat API Reference - Doc-only update to change text/description for tags field.
* api-change:``kendra``: This release adds support for a new authentication type - Personal Access Token (PAT) for confluence server.
* api-change:``lookoutmetrics``: This release is to make GetDataQualityMetrics API publicly available.


1.25.56
=======

* enhancement:Endpoints: Enforce SSL common name as default endpoint url
* api-change:``chime-sdk-media-pipelines``: The Amazon Chime SDK now supports live streaming of real-time video from the Amazon Chime SDK sessions to streaming platforms such as Amazon IVS and Amazon Elemental MediaLive. We have also added support for concatenation to create a single media capture file.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``cognito-idp``: This change is being made simply to fix the public documentation based on the models. We have included the PasswordChange and ResendCode events, along with the Pass, Fail and InProgress status. We have removed the Success and Failure status which are never returned by our APIs.
* api-change:``dynamodb``: This release adds support for importing data from S3 into a new DynamoDB table
* api-change:``ec2``: This release adds support for VPN log options , a new feature allowing S2S VPN connections to send IKE activity logs to CloudWatch Logs
* api-change:``networkmanager``: Add TransitGatewayPeeringAttachmentId property to TransitGatewayPeering Model


1.25.55
=======

* bugfix:``configure``: Fix regression in not being able to set configuration values for new profile (fixes `#7199 <https://github.com/aws/aws-cli/issues/7199>`__)


1.25.54
=======

* enhancement:Endpoints: Enforce SSL common name as default endpoint url
* api-change:``appmesh``: AWS App Mesh release to support Multiple Listener and Access Log Format feature
* api-change:``connectcampaigns``: Updated exceptions for Amazon Connect Outbound Campaign api's.
* api-change:``kendra``: This release adds Zendesk connector (which allows you to specify Zendesk SAAS platform as data source), Proxy Support for Sharepoint and Confluence Server (which allows you to specify the proxy configuration if proxy is required to connect to your Sharepoint/Confluence Server as data source).
* api-change:``lakeformation``: This release adds a new API support "AssumeDecoratedRoleWithSAML" and also release updates the corresponding documentation.
* api-change:``lambda``: Added support for customization of Consumer Group ID for MSK and Kafka Event Source Mappings.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``rds``: Adds support for Internet Protocol Version 6 (IPv6) for RDS Aurora database clusters.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager.


1.25.53
=======

* api-change:``rekognition``: This release adds APIs which support copying an Amazon Rekognition Custom Labels model and managing project policies across AWS account.
* api-change:``servicecatalog``: Documentation updates for Service Catalog


1.25.52
=======

* api-change:``cloudfront``: Adds Http 3 support to distributions
* api-change:``identitystore``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``sso``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``wisdom``: This release introduces a new API PutFeedback that allows submitting feedback to Wisdom on content relevance.


1.25.51
=======

* api-change:``amp``: This release adds log APIs that allow customers to manage logging for their Amazon Managed Service for Prometheus workspaces.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports channels with up to one million participants with elastic channels.
* api-change:``ivs``: Updates various list api MaxResults ranges
* api-change:``personalize-runtime``: This release provides support for promotions in AWS Personalize runtime.
* api-change:``rds``: Adds support for RDS Custom to DBInstanceClass in ModifyDBInstance


1.25.50
=======

* api-change:``backupstorage``: This is the first public release of AWS Backup Storage. We are exposing some previously-internal APIs for use by external services. These APIs are not meant to be used directly by customers.
* api-change:``glue``: Add support for Python 3.9 AWS Glue Python Shell jobs
* api-change:``privatenetworks``: This is the initial SDK release for AWS Private 5G. AWS Private 5G is a managed service that makes it easy to deploy, operate, and scale your own private mobile network at your on-premises location.


1.25.49
=======

* api-change:``dlm``: This release adds support for excluding specific data (non-boot) volumes from multi-volume snapshot sets created by snapshot lifecycle policies
* api-change:``ec2``: This release adds support for excluding specific data (non-root) volumes from multi-volume snapshot sets created from instances.


1.25.48
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``location``: Amazon Location Service now allows circular geofences in BatchPutGeofence, PutGeofence, and GetGeofence  APIs.
* api-change:``sagemaker-a2i-runtime``: Fix bug with parsing ISO-8601 CreationTime in Java SDK in DescribeHumanLoop
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying multiple alternate EC2 instance types to make tuning jobs more robust when the preferred instance type is not available due to insufficient capacity.


1.25.47
=======

* api-change:``glue``: Add an option to run non-urgent or non-time sensitive Glue Jobs on spare capacity
* api-change:``identitystore``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``iotwireless``: AWS IoT Wireless release support for sidewalk data reliability.
* api-change:``pinpoint``: Adds support for Advance Quiet Time in Journeys. Adds RefreshOnSegmentUpdate and WaitForQuietTime to JourneyResponse.
* api-change:``quicksight``: A series of documentation updates to the QuickSight API reference.
* api-change:``sso-admin``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``sso-oidc``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``sso``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)


1.25.46
=======

* api-change:``chime-sdk-meetings``: Adds support for Tags on Amazon Chime SDK WebRTC sessions
* api-change:``config``: Add resourceType enums for Athena, GlobalAccelerator, Detective and EC2 types
* api-change:``dms``: Documentation updates for Database Migration Service (DMS).
* api-change:``iot``: The release is to support attach a provisioning template to CACert for JITP function,  Customer now doesn't have to hardcode a roleArn and templateBody during register a CACert to enable JITP.


1.25.45
=======

* api-change:``cognito-idp``: Add a new exception type, ForbiddenException, that is returned when request is not allowed
* api-change:``wafv2``: You can now associate an AWS WAF web ACL with an Amazon Cognito user pool.


1.25.44
=======

* api-change:``license-manager-user-subscriptions``: This release supports user based subscription for Microsoft Visual Studio Professional and Enterprise on EC2.
* api-change:``personalize``: This release adds support for incremental bulk ingestion for the Personalize CreateDatasetImportJob API.


1.25.43
=======

* api-change:``config``: Documentation update for PutConfigRule and PutOrganizationConfigRule
* api-change:``workspaces``: This release introduces ModifySamlProperties, a new API that allows control of SAML properties associated with a WorkSpaces directory. The DescribeWorkspaceDirectories API will now additionally return SAML properties in its responses.


1.25.42
=======

* bugfix:TraceId: Rollback bugfix for obeying _X_AMZN_TRACE_ID env var


1.25.41
=======

* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``fsx``: Documentation updates for Amazon FSx
* api-change:``shield``: AWS Shield Advanced now supports filtering for ListProtections and ListProtectionGroups.


1.25.40
=======

* api-change:``ec2``: Documentation updates for VM Import/Export.
* api-change:``es``: This release adds support for gp3 EBS (Elastic Block Store) storage.
* api-change:``lookoutvision``: This release introduces support for image segmentation models and updates CPU accelerator options for models hosted on edge devices.
* api-change:``opensearch``: This release adds support for gp3 EBS (Elastic Block Store) storage.


1.25.39
=======

* api-change:``auditmanager``: This release adds an exceeded quota exception to several APIs. We added a ServiceQuotaExceededException for the following operations: CreateAssessment, CreateControl, CreateAssessmentFramework, and UpdateAssessmentStatus.
* api-change:``chime``: Chime VoiceConnector will now support ValidateE911Address which will allow customers to prevalidate their addresses included in their SIP invites for emergency calling
* api-change:``config``: This release adds ListConformancePackComplianceScores API to support the new compliance score feature, which provides a percentage of the number of compliant rule-resource combinations in a conformance pack compared to the number of total possible rule-resource combinations in the conformance pack.
* api-change:``globalaccelerator``: Global Accelerator now supports dual-stack accelerators, enabling support for IPv4 and IPv6 traffic.
* api-change:``marketplace-catalog``: The SDK for the StartChangeSet API will now automatically set and use an idempotency token in the ClientRequestToken request parameter if the customer does not provide it.
* api-change:``polly``: Amazon Polly adds new English and Hindi voice - Kajal. Kajal is available as Neural voice only.
* api-change:``ssm``: Adding doc updates for OpsCenter support in Service Setting actions.
* api-change:``workspaces``: Added CreateWorkspaceImage API to create a new WorkSpace image from an existing WorkSpace.


1.25.38
=======

* api-change:``appsync``: Adds support for a new API to evaluate mapping templates with mock data, allowing you to remotely unit test your AppSync resolvers and functions.
* api-change:``detective``: Added the ability to get data source package information for the behavior graph. Graph administrators can now start (or stop) optional datasources on the behavior graph.
* api-change:``guardduty``: Amazon GuardDuty introduces a new Malware Protection feature that triggers malware scan on selected EC2 instance resources, after the service detects a potentially malicious activity.
* api-change:``lookoutvision``: This release introduces support for the automatic scaling of inference units used by Amazon Lookout for Vision models.
* api-change:``macie2``: This release adds support for retrieving (revealing) sample occurrences of sensitive data that Amazon Macie detects and reports in findings.
* api-change:``rds``: Adds support for using RDS Proxies with RDS for MariaDB databases.
* api-change:``rekognition``: This release introduces support for the automatic scaling of inference units used by Amazon Rekognition Custom Labels models.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``transfer``: AWS Transfer Family now supports Applicability Statement 2 (AS2), a network protocol used for the secure and reliable transfer of critical Business-to-Business (B2B) data over the public internet using HTTP/HTTPS as the transport mechanism.


1.25.37
=======

* api-change:``autoscaling``: Documentation update for Amazon EC2 Auto Scaling.


1.25.36
=======

* api-change:``account``: This release enables customers to manage the primary contact information for their AWS accounts. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/API_Operations.html
* api-change:``ec2``: Added support for EC2 M1 Mac instances. For more information, please visit aws.amazon.com/mac.
* api-change:``iotdeviceadvisor``: Added new service feature (Early access only) - Long Duration Test, where customers can test the IoT device to observe how it behaves when the device is in operation for longer period.
* api-change:``medialive``: Link devices now support remote rebooting. Link devices now support maintenance windows. Maintenance windows allow a Link device to install software updates without stopping the MediaLive channel. The channel will experience a brief loss of input from the device while updates are installed.
* api-change:``rds``: This release adds the "ModifyActivityStream" API with support for audit policy state locking and unlocking.
* api-change:``transcribe``: Remove unsupported language codes for StartTranscriptionJob and update VocabularyFileUri for UpdateMedicalVocabulary


1.25.35
=======

* api-change:``athena``: This feature allows customers to retrieve runtime statistics for completed queries
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``dms``: Documentation updates for Database Migration Service (DMS).
* api-change:``docdb``: Enable copy-on-write restore type
* api-change:``ec2-instance-connect``: This release includes a new exception type "EC2InstanceUnavailableException" for SendSSHPublicKey and SendSerialConsoleSSHPublicKey APIs.
* api-change:``frauddetector``: The release introduces Account Takeover Insights (ATI) model. The ATI model detects fraud relating to account takeover. This release also adds support for new variable types: ARE_CREDENTIALS_VALID and SESSION_ID and adds new structures to Model Version APIs.
* api-change:``iotsitewise``: Added asynchronous API to ingest bulk historical and current data into IoT SiteWise.
* api-change:``kendra``: Amazon Kendra now provides Oauth2 support for SharePoint Online. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-sharepoint.html
* api-change:``network-firewall``: Network Firewall now supports referencing dynamic IP sets from stateful rule groups, for IP sets stored in Amazon VPC prefix lists.
* api-change:``rds``: Adds support for creating an RDS Proxy for an RDS for MariaDB database.


1.25.34
=======

* api-change:``acm-pca``: AWS Certificate Manager (ACM) Private Certificate Authority (PCA) documentation updates
* api-change:``iot``: GA release the ability to enable/disable IoT Fleet Indexing for Device Defender and Named Shadow information, and search them through IoT Fleet Indexing APIs. This includes Named Shadow Selection as a part of the UpdateIndexingConfiguration API.


1.25.33
=======

* api-change:``devops-guru``: Added new APIs for log anomaly detection feature.
* api-change:``glue``: Documentation updates for AWS Glue Job Timeout and Autoscaling
* api-change:``sagemaker-edge``: Amazon SageMaker Edge Manager provides lightweight model deployment feature to deploy machine learning models on requested devices.
* api-change:``sagemaker``: Fixed an issue with cross account QueryLineage
* api-change:``workspaces``: Increased the character limit of the login message from 850 to 2000 characters.


1.25.32
=======

* api-change:``discovery``: Add AWS Agentless Collector details to the GetDiscoverySummary API response
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``elasticache``: Adding AutoMinorVersionUpgrade in the DescribeReplicationGroups API
* api-change:``kms``: Added support for the SM2 KeySpec in China Partition Regions
* api-change:``mediapackage``: This release adds "IncludeIframeOnlyStream" for Dash endpoints and increases the number of supported video and audio encryption presets for Speke v2
* api-change:``sagemaker``: Amazon SageMaker Edge Manager provides lightweight model deployment feature to deploy machine learning models on requested devices.
* api-change:``sso-admin``: AWS SSO now supports attaching customer managed policies and a permissions boundary to your permission sets. This release adds new API operations to manage and view the customer managed policies and the permissions boundary for a given permission set.


1.25.31
=======

* api-change:``datasync``: Documentation updates for AWS DataSync regarding configuring Amazon FSx for ONTAP location security groups and SMB user permissions.
* api-change:``drs``: Changed existing APIs to allow choosing a dynamic volume type for replicating volumes, to reduce costs for customers.
* api-change:``evidently``: This release adds support for the new segmentation feature.
* api-change:``wafv2``: This SDK release provide customers ability to add sensitivity level for WAF SQLI Match Statements.


1.25.30
=======

* api-change:``athena``: This release updates data types that contain either QueryExecutionId, NamedQueryId or ExpectedBucketOwner. Ids must be between 1 and 128 characters and contain only non-whitespace characters. ExpectedBucketOwner must be 12-digit string.
* api-change:``codeartifact``: This release introduces Package Origin Controls, a mechanism used to counteract Dependency Confusion attacks. Adds two new APIs, PutPackageOriginConfiguration and DescribePackage, and updates the ListPackage, DescribePackageVersion and ListPackageVersion APIs in support of the feature.
* api-change:``config``: Update ResourceType enum with values for Route53Resolver, Batch, DMS, Workspaces, Stepfunctions, SageMaker, ElasticLoadBalancingV2, MSK types
* api-change:``ec2``: This release adds flow logs for Transit Gateway to  allow customers to gain deeper visibility and insights into network traffic through their Transit Gateways.
* api-change:``fms``: Adds support for strict ordering in stateful rule groups in Network Firewall policies.
* api-change:``glue``: This release adds an additional worker type for Glue Streaming jobs.
* api-change:``inspector2``: This release adds support for Inspector V2 scan configurations through the get and update configuration APIs. Currently this allows configuring ECR automated re-scan duration to lifetime or 180 days or 30 days.
* api-change:``kendra``: This release adds AccessControlConfigurations which allow you to redefine your document level access control without the need for content re-indexing.
* api-change:``nimble``: Amazon Nimble Studio adds support for IAM-based access to AWS resources for Nimble Studio components and custom studio components. Studio Component scripts use these roles on Nimble Studio workstation to mount filesystems, access S3 buckets, or other configured resources in the Studio's AWS account
* api-change:``outposts``: This release adds the ShipmentInformation and AssetInformationList fields to the GetOrder API response.
* api-change:``sagemaker``: This release adds support for G5, P4d, and C6i instance types in Amazon SageMaker Inference and increases the number of hyperparameters that can be searched from 20 to 30 in Amazon SageMaker Automatic Model Tuning


1.25.29
=======

* api-change:``appconfig``: Adding Create, Get, Update, Delete, and List APIs for new two new resources: Extensions and ExtensionAssociations.


1.25.28
=======

* api-change:``networkmanager``: This release adds general availability API support for AWS Cloud WAN.


1.25.27
=======

* api-change:``ec2``: Build, manage, and monitor a unified global network that connects resources running across your cloud and on-premises environments using the AWS Cloud WAN APIs.
* api-change:``redshift-serverless``: Removed prerelease language for GA launch.
* api-change:``redshift``: This release adds a new --snapshot-arn field for describe-cluster-snapshots, describe-node-configuration-options, restore-from-cluster-snapshot, authorize-snapshot-acsess, and revoke-snapshot-acsess APIs. It allows customers to give a Redshift snapshot ARN or a Redshift Serverless ARN as input.


1.25.26
=======

* api-change:``backup``: This release adds support for authentication using IAM user identity instead of passed IAM role, identified by excluding the IamRoleArn field in the StartRestoreJob API. This feature applies to only resource clients with a destructive restore nature (e.g. SAP HANA).


1.25.25
=======

* api-change:``chime-sdk-meetings``: Adds support for AppKeys and TenantIds in Amazon Chime SDK WebRTC sessions
* api-change:``dms``: New api to migrate event subscriptions to event bridge rules
* api-change:``iot``: This release adds support to register a CA certificate without having to provide a verification certificate. This also allows multiple AWS accounts to register the same CA in the same region.
* api-change:``iotwireless``: Adds 5 APIs: PutPositionConfiguration, GetPositionConfiguration, ListPositionConfigurations, UpdatePosition, GetPosition for the new Positioning Service feature which enables customers to configure solvers to calculate position of LoRaWAN devices, or specify position of LoRaWAN devices & gateways.
* api-change:``sagemaker``: Heterogeneous clusters: the ability to launch training jobs with multiple instance types. This enables running component of the training job on the instance type that is most suitable for it. e.g. doing data processing and augmentation on CPU instances and neural network training on GPU instances


1.25.24
=======

* api-change:``cloudformation``: My AWS Service (placeholder) - Add a new feature Account-level Targeting for StackSet operation
* api-change:``synthetics``: This release introduces Group feature, which enables users to group cross-region canaries.


1.25.23
=======

* api-change:``config``: Updating documentation service limits
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``quicksight``: This release allows customers to programmatically create QuickSight accounts with Enterprise and Enterprise + Q editions. It also releases allowlisting domains for embedding QuickSight dashboards at runtime through the embedding APIs.
* api-change:``rds``: Adds waiters support for DBCluster.
* api-change:``rolesanywhere``: IAM Roles Anywhere allows your workloads such as servers, containers, and applications to obtain temporary AWS credentials and use the same IAM roles and policies that you have configured for your AWS workloads to access AWS resources.
* api-change:``ssm-incidents``: Adds support for tagging incident-record on creation by providing incident tags in the template within a response-plan.


1.25.22
=======

* api-change:``dms``: Added new features for AWS DMS version 3.4.7 that includes new endpoint settings for S3, OpenSearch, Postgres, SQLServer and Oracle.
* api-change:``rds``: Adds support for additional retention periods to Performance Insights.


1.25.21
=======

* api-change:``athena``: This feature introduces the API support for Athena's parameterized query and BatchGetPreparedStatement API.
* api-change:``customer-profiles``: This release adds the optional MinAllowedConfidenceScoreForMerging parameter to the CreateDomain, UpdateDomain, and GetAutoMergingPreview APIs in Customer Profiles. This parameter is used as a threshold to influence the profile auto-merging step of the Identity Resolution process.
* api-change:``emr``: Update emr command to latest version
* api-change:``glue``: This release adds tag as an input of CreateDatabase
* api-change:``kendra``: Amazon Kendra now provides a data source connector for alfresco
* api-change:``mwaa``: Documentation updates for Amazon Managed Workflows for Apache Airflow.
* api-change:``pricing``: Documentation update for GetProducts Response.
* api-change:``wellarchitected``: Added support for UpdateGlobalSettings API. Added status filter to ListWorkloadShares and ListLensShares.
* api-change:``workmail``: This release adds support for managing user availability configurations in Amazon WorkMail.


1.25.20
=======

* api-change:``appstream``: Includes support for StreamingExperienceSettings in CreateStack and UpdateStack APIs
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``medialive``: This release adds support for automatic renewal of MediaLive reservations at the end of each reservation term. Automatic renewal is optional. This release also adds support for labelling accessibility-focused audio and caption tracks in HLS outputs.
* api-change:``redshift-serverless``: Add new API operations for Amazon Redshift Serverless, a new way of using Amazon Redshift without needing to manually manage provisioned clusters. The new operations let you interact with Redshift Serverless resources, such as create snapshots, list VPC endpoints, delete resource policies, and more.
* api-change:``sagemaker``: This release adds: UpdateFeatureGroup, UpdateFeatureMetadata, DescribeFeatureMetadata APIs; FeatureMetadata type in Search API; LastModifiedTime, LastUpdateStatus, OnlineStoreTotalSizeBytes in DescribeFeatureGroup API.
* api-change:``translate``: Added ListLanguages API which can be used to list the languages supported by Translate.


1.25.19
=======

* api-change:``datasync``: AWS DataSync now supports Amazon FSx for NetApp ONTAP locations.
* api-change:``ec2``: This release adds a new spread placement group to EC2 Placement Groups: host level spread, which spread instances between physical hosts, available to Outpost customers only. CreatePlacementGroup and DescribePlacementGroups APIs were updated with a new parameter: SpreadLevel to support this feature.
* api-change:``finspace-data``: Release new API GetExternalDataViewAccessDetails
* api-change:``polly``: Add 4 new neural voices - Pedro (es-US), Liam (fr-CA), Daniel (de-DE) and Arthur (en-GB).


1.25.18
=======

* api-change:``iot``: This release ease the restriction for the input of tag value to align with AWS standard, now instead of min length 1, we change it to min length 0.


1.25.17
=======

* api-change:``glue``: This release enables the new ListCrawls API for viewing the AWS Glue Crawler run history.
* api-change:``rds-data``: Documentation updates for RDS Data API


1.25.16
=======

* api-change:``lookoutequipment``: This release adds visualizations to the scheduled inference results. Users will be able to see interference results, including diagnostic results from their running inference schedulers.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has released support for automatic DolbyVision metadata generation when converting HDR10 to DolbyVision.
* api-change:``mgn``: New and modified APIs for the Post-Migration Framework
* api-change:``migration-hub-refactor-spaces``: This release adds the new API UpdateRoute that allows route to be updated to ACTIVE/INACTIVE state. In addition, CreateRoute API will now allow users to create route in ACTIVE/INACTIVE state.
* api-change:``sagemaker``: SageMaker Ground Truth now supports Virtual Private Cloud. Customers can launch labeling jobs and access to their private workforce in VPC mode.


1.25.15
=======

* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``pricing``: This release introduces 1 update to the GetProducts API. The serviceCode attribute is now required when you use the GetProductsRequest.
* api-change:``transfer``: Until today, the service supported only RSA host keys and user keys. Now with this launch, Transfer Family has expanded the support for ECDSA and ED25519 host keys and user keys, enabling customers to support a broader set of clients by choosing RSA, ECDSA, and ED25519 host and user keys.


1.25.14
=======

* api-change:``ec2``: This release adds support for Private IP VPNs, a new feature allowing S2S VPN connections to use private ip addresses as the tunnel outside ip address over Direct Connect as transport.
* api-change:``ecs``: Amazon ECS UpdateService now supports the following parameters: PlacementStrategies, PlacementConstraints and CapacityProviderStrategy.
* api-change:``wellarchitected``: Adds support for lens tagging, Adds support for multiple helpful-resource urls and multiple improvement-plan urls.


1.25.13
=======

* api-change:``ds``: This release adds support for describing and updating AWS Managed Microsoft AD settings
* api-change:``kafka``: Documentation updates to use Az Id during cluster creation.
* api-change:``outposts``: This release adds the AssetLocation structure to the ListAssets response. AssetLocation includes the RackElevation for an Asset.


1.25.12
=======

* api-change:``connect``: This release updates these APIs: UpdateInstanceAttribute, DescribeInstanceAttribute and ListInstanceAttributes. You can use it to programmatically enable/disable High volume outbound communications using attribute type HIGH_VOLUME_OUTBOUND on the specified Amazon Connect instance.
* api-change:``connectcampaigns``: Added Amazon Connect high volume outbound communications SDK.
* api-change:``dynamodb``: Doc only update for DynamoDB service
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version


1.25.11
=======

* api-change:``redshift-data``: This release adds a new --workgroup-name field to operations that connect to an endpoint. Customers can now execute queries against their serverless workgroups.
* api-change:``redshiftserverless``: Add new API operations for Amazon Redshift Serverless, a new way of using Amazon Redshift without needing to manually manage provisioned clusters. The new operations let you interact with Redshift Serverless resources, such as create snapshots, list VPC endpoints, delete resource policies, and more.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``securityhub``: Added Threats field for security findings. Added new resource details for ECS Container, ECS Task, RDS SecurityGroup, Kinesis Stream, EC2 TransitGateway, EFS AccessPoint, CloudFormation Stack, CloudWatch Alarm, VPC Peering Connection and WAF Rules


1.25.10
=======

* api-change:``finspace-data``: This release adds a new set of APIs, GetPermissionGroup, DisassociateUserFromPermissionGroup, AssociateUserToPermissionGroup, ListPermissionGroupsByUser, ListUsersByPermissionGroup.
* api-change:``guardduty``: Adds finding fields available from GuardDuty Console. Adds FreeTrial related operations. Deprecates the use of various APIs related to Master Accounts and Replace them with Administrator Accounts.
* api-change:``servicecatalog-appregistry``: This release adds a new API ListAttributeGroupsForApplication that returns associated attribute groups of an application. In addition, the UpdateApplication and UpdateAttributeGroup APIs will not allow users to update the 'Name' attribute.
* api-change:``workspaces``: Added new field "reason" to OperationNotSupportedException. Receiving this exception in the DeregisterWorkspaceDirectory API will now return a reason giving more context on the failure.


1.25.9
======

* api-change:``budgets``: Add a budgets ThrottlingException. Update the CostFilters value pattern.
* api-change:``lookoutmetrics``: Adding filters to Alert and adding new UpdateAlert API.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for rules that constrain Automatic-ABR rendition selection when generating ABR package ladders.


1.25.8
======

* api-change:``outposts``: This release adds API operations AWS uses to install Outpost servers.


1.25.7
======

* api-change:``frauddetector``: Documentation updates for Amazon Fraud Detector (AWSHawksNest)


1.25.6
======

* api-change:``chime-sdk-meetings``: Adds support for live transcription in AWS GovCloud (US) Regions.


1.25.5
======

* api-change:``dms``: This release adds DMS Fleet Advisor APIs and exposes functionality for DMS Fleet Advisor. It adds functionality to create and modify fleet advisor instances, and to collect and analyze information about the local data infrastructure.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``m2``: AWS Mainframe Modernization service is a managed mainframe service and set of tools for planning, migrating, modernizing, and running mainframe workloads on AWS
* api-change:``neptune``: This release adds support for Neptune to be configured as a global database, with a primary DB cluster in one region, and up to five secondary DB clusters in other regions.
* api-change:``redshift-serverless``: Add new API operations for Amazon Redshift Serverless, a new way of using Amazon Redshift without needing to manually manage provisioned clusters. The new operations let you interact with Redshift Serverless resources, such as create snapshots, list VPC endpoints, delete resource policies, and more.
* api-change:``redshift``: Adds new API GetClusterCredentialsWithIAM to return temporary credentials.


1.25.4
======

* api-change:``auditmanager``: This release introduces 2 updates to the Audit Manager API. The roleType and roleArn attributes are now required when you use the CreateAssessment or UpdateAssessment operation. We also added a throttling exception to the RegisterAccount API operation.
* api-change:``ce``: Added two new APIs to support cost allocation tags operations: ListCostAllocationTags, UpdateCostAllocationTagsStatus.


1.25.3
======

* api-change:``chime-sdk-messaging``: This release adds support for searching channels by members via the SearchChannels API, removes required restrictions for Name and Mode in UpdateChannel API and enhances CreateChannel API by exposing member and moderator list as well as channel id as optional parameters.
* api-change:``connect``: This release adds a new API, GetCurrentUserData, which returns real-time details about users' current activity.


1.25.2
======

* api-change:``connect``: This release adds the following features: 1) New APIs to manage (create, list, update) task template resources, 2) Updates to startTaskContact API to support task templates, and 3) new TransferContact API to programmatically transfer in-progress tasks via a contact flow.
* api-change:``proton``: Add new "Components" API to enable users to Create, Delete and Update AWS Proton components.
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``application-insights``: Provide Account Level onboarding support through CFN/CLI
* api-change:``kendra``: Amazon Kendra now provides a data source connector for GitHub. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-github.html
* api-change:``voice-id``: Added a new attribute ServerSideEncryptionUpdateDetails to Domain and DomainSummary.


1.25.1
======

* api-change:``route53``: Add new APIs to support Route 53 IP Based Routing
* api-change:``forecast``: Added Format field to Import and Export APIs in Amazon Forecast. Added TimeSeriesSelector to Create Forecast API.
* api-change:``chime-sdk-meetings``: Adds support for centrally controlling each participant's ability to send and receive audio, video and screen share within a WebRTC session.  Attendee capabilities can be specified when the attendee is created and updated during the session with the new BatchUpdateAttendeeCapabilitiesExcept API.
* api-change:``backup-gateway``: Adds GetGateway and UpdateGatewaySoftwareNow API and adds hypervisor name to UpdateHypervisor API


1.25.0
======

* api-change:``lookoutmetrics``: Adding backtest mode to detectors using the Cloudwatch data source.
* api-change:``transcribe``: Amazon Transcribe now supports automatic language identification for multi-lingual audio in batch mode.
* api-change:``iotsitewise``: This release adds the following new optional field to the IoT SiteWise asset resource: assetDescription.
* api-change:``sagemaker``: Amazon SageMaker Notebook Instances now support Jupyter Lab 3.
* feature:Python: Dropped support for Python 3.6
* api-change:``drs``: Changed existing APIs and added new APIs to accommodate using multiple AWS accounts with AWS Elastic Disaster Recovery.
* api-change:``cognito-idp``: Amazon Cognito now supports IP Address propagation for all unauthenticated APIs (e.g. SignUp, ForgotPassword).
* feature:Python: Dropped support for Python 3.6


1.24.10
=======

* api-change:``appflow``: Adding the following features/changes: Parquet output that preserves typing from the source connector, Failed executions threshold before deactivation for scheduled flows, increasing max size of access and refresh token from 2048 to 4096
* api-change:``sagemaker``: Amazon SageMaker Notebook Instances now allows configuration of Instance Metadata Service version and Amazon SageMaker Studio now supports G5 instance types.
* api-change:``datasync``: AWS DataSync now supports TLS encryption in transit, file system policies and access points for EFS locations.
* api-change:``emr-serverless``: This release adds support for Amazon EMR Serverless, a serverless runtime environment that simplifies running analytics applications using the latest open source frameworks such as Apache Spark and Apache Hive.


1.24.9
======

* api-change:``ec2``: C7g instances, powered by the latest generation AWS Graviton3 processors, provide the best price performance in Amazon EC2 for compute-intensive workloads.
* api-change:``emr-serverless``: This release adds support for Amazon EMR Serverless, a serverless runtime environment that simplifies running analytics applications using the latest open source frameworks such as Apache Spark and Apache Hive.
* api-change:``forecast``: Introduced a new field in Auto Predictor as Time Alignment Boundary. It helps in aligning the timestamps generated during Forecast exports
* api-change:``lightsail``: Amazon Lightsail now supports the ability to configure a Lightsail Container Service to pull images from Amazon ECR private repositories in your account.


1.24.8
======

* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for manually selecting features from the input dataset using the CreateAutoMLJob API.
* api-change:``apprunner``: Documentation-only update added for CodeConfiguration.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``fsx``: This release adds root squash support to FSx for Lustre to restrict root level access from clients by mapping root users to a less-privileged user/group with limited permissions.
* api-change:``lookoutmetrics``: Adding AthenaSourceConfig for MetricSet APIs to support Athena as a data source.
* api-change:``voice-id``: VoiceID will now automatically expire Speakers if they haven't been accessed for Enrollment, Re-enrollment or Successful Auth for three years. The Speaker APIs now return a "LastAccessedAt" time for Speakers, and the EvaluateSession API returns "SPEAKER_EXPIRED" Auth Decision for EXPIRED Speakers.
* api-change:``cloudformation``: Add a new parameter statusReason to DescribeStackSetOperation output for additional details


1.24.7
======

* api-change:``ec2``: Stop Protection feature enables customers to protect their instances from accidental stop actions.
* api-change:``cognito-idp``: Amazon Cognito now supports requiring attribute verification (ex. email and phone number) before update.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for rules that constrain Automatic-ABR rendition selection when generating ABR package ladders.
* api-change:``networkmanager``: This release adds Multi Account API support for a TGW Global Network, to enable and disable AWSServiceAccess with AwsOrganizations for Network Manager service and dependency CloudFormation StackSets service.
* api-change:``ivschat``: Doc-only update. For MessageReviewHandler structure, added timeout period in the description of the fallbackResult field


1.24.6
======

* api-change:``forecast``: New APIs for Monitor that help you understand how your predictors perform over time.
* api-change:``elasticache``: Added support for encryption in transit for Memcached clusters. Customers can now launch Memcached cluster with encryption in transit enabled when using Memcached version 1.6.12 or later.
* api-change:``personalize``: Adding modelMetrics as part of DescribeRecommender API response for Personalize.


1.24.5
======

* api-change:``comprehend``: Comprehend releases 14 new entity types for DetectPiiEntities and ContainsPiiEntities APIs.
* api-change:``logs``: Doc-only update to publish the new valid values for log retention
* enhancement:dependency: Bump upper bound of docutils to <0.17


1.24.4
======

* api-change:``gamesparks``: This release adds an optional DeploymentResult field in the responses of GetStageDeploymentIntegrationTests and ListStageDeploymentIntegrationTests APIs.
* api-change:``lookoutmetrics``: In this release we added SnsFormat to SNSConfiguration to support human readable alert.


1.24.3
======

* api-change:``quicksight``: API UpdatePublicSharingSettings enables IAM admins to enable/disable account level setting for public access of dashboards. When enabled, owners/co-owners for dashboards can enable public access on their dashboards. These dashboards can only be accessed through share link or embedding.
* api-change:``greengrassv2``: This release adds the new DeleteDeployment API operation that you can use to delete deployment resources. This release also adds support for discontinued AWS-provided components, so AWS can communicate when a component has any issues that you should consider before you deploy it.
* api-change:``transfer``: AWS Transfer Family now supports SetStat server configuration option, which provides the ability to ignore SetStat command issued by file transfer clients, enabling customers to upload files without any errors.
* api-change:``batch``: Documentation updates for AWS Batch.
* api-change:``appmesh``: This release updates the existing Create and Update APIs for meshes and virtual nodes by adding a new IP preference field. This new IP preference field can be used to control the IP versions being used with the mesh and allows for IPv6 support within App Mesh.
* api-change:``iotevents-data``: Introducing new API for deleting detectors: BatchDeleteDetector.


1.24.2
======

* api-change:``glue``: This release adds a new optional parameter called codeGenNodeConfiguration to CRUD job APIs that allows users to manage visual jobs via APIs. The updated CreateJob and UpdateJob will create jobs that can be viewed in Glue Studio as a visual graph. GetJob can be used to get codeGenNodeConfiguration.
* api-change:``kms``: Add HMAC best practice tip, annual rotation of AWS managed keys.


1.24.1
======

* api-change:``cloudfront``: Introduced a new error (TooLongCSPInResponseHeadersPolicy) that is returned when the value of the Content-Security-Policy header in a response headers policy exceeds the maximum allowed length.
* api-change:``rekognition``: Documentation updates for Amazon Rekognition.
* api-change:``resiliencehub``: In this release, we are introducing support for Amazon Elastic Container Service, Amazon Route 53, AWS Elastic Disaster Recovery, AWS Backup in addition to the existing supported Services.  This release also supports Terraform file input from S3 and scheduling daily assessments
* api-change:``servicecatalog``: Updated the descriptions for the ListAcceptedPortfolioShares API description and the PortfolioShareType parameters.
* api-change:``discovery``: Add Migration Evaluator Collector details to the GetDiscoverySummary API response
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``workspaces-web``: Amazon WorkSpaces Web now supports Administrator timeout control


1.24.0
======

* feature:``eks get-token``: All eks get-token commands default to api version v1beta1.
* api-change:``grafana``: This release adds APIs for creating and deleting API keys in an Amazon Managed Grafana workspace.
* feature:Loaders: Support for loading gzip compressed model files.
* bugfix:``eks get-token``: Correctly fallback to client.authentication.k8s.io/v1beta1 API if KUBERNETES_EXEC_INFO is undefined


1.23.13
=======

* api-change:``kendra``: Amazon Kendra now provides a data source connector for Jira. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-jira.html
* api-change:``transfer``: AWS Transfer Family now accepts ECDSA keys for server host keys
* api-change:``ssm-incidents``: Adding support for dynamic SSM Runbook parameter values. Updating validation pattern for engagements. Adding ConflictException to UpdateReplicationSet API contract.
* api-change:``workspaces``: Increased the character limit of the login message from 600 to 850 characters.
* api-change:``ec2``: This release introduces a target type Gateway Load Balancer Endpoint for mirrored traffic. Customers can now specify GatewayLoadBalancerEndpoint option during the creation of a traffic mirror target.
* api-change:``iot``: Documentation update for China region ListMetricValues for IoT
* api-change:``lightsail``: This release adds support to include inactive database bundles in the response of the GetRelationalDatabaseBundles request.
* api-change:``outposts``: Documentation updates for AWS Outposts.
* api-change:``ivschat``: Documentation-only updates for IVS Chat API Reference.
* api-change:``finspace-data``: We've now deprecated CreateSnapshot permission for creating a data view, instead use CreateDataView permission.
* api-change:``lambda``: Lambda releases NodeJs 16 managed runtime to be available in all commercial regions.


1.23.12
=======

* api-change:``ec2``: This release updates AWS PrivateLink APIs to support IPv6 for PrivateLink Services and Endpoints of type 'Interface'.
* api-change:``secretsmanager``: Doc only update for Secrets Manager that fixes several customer-reported issues.


1.23.11
=======

* api-change:``eks``: Adds BOTTLEROCKET_ARM_64_NVIDIA and BOTTLEROCKET_x86_64_NVIDIA AMI types to EKS managed nodegroups
* api-change:``emr``: Update emr command to latest version
* api-change:``ec2``: Added support for using NitroTPM and UEFI Secure Boot on EC2 instances.
* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer
* api-change:``migration-hub-refactor-spaces``: AWS Migration Hub Refactor Spaces documentation only update to fix a formatting issue.


1.23.10
=======

* api-change:``ssm-contacts``: Fixed an error in the DescribeEngagement example for AWS Incident Manager.
* api-change:``cloudcontrol``: SDK release for Cloud Control API to include paginators for Python SDK.
* api-change:``evidently``: Add detail message inside GetExperimentResults API response to indicate experiment result availability


1.23.9
======

* api-change:``rds``: [``botocore``] Various documentation improvements.
* api-change:``redshift``: [``botocore``] Introduces new field 'LoadSampleData' in CreateCluster operation. Customers can now specify 'LoadSampleData' option during creation of a cluster, which results in loading of sample data in the cluster that is created.
* api-change:``ec2``: [``botocore``] Add new state values for IPAMs, IPAM Scopes, and IPAM Pools.
* api-change:``mediapackage``: [``botocore``] This release adds Dvb Dash 2014 as an available profile option for Dash Origin Endpoints.
* api-change:``securityhub``: [``botocore``] Documentation updates for Security Hub API reference
* enhancement:eks get-token: Add support for respecting API version found in KUBERNETES_EXEC_INFO environment variable
* api-change:``location``: [``botocore``] Amazon Location Service now includes a MaxResults parameter for ListGeofences requests.
* enhancement:eks update-kubeconfig: Update default API version to v1beta1


1.23.8
======

* api-change:``ec2``: [``botocore``] Amazon EC2 I4i instances are powered by 3rd generation Intel Xeon Scalable processors and feature up to 30 TB of local AWS Nitro SSD storage
* api-change:``kendra``: [``botocore``] AWS Kendra now supports hierarchical facets for a query. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/filtering.html
* api-change:``iot``: [``botocore``] AWS IoT Jobs now allows you to create up to 100,000 active continuous and snapshot jobs by using concurrency control.
* api-change:``datasync``: [``botocore``] AWS DataSync now supports a new ObjectTags Task API option that can be used to control whether Object Tags are transferred.


1.23.7
======

* api-change:``ssm``: [``botocore``] This release adds the TargetMaps parameter in SSM State Manager API.
* api-change:``backup``: [``botocore``] Adds support to 2 new filters about job complete time for 3 list jobs APIs in AWS Backup
* api-change:``lightsail``: [``botocore``] Documentation updates for Lightsail
* api-change:``iotsecuretunneling``: [``botocore``] This release introduces a new API RotateTunnelAccessToken that allow revoking the existing tokens and generate new tokens


1.23.6
======

* api-change:``ec2``: [``botocore``] Adds support for allocating Dedicated Hosts on AWS  Outposts. The AllocateHosts API now accepts an OutpostArn request  parameter, and the DescribeHosts API now includes an OutpostArn response parameter.
* api-change:``s3``: [``botocore``] Documentation only update for doc bug fixes for the S3 API docs.
* api-change:``kinesisvideo``: [``botocore``] Add support for multiple image feature related APIs for configuring image generation and notification of a video stream. Add "GET_IMAGES" to the list of supported API names for the GetDataEndpoint API.
* api-change:``sagemaker``: [``botocore``] SageMaker Autopilot adds new metrics for all candidate models generated by Autopilot experiments; RStudio on SageMaker now allows users to bring your own development environment in a custom image.
* api-change:``kinesis-video-archived-media``: [``botocore``] Add support for GetImages API  for retrieving images from a video stream


1.23.5
======

* api-change:``organizations``: [``botocore``] This release adds the INVALID_PAYMENT_INSTRUMENT as a fail reason and an error message.
* api-change:``synthetics``: [``botocore``] CloudWatch Synthetics has introduced a new feature to provide customers with an option to delete the underlying resources that Synthetics canary creates when the user chooses to delete the canary.
* api-change:``outposts``: [``botocore``] This release adds a new API called ListAssets to the Outposts SDK, which lists the hardware assets in an Outpost.


1.23.4
======

* api-change:``rds``: [``botocore``] Feature - Adds support for Internet Protocol Version 6 (IPv6) on RDS database instances.
* api-change:``codeguru-reviewer``: [``botocore``] Amazon CodeGuru Reviewer now supports suppressing recommendations from being generated on specific files and directories.
* api-change:``ssm``: [``botocore``] Update the StartChangeRequestExecution, adding TargetMaps to the Runbook parameter
* api-change:``mediaconvert``: [``botocore``] AWS Elemental MediaConvert SDK nows supports creation of Dolby Vision profile 8.1, the ability to generate black frames of video, and introduces audio-only DASH and CMAF support.
* api-change:``wafv2``: [``botocore``] You can now inspect all request headers and all cookies. You can now specify how to handle oversize body contents in your rules that inspect the body.


1.23.3
======

* api-change:``auditmanager``: [``botocore``] This release adds documentation updates for Audit Manager. We provided examples of how to use the Custom_ prefix for the keywordValue attribute. We also provided more details about the DeleteAssessmentReport operation.
* api-change:``network-firewall``: [``botocore``] AWS Network Firewall adds support for stateful threat signature AWS managed rule groups.
* api-change:``ec2``: [``botocore``] This release adds support to query the public key and creation date of EC2 Key Pairs. Additionally, the format (pem or ppk) of a key pair can be specified when creating a new key pair.
* api-change:``braket``: [``botocore``] This release enables Braket Hybrid Jobs with Embedded Simulators to have multiple instances.
* api-change:``guardduty``: [``botocore``] Documentation update for API description.
* api-change:``connect``: [``botocore``] This release introduces an API for changing the current agent status of a user in Connect.


1.23.2
======

* api-change:``rekognition``: [``botocore``] This release adds support to configure stream-processor resources for label detections on streaming-videos. UpateStreamProcessor API is also launched with this release, which could be used to update an existing stream-processor.
* api-change:``cloudtrail``: [``botocore``] Increases the retention period maximum to 2557 days. Deprecates unused fields of the ListEventDataStores API response. Updates documentation.
* api-change:``lookoutequipment``: [``botocore``] This release adds the following new features: 1) Introduces an option for automatic schema creation 2) Now allows for Ingestion of data containing most common errors and allows automatic data cleaning 3) Introduces new API ListSensorStatistics that gives further information about the ingested data
* api-change:``iotwireless``: [``botocore``] Add list support for event configurations, allow to get and update event configurations by resource type, support LoRaWAN events; Make NetworkAnalyzerConfiguration as a resource, add List, Create, Delete API support; Add FCntStart attribute support for ABP WirelessDevice.
* api-change:``amplify``: [``botocore``] Documentation only update to support the Amplify GitHub App feature launch
* api-change:``chime-sdk-media-pipelines``: [``botocore``] For Amazon Chime SDK meetings, the Amazon Chime Media Pipelines SDK allows builders to capture audio, video, and content share streams. You can also capture meeting events, live transcripts, and data messages. The pipelines save the artifacts to an Amazon S3 bucket that you designate.
* api-change:``sagemaker``: [``botocore``] Amazon SageMaker Autopilot adds support for custom validation dataset and validation ratio through the CreateAutoMLJob and DescribeAutoMLJob APIs.


1.23.1
======

* api-change:``lightsail``: [``botocore``] This release adds support for Lightsail load balancer HTTP to HTTPS redirect and TLS policy configuration.
* api-change:``sagemaker``: [``botocore``] SageMaker Inference Recommender now accepts customer KMS key ID for encryption of endpoints and compilation outputs created during inference recommendation.
* api-change:``pricing``: [``botocore``] Documentation updates for Price List API
* api-change:``glue``: [``botocore``] This release adds documentation for the APIs to create, read, delete, list, and batch read of AWS Glue custom patterns, and for Lake Formation configuration settings in the AWS Glue crawler.
* api-change:``cloudfront``: [``botocore``] CloudFront now supports the Server-Timing header in HTTP responses sent from CloudFront. You can use this header to view metrics that help you gain insights about the behavior and performance of CloudFront. To use this header, enable it in a response headers policy.
* api-change:``ivschat``: [``botocore``] Adds new APIs for IVS Chat, a feature for building interactive chat experiences alongside an IVS broadcast.
* api-change:``network-firewall``: [``botocore``] AWS Network Firewall now enables customers to use a customer managed AWS KMS key for the encryption of their firewall resources.


1.23.0
======

* api-change:``gamelift``: [``botocore``] Documentation updates for Amazon GameLift.
* api-change:``mq``: [``botocore``] This release adds the CRITICAL_ACTION_REQUIRED broker state and the ActionRequired API property. CRITICAL_ACTION_REQUIRED informs you when your broker is degraded. ActionRequired provides you with a code which you can use to find instructions in the Developer Guide on how to resolve the issue.
* feature:IMDS: [``botocore``] Added resiliency mechanisms to IMDS Credential Fetcher
* api-change:``securityhub``: [``botocore``] Security Hub now lets you opt-out of auto-enabling the defaults standards (CIS and FSBP) in accounts that are auto-enabled with Security Hub via Security Hub's integration with AWS Organizations.
* api-change:``connect``: [``botocore``] This release adds SearchUsers API which can be used to search for users with a Connect Instance
* api-change:``rds-data``: [``botocore``] Support to receive SQL query results in the form of a simplified JSON string. This enables developers using the new JSON string format to more easily convert it to an object using popular JSON string parsing libraries.


1.22.101
========

* api-change:``chime-sdk-meetings``: [``botocore``] Include additional exceptions types.
* api-change:``ec2``: [``botocore``] Adds support for waiters that automatically poll for a deleted NAT Gateway until it reaches the deleted state.


1.22.100
========

* api-change:``wisdom``: [``botocore``] This release updates the GetRecommendations API to include a trigger event list for classifying and grouping recommendations.
* api-change:``elasticache``: [``botocore``] Doc only update for ElastiCache
* api-change:``iottwinmaker``: [``botocore``] General availability (GA) for AWS IoT TwinMaker. For more information, see https://docs.aws.amazon.com/iot-twinmaker/latest/apireference/Welcome.html
* api-change:``secretsmanager``: [``botocore``] Documentation updates for Secrets Manager
* api-change:``mediatailor``: [``botocore``] This release introduces tiered channels and adds support for live sources. Customers using a STANDARD channel can now create programs using live sources.
* api-change:``storagegateway``: [``botocore``] This release adds support for minimum of 5 character length virtual tape barcodes.
* api-change:``lookoutmetrics``: [``botocore``] Added DetectMetricSetConfig API for detecting configuration required for creating metric set from provided S3 data source.
* api-change:``iotsitewise``: [``botocore``] This release adds 3 new batch data query APIs : BatchGetAssetPropertyValue, BatchGetAssetPropertyValueHistory and BatchGetAssetPropertyAggregates
* api-change:``glue``: [``botocore``] This release adds APIs to create, read, delete, list, and batch read of Glue custom entity types


1.22.99
=======

* api-change:``macie2``: [``botocore``] Sensitive data findings in Amazon Macie now indicate how Macie found the sensitive data that produced a finding (originType).
* api-change:``rds``: [``botocore``] Added a new cluster-level attribute to set the capacity range for Aurora Serverless v2 instances.
* api-change:``mgn``: [``botocore``] Removed required annotation from input fields in Describe operations requests. Added quotaValue to ServiceQuotaExceededException
* api-change:``connect``: [``botocore``] This release adds APIs to search, claim, release, list, update, and describe phone numbers. You can also use them to associate and disassociate contact flows to phone numbers.


1.22.98
=======

* api-change:``textract``: This release adds support for specifying and extracting information from documents using the Queries feature within Analyze Document API
* api-change:``ssm``: Added offset support for specifying the number of days to wait after the date and time specified by a CRON expression when creating SSM association.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Quip. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-quip.html
* api-change:``personalize``: Adding StartRecommender and StopRecommender APIs for Personalize.
* api-change:``polly``: Amazon Polly adds new Austrian German voice - Hannah. Hannah is available as Neural voice only.
* api-change:``redshift``: Introduces new fields for LogDestinationType and LogExports on EnableLogging requests and Enable/Disable/DescribeLogging responses. Customers can now select CloudWatch Logs as a destination for their Audit Logs.
* api-change:``transfer``: This release contains corrected HomeDirectoryMappings examples for several API functions: CreateAccess, UpdateAccess, CreateUser, and UpdateUser,.
* api-change:``autoscaling``: EC2 Auto Scaling now adds default instance warm-up times for all scaling activities, health check replacements, and other replacement events in the Auto Scaling instance lifecycle.
* api-change:``kms``: Adds support for KMS keys and APIs that generate and verify HMAC codes
* api-change:``worklink``: Amazon WorkLink is no longer supported. This will be removed in a future version of the SDK.


1.22.97
=======

* api-change:``rds``: Removes Amazon RDS on VMware with the deletion of APIs related to Custom Availability Zones and Media installation
* api-change:``athena``: This release adds subfields, ErrorMessage, Retryable, to the AthenaError response object in the GetQueryExecution API when a query fails.
* api-change:``lightsail``: This release adds support to describe the synchronization status of the account-level block public access feature for your Amazon Lightsail buckets.


1.22.96
=======

* api-change:``appflow``: Enables users to pass custom token URL parameters for Oauth2 authentication during create connector profile
* api-change:``appstream``: Includes updates for create and update fleet APIs to manage the session scripts locations for Elastic fleets.
* api-change:``glue``: Auto Scaling for Glue version 3.0 and later jobs to dynamically scale compute resources. This SDK change provides customers with the auto-scaled DPU usage
* bugfix:Configuration: Fixes `#2996 <https://github.com/aws/aws-cli/issues/2996>`__. Fixed a bug where config file updates would sometimes append new sections to the previous section without adding a newline.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``batch``: Enables configuration updates for compute environments with BEST_FIT_PROGRESSIVE and SPOT_CAPACITY_OPTIMIZED allocation strategies.
* api-change:``ec2``: Documentation updates for Amazon EC2.


1.22.95
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``fsx``: This release adds support for deploying FSx for ONTAP file systems in a single Availability Zone.


1.22.94
=======

* api-change:``iottwinmaker``: This release adds the following new features: 1) ListEntities API now supports search using ExternalId. 2) BatchPutPropertyValue and GetPropertyValueHistory API now allows users to represent time in sub-second level precisions.
* api-change:``efs``: Update efs command to latest version
* api-change:``devops-guru``: This release adds new APIs DeleteInsight to deletes the insight along with the associated anomalies, events and recommendations.
* api-change:``ec2``: X2idn and X2iedn instances are powered by 3rd generation Intel Xeon Scalable processors with an all-core turbo frequency up to 3.5 GHzAmazon EC2. C6a instances are powered by 3rd generation AMD EPYC processors.


1.22.93
=======

* api-change:``apprunner``: This release adds tracing for App Runner services with X-Ray using AWS Distro for OpenTelemetry. New APIs: CreateObservabilityConfiguration, DescribeObservabilityConfiguration, ListObservabilityConfigurations, and DeleteObservabilityConfiguration. Updated APIs: CreateService and UpdateService.
* api-change:``amplifyuibuilder``: In this release, we have added the ability to bind events to component level actions.
* api-change:``workspaces``: Added API support that allows customers to create GPU-enabled WorkSpaces using EC2 G4dn instances.


1.22.92
=======

* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for the pass-through of WebVTT styling to WebVTT outputs, pass-through of KLV metadata to supported formats, and improved filter support for processing 444/RGB content.
* api-change:``wafv2``: Add a new CurrentDefaultVersion field to ListAvailableManagedRuleGroupVersions API response; add a new VersioningSupported boolean to each ManagedRuleGroup returned from ListAvailableManagedRuleGroups API response.
* api-change:``mediapackage-vod``: This release adds ScteMarkersSource as an available field for Dash Packaging Configurations. When set to MANIFEST, MediaPackage will source the SCTE-35 markers from the manifest. When set to SEGMENTS, MediaPackage will source the SCTE-35 markers from the segments.


1.22.91
=======

* api-change:``apigateway``: ApiGateway CLI command get-usage now includes usagePlanId, startDate, and endDate fields in the output to match documentation.
* api-change:``pi``: Adds support for DocumentDB to the Performance Insights API.
* api-change:``sagemaker``: Amazon Sagemaker Notebook Instances now supports G5 instance types
* api-change:``docdb``: Added support to enable/disable performance insights when creating or modifying db instances
* api-change:``events``: Update events command to latest version
* api-change:``personalize``: This release provides tagging support in AWS Personalize.


1.22.90
=======

* api-change:``config``: Add resourceType enums for AWS::EMR::SecurityConfiguration and AWS::SageMaker::CodeRepository
* api-change:``lambda``: This release adds new APIs for creating and managing Lambda Function URLs and adds a new FunctionUrlAuthType parameter to the AddPermission API. Customers can use Function URLs to create built-in HTTPS endpoints on their functions.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Box. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-box.html
* api-change:``panorama``: Added Brand field to device listings.


1.22.89
=======

* api-change:``s3control``: Documentation-only update for doc bug fixes for the S3 Control API docs.
* api-change:``securityhub``: Added additional ASFF details for RdsSecurityGroup AutoScalingGroup, ElbLoadBalancer, CodeBuildProject and RedshiftCluster.
* api-change:``datasync``: AWS DataSync now supports Amazon FSx for OpenZFS locations.
* api-change:``fsx``: Provide customers more visibility into file system status by adding new "Misconfigured Unavailable" status for Amazon FSx for Windows File Server.


1.22.88
=======

* api-change:``sms``: Revised product update notice for SMS console deprecation.
* api-change:``servicecatalog``: This release adds ProvisioningArtifictOutputKeys to DescribeProvisioningParameters to reference the outputs of a Provisioned Product and deprecates ProvisioningArtifactOutputs.
* api-change:``iot``: AWS IoT - AWS IoT Device Defender adds support to list metric datapoints collected for IoT devices through the ListMetricValues API
* api-change:``proton``: SDK release to support tagging for AWS Proton Repository resource


1.22.87
=======

* api-change:``connect``: This release updates these APIs: UpdateInstanceAttribute, DescribeInstanceAttribute and ListInstanceAttributes. You can use it to programmatically enable/disable multi-party conferencing using attribute type MULTI_PARTY_CONFERENCING on the specified Amazon Connect instance.


1.22.86
=======

* api-change:``databrew``: This AWS Glue Databrew release adds feature to support ORC as an input format.
* api-change:``route53-recovery-cluster``: This release adds a new API "ListRoutingControls" to list routing control states using the highly reliable Route 53 ARC data plane endpoints.
* api-change:``pinpoint-sms-voice-v2``: Amazon Pinpoint now offers a version 2.0 suite of SMS and voice APIs, providing increased control over sending and configuration. This release is a new SDK for sending SMS and voice messages called PinpointSMSVoiceV2.
* api-change:``cloudcontrol``: SDK release for Cloud Control API in Amazon Web Services China (Beijing) Region, operated by Sinnet, and Amazon Web Services China (Ningxia) Region, operated by NWCD
* api-change:``workspaces``: Added APIs that allow you to customize the logo, login message, and help links in the WorkSpaces client login page. To learn more, visit https://docs.aws.amazon.com/workspaces/latest/adminguide/customize-branding.html
* api-change:``grafana``: This release adds tagging support to the Managed Grafana service. New APIs: TagResource, UntagResource and ListTagsForResource. Updates: add optional field tags to support tagging while calling CreateWorkspace.
* api-change:``auditmanager``: This release adds documentation updates for Audit Manager. The updates provide data deletion guidance when a customer deregisters Audit Manager or deregisters a delegated administrator.


1.22.85
=======

* api-change:``iot-data``: Update the default AWS IoT Core Data Plane endpoint from VeriSign signed to ATS signed. If you have firewalls with strict egress rules, configure the rules to grant you access to data-ats.iot.[region].amazonaws.com or data-ats.iot.[region].amazonaws.com.cn.
* api-change:``fms``: AWS Firewall Manager now supports the configuration of third-party policies that can use either the centralized or distributed deployment models.
* api-change:``ec2``: This release simplifies the auto-recovery configuration process enabling customers to set the recovery behavior to disabled or default
* api-change:``fsx``: This release adds support for modifying throughput capacity for FSx for ONTAP file systems.
* api-change:``iot``: Doc only update for IoT that fixes customer-reported issues.


1.22.84
=======

* api-change:``organizations``: This release provides the new CloseAccount API that enables principals in the management account to close any member account within an organization.


1.22.83
=======

* api-change:``medialive``: This release adds support for selecting a maintenance window.
* api-change:``acm-pca``: Updating service name entities


1.22.82
=======

* api-change:``ec2``: This is release adds support for Amazon VPC Reachability Analyzer to analyze path through a Transit Gateway.
* api-change:``ssm``: This Patch Manager release supports creating, updating, and deleting Patch Baselines for Rocky Linux OS.
* api-change:``batch``: Bug Fix: Fixed a bug where shapes were marked as unboxed and were not serialized and sent over the wire, causing an API error from the service.


1.22.81
=======

* api-change:``config``: Added new APIs GetCustomRulePolicy and GetOrganizationCustomRulePolicy, and updated existing APIs PutConfigRule, DescribeConfigRule, DescribeConfigRuleEvaluationStatus, PutOrganizationConfigRule, DescribeConfigRule to support a new feature for building AWS Config rules with AWS CloudFormation Guard
* api-change:``lambda``: Adds support for increased ephemeral storage (/tmp) up to 10GB for Lambda functions. Customers can now provision up to 10 GB of ephemeral storage per function instance, a 20x increase over the previous limit of 512 MB.
* api-change:``transcribe``: This release adds an additional parameter for subtitling with Amazon Transcribe batch jobs: outputStartIndex.


1.22.80
=======

* api-change:``ssm``: Update AddTagsToResource, ListTagsForResource, and RemoveTagsFromResource APIs to reflect the support for tagging Automation resources. Includes other minor documentation updates.
* api-change:``transfer``: Documentation updates for AWS Transfer Family to describe how to remove an associated workflow from a server.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``ebs``: Increased the maximum supported value for the Timeout parameter of the StartSnapshot API from 60 minutes to 4320 minutes.  Changed the HTTP error code for ConflictException from 503 to 409.
* api-change:``auditmanager``: This release updates 1 API parameter, the SnsArn attribute. The character length and regex pattern for the SnsArn attribute have been updated, which enables you to deselect an SNS topic when using the UpdateSettings operation.
* api-change:``redshift``: This release adds a new [--encrypted | --no-encrypted] field in restore-from-cluster-snapshot API. Customers can now restore an unencrypted snapshot to a cluster encrypted with AWS Managed Key or their own KMS key.
* api-change:``gamesparks``: Released the preview of Amazon GameSparks, a fully managed AWS service that provides a multi-service backend for game developers.


1.22.79
=======

* api-change:``location``: Amazon Location Service now includes a MaxResults parameter for GetDevicePositionHistory requests.
* api-change:``ecs``: Documentation only update to address tickets
* api-change:``polly``: Amazon Polly adds new Catalan voice - Arlet. Arlet is available as Neural voice only.
* api-change:``ce``: Added three new APIs to support tagging and resource-level authorization on Cost Explorer resources: TagResource, UntagResource, ListTagsForResource.  Added optional parameters to CreateCostCategoryDefinition, CreateAnomalySubscription and CreateAnomalyMonitor APIs to support Tag On Create.
* api-change:``lakeformation``: The release fixes the incorrect permissions called out in the documentation - DESCRIBE_TAG, ASSOCIATE_TAG, DELETE_TAG, ALTER_TAG. This trebuchet release fixes the corresponding SDK and documentation.


1.22.78
=======

* api-change:``mediaconnect``: This release adds support for selecting a maintenance window.
* api-change:``chime-sdk-meetings``: Add support for media replication to link multiple WebRTC media sessions together to reach larger and global audiences. Participants connected to a replica session can be granted access to join the primary session and can switch sessions with their existing WebRTC connection
* api-change:``ram``: Document improvements to the RAM API operations and parameter descriptions.
* api-change:``ecr``: This release includes a fix in the DescribeImageScanFindings paginated output.
* api-change:``quicksight``: AWS QuickSight Service Features - Expand public API support for group management.


1.22.77
=======

* api-change:``glue``: Added 9 new APIs for AWS Glue Interactive Sessions: ListSessions, StopSession, CreateSession, GetSession, DeleteSession, RunStatement, GetStatement, ListStatements, CancelStatement


1.22.76
=======

* api-change:``billingconductor``: This is the initial SDK release for AWS Billing Conductor. The AWS Billing Conductor is a customizable billing service, allowing you to customize your billing data to match your desired business structure.
* api-change:``acm-pca``: AWS Certificate Manager (ACM) Private Certificate Authority (CA) now supports customizable certificate subject names and extensions.
* api-change:``amplifybackend``: Adding the ability to customize Cognito verification messages for email and SMS in CreateBackendAuth and UpdateBackendAuth. Adding deprecation documentation for ForgotPassword in CreateBackendAuth and UpdateBackendAuth
* api-change:``ssm-incidents``: Removed incorrect validation pattern for IncidentRecordSource.invokedBy
* api-change:``s3outposts``: S3 on Outposts is releasing a new API, ListSharedEndpoints, that lists all endpoints associated with S3 on Outpost, that has been shared by Resource Access Manager (RAM).


1.22.75
=======

* api-change:``ec2``: Adds the Cascade parameter to the DeleteIpam API. Customers can use this parameter to automatically delete their IPAM, including non-default scopes, pools, cidrs, and allocations. There mustn't be any pools provisioned in the default public scope to use this parameter.
* api-change:``rds``: Various documentation improvements
* api-change:``dataexchange``: This feature enables data providers to use the RevokeRevision operation to revoke subscriber access to a given revision. Subscribers are unable to interact with assets within a revoked revision.
* api-change:``robomaker``: This release deprecates ROS, Ubuntu and Gazbeo from RoboMaker Simulation Service Software Suites in favor of user-supplied containers and Relaxed Software Suites.
* api-change:``location``: New HERE style "VectorHereExplore" and "VectorHereExploreTruck".
* api-change:``cognito-idp``: Updated EmailConfigurationType and SmsConfigurationType to reflect that you can now choose Amazon SES and Amazon SNS resources in the same Region.
* api-change:``keyspaces``: Fixing formatting issues in CLI and SDK documentation
* api-change:``ecs``: Documentation only update to address tickets


1.22.74
=======

* api-change:``kendra``: Amazon Kendra now provides a data source connector for Slack. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-slack.html
* api-change:``config``: Add resourceType enums for AWS::ECR::PublicRepository and AWS::EC2::LaunchTemplate
* api-change:``timestream-query``: Amazon Timestream Scheduled Queries now support Timestamp datatype in a multi-measure record.
* api-change:``elasticache``: Doc only update for ElastiCache


1.22.73
=======

* api-change:``secretsmanager``: Documentation updates for Secrets Manager.
* api-change:``outposts``: This release adds address filters for listSites
* api-change:``connect``: This release adds support for enabling Rich Messaging when starting a new chat session via the StartChatContact API. Rich Messaging enables the following formatting options: bold, italics, hyperlinks, bulleted lists, and numbered lists.
* api-change:``chime``: Chime VoiceConnector Logging APIs will now support MediaMetricLogs. Also CreateMeetingDialOut now returns AccessDeniedException.
* api-change:``lambda``: Adds PrincipalOrgID support to AddPermission API. Customers can use it to manage permissions to lambda functions at AWS Organizations level.


1.22.72
=======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``transcribe``: Documentation fix for API `StartMedicalTranscriptionJobRequest`, now showing min sample rate as 16khz
* api-change:``transfer``: Adding more descriptive error types for managed workflows


1.22.71
=======

* api-change:``comprehend``: Amazon Comprehend now supports extracting the sentiment associated with entities such as brands, products and services from text documents.


1.22.70
=======

* api-change:``eks``: Introducing a new enum for NodeGroup error code: Ec2SubnetMissingIpv6Assignment
* api-change:``keyspaces``: Adding link to CloudTrail section in Amazon Keyspaces Developer Guide
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for reading timecode from AVCHD sources and now provides the ability to segment WebVTT at the same interval as the video and audio in HLS packages.


1.22.69
=======

* api-change:``ecs``: Amazon ECS UpdateService API now supports additional parameters: loadBalancers, propagateTags, enableECSManagedTags, and serviceRegistries
* api-change:``chime-sdk-meetings``: Adds support for Transcribe language identification feature to the StartMeetingTranscription API.
* api-change:``migration-hub-refactor-spaces``: AWS Migration Hub Refactor Spaces documentation update.


1.22.68
=======

* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``synthetics``: Allow custom handler function.
* api-change:``transfer``: Add waiters for server online and offline.
* api-change:``connect``: This release updates the *InstanceStorageConfig APIs so they support a new ResourceType: REAL_TIME_CONTACT_ANALYSIS_SEGMENTS. Use this resource type to enable streaming for real-time contact analysis and to associate the Kinesis stream where real-time contact analysis segments will be published.
* api-change:``macie``: Amazon Macie Classic (macie) has been discontinued and is no longer available. A new Amazon Macie (macie2) is now available with significant design improvements and additional features.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``devops-guru``: Amazon DevOps Guru now integrates with Amazon CodeGuru Profiler. You can view CodeGuru Profiler recommendations for your AWS Lambda function in DevOps Guru. This feature is enabled by default for new customers as of 3/4/2022. Existing customers can enable this feature with UpdateEventSourcesConfig.


1.22.67
=======

* api-change:``timestream-query``: Documentation only update for SDK and CLI
* api-change:``greengrassv2``: Doc only update that clarifies Create Deployment section.
* api-change:``kendra``: Amazon Kendra now suggests spell corrections for a query. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/query-spell-check.html
* api-change:``fsx``: This release adds support for data repository associations to use root ("/") as the file system path
* api-change:``appflow``: Launching Amazon AppFlow Marketo as a destination connector SDK.


1.22.66
=======

* api-change:``athena``: This release adds support for S3 Object Ownership by allowing the S3 bucket owner full control canned ACL to be set when Athena writes query results to S3 buckets.
* api-change:``ecr``: This release adds support for tracking images lastRecordedPullTime.
* api-change:``keyspaces``: This release adds support for data definition language (DDL) operations
* api-change:``gamelift``: Minor updates to address errors.
* api-change:``cloudtrail``: Add bytesScanned field into responses of DescribeQuery and GetQueryResults.


1.22.65
=======

* api-change:``mgn``: Add support for GP3 and IO2 volume types. Add bootMode to LaunchConfiguration object (and as a parameter to UpdateLaunchConfigurationRequest).
* api-change:``rds``: Documentation updates for Multi-AZ DB clusters.
* api-change:``mediapackage``: This release adds Hybridcast as an available profile option for Dash Origin Endpoints.
* api-change:``kafkaconnect``: Adds operation for custom plugin deletion (DeleteCustomPlugin) and adds new StateDescription field to DescribeCustomPlugin and DescribeConnector responses to return errors from asynchronous resource creation.


1.22.64
=======

* api-change:``ec2``: This release adds support for new AMI property 'lastLaunchedTime'
* api-change:``fsx``: This release adds support for the following FSx for OpenZFS features: snapshot lifecycle transition messages, force flag for deleting file systems with child resources, LZ4 data compression, custom record sizes, and unsetting volume quotas and reservations.
* api-change:``route53-recovery-cluster``: This release adds a new API option to enable overriding safety rules to allow routing control state updates.
* api-change:``fis``: This release adds logging support for AWS Fault Injection Simulator experiments. Experiment templates can now be configured to send experiment activity logs to Amazon CloudWatch Logs or to an S3 bucket.
* api-change:``servicecatalog-appregistry``: AppRegistry is deprecating Application and Attribute-Group Name update feature. In this release, we are marking the name attributes for Update APIs as deprecated to give a heads up to our customers.
* api-change:``athena``: This release adds support for updating an existing named query.
* api-change:``finspace-data``: Add new APIs for managing Users and Permission Groups.
* api-change:``amplifyuibuilder``: We are adding the ability to configure workflows and actions for components.
* api-change:``amplify``: Add repositoryCloneMethod field for hosting an Amplify app. This field shows what authorization method is used to clone the repo: SSH, TOKEN, or SIGV4.


1.22.63
=======

* api-change:``panorama``: Added NTP server configuration parameter to ProvisionDevice operation. Added alternate software fields to DescribeDevice response
* api-change:``elasticache``: Doc only update for ElastiCache


1.22.62
=======

* api-change:``lightsail``: This release adds support to delete and create Lightsail default key pairs that you can use with Lightsail instances.
* api-change:``s3``: This release adds support for new integrity checking capabilities in Amazon S3. You can choose from four supported checksum algorithms for data integrity checking on your upload and download requests. In addition, AWS SDK can automatically calculate a checksum as it streams data into S3
* api-change:``fms``: AWS Firewall Manager now supports the configuration of AWS Network Firewall policies with either centralized or distributed deployment models. This release also adds support for custom endpoint configuration, where you can choose which Availability Zones to create firewall endpoints in.
* api-change:``s3control``: Amazon S3 Batch Operations adds support for new integrity checking capabilities in Amazon S3.
* api-change:``route53``: SDK doc update for Route 53 to update some parameters with new information.
* api-change:``autoscaling``: You can now hibernate instances in a warm pool to stop instances without deleting their RAM contents. You can now also return instances to the warm pool on scale in, instead of always terminating capacity that you will need later.
* api-change:``transfer``: Support automatic pagination when listing AWS Transfer Family resources.
* api-change:``databrew``: This AWS Glue Databrew release adds feature to merge job outputs into a max number of files for S3 File output type.


1.22.61
=======

* api-change:``textract``: Added support for merged cells and column header for table response.
* api-change:``lambda``: Lambda releases .NET 6 managed runtime to be available in all commercial regions.
* api-change:``transfer``: The file input selection feature provides the ability to use either the originally uploaded file or the output file from the previous workflow step, enabling customers to make multiple copies of the original file while keeping the source file intact for file archival.


1.22.60
=======

* api-change:``apprunner``: AWS App Runner adds a Java platform (Corretto 8, Corretto 11 runtimes) and a Node.js 14 runtime.
* api-change:``translate``: This release enables customers to use translation settings for formality customization in their synchronous translation output.
* api-change:``wafv2``: Updated descriptions for logging configuration.


1.22.59
=======

* api-change:``customer-profiles``: This release introduces apis CreateIntegrationWorkflow, DeleteWorkflow, ListWorkflows, GetWorkflow and GetWorkflowSteps. These apis are used to manage and view integration workflows.
* api-change:``imagebuilder``: This release adds support to enable faster launching for Windows AMIs created by EC2 Image Builder.
* api-change:``dynamodb``: DynamoDB ExecuteStatement API now supports Limit as a request parameter to specify the maximum number of items to evaluate. If specified, the service will process up to the Limit and the results will include a LastEvaluatedKey value to continue the read in a subsequent operation.


1.22.58
=======

* api-change:``budgets``: This change introduces DescribeBudgetNotificationsForAccount API which returns budget notifications for the specified account
* api-change:``gamelift``: Increase string list limit from 10 to 100.
* api-change:``transfer``: Properties for Transfer Family used with SFTP, FTP, and FTPS protocols. Display Banners are bodies of text that can be displayed before and/or after a user authenticates onto a server using one of the previously mentioned protocols.


1.22.57
=======

* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``evidently``: Add support for filtering list of experiments and launches by status
* api-change:``redshift``: SDK release for Cross region datasharing and cost-control for cross region datasharing
* api-change:``backup``: AWS Backup add new S3_BACKUP_OBJECT_FAILED and S3_RESTORE_OBJECT_FAILED event types in BackupVaultNotifications events list.


1.22.56
=======

* api-change:``glue``: Support for optimistic locking in UpdateTable
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``budgets``: Adds support for auto-adjusting budgets, a new budget method alongside fixed and planned. Auto-adjusting budgets introduces new metadata to configure a budget limit baseline using a historical lookback average or current period forecast.
* api-change:``ssm``: Assorted ticket fixes and updates for AWS Systems Manager.
* api-change:``ce``: AWS Cost Anomaly Detection now supports SNS FIFO topic subscribers.


1.22.55
=======

* api-change:``rds``: Adds support for determining which Aurora PostgreSQL versions support Babelfish.
* api-change:``appflow``: Launching Amazon AppFlow SAP as a destination connector SDK.
* api-change:``athena``: This release adds a subfield, ErrorType, to the AthenaError response object in the GetQueryExecution API when a query fails.


1.22.54
=======

* api-change:``ssm``: Documentation updates for AWS Systems Manager.


1.22.53
=======

* api-change:``cloudformation``: This SDK release adds AWS CloudFormation Hooks HandlerErrorCodes
* api-change:``lookoutvision``: This release makes CompilerOptions in Lookout for Vision's StartModelPackagingJob's Configuration object optional.
* api-change:``pinpoint``: This SDK release adds a new paramater creation date for GetApp and GetApps Api call
* api-change:``sns``: Customer requested typo fix in API documentation.
* api-change:``wafv2``: Adds support for AWS WAF Fraud Control account takeover prevention (ATP), with configuration options for the new managed rule group AWSManagedRulesATPRuleSet and support for application integration SDKs for Android and iOS mobile apps.


1.22.52
=======

* api-change:``cloudformation``: This SDK release is for the feature launch of AWS CloudFormation Hooks.


1.22.51
=======

* api-change:``s3control``: This release adds support for S3 Batch Replication. Batch Replication lets you replicate existing objects, already replicated objects to new destinations, and objects that previously failed to replicate. Customers will receive object-level visibility of progress and a detailed completion report.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Amazon FSx. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-fsx.html
* api-change:``sagemaker``: Autopilot now generates an additional report with information on the performance of the best model, such as a Confusion matrix and  Area under the receiver operating characteristic (AUC-ROC). The path to the report can be found in CandidateArtifactLocations.
* api-change:``apprunner``: This release adds support for App Runner to route outbound network traffic of a service through an Amazon VPC. New API: CreateVpcConnector, DescribeVpcConnector, ListVpcConnectors, and DeleteVpcConnector. Updated API: CreateService, DescribeService, and UpdateService.


1.22.50
=======

* api-change:``auditmanager``: This release updates 3 API parameters. UpdateAssessmentFrameworkControlSet now requires the controls attribute, and CreateAssessmentFrameworkControl requires the id attribute. Additionally, UpdateAssessmentFramework now has a minimum length constraint for the controlSets attribute.
* api-change:``events``: Update events command to latest version
* api-change:``ssm-incidents``: Update RelatedItem enum to support SSM Automation
* api-change:``synthetics``: Adding names parameters to the Describe APIs.


1.22.49
=======

* api-change:``lakeformation``: Add support for calling Update Table Objects without a TransactionId.
* api-change:``athena``: You can now optionally specify the account ID that you expect to be the owner of your query results output location bucket in Athena. If the account ID of the query results bucket owner does not match the specified account ID, attempts to output to the bucket will fail with an S3 permissions error.
* api-change:``rds``: updates for RDS Custom for Oracle 12.1 support


1.22.48
=======

* api-change:``rbin``: Add EC2 Image recycle bin support.
* api-change:``meteringmarketplace``: Add CustomerAWSAccountId to ResolveCustomer API response and increase UsageAllocation limit to 2500.
* api-change:``ec2``: adds support for AMIs in Recycle Bin
* api-change:``robomaker``: The release deprecates the use various APIs of RoboMaker Deployment Service in favor of AWS IoT GreenGrass v2.0.


1.22.47
=======

* api-change:``emr``: Update emr command to latest version
* api-change:``elasticache``: Documentation update for AWS ElastiCache
* enhancement:datapipeline: Deprecated support for the datapipeline create-default-roles command
* api-change:``es``: Allows customers to get progress updates for blue/green deployments
* api-change:``fis``: Added GetTargetResourceType and ListTargetResourceTypesAPI actions. These actions return additional details about resource types and parameters that can be targeted by FIS actions. Added a parameters field for the targets that can be specified in experiment templates.
* api-change:``comprehend``: Amazon Comprehend now supports sharing and importing custom trained models from one AWS account to another within the same region.
* api-change:``dynamodb``: Documentation update for DynamoDB Java SDK.
* api-change:``iot``: This release adds support for configuring AWS IoT logging level per client ID, source IP, or principal ID.
* api-change:``ce``: Doc-only update for Cost Explorer API that adds INVOICING_ENTITY dimensions
* api-change:``appflow``: Launching Amazon AppFlow Custom Connector SDK.
* api-change:``glue``: Launch Protobuf support for AWS Glue Schema Registry
* api-change:``personalize``: Adding minRecommendationRequestsPerSecond attribute to recommender APIs.


1.22.46
=======

* api-change:``sagemaker``: This release added a new NNA accelerator compilation support for Sagemaker Neo.
* api-change:``athena``: This release adds a field, AthenaError, to the GetQueryExecution response object when a query fails.
* api-change:``secretsmanager``: Feature are ready to release on Jan 28th
* api-change:``cognito-idp``: Doc updates for Cognito user pools API Reference.
* api-change:``appconfig``: Documentation updates for AWS AppConfig
* api-change:``appconfigdata``: Documentation updates for AWS AppConfig Data.


1.22.45
=======

* api-change:``amplify``: Doc only update to the description of basicauthcredentials to describe the required encoding and format.
* api-change:``kafka``: Amazon MSK has updated the CreateCluster and UpdateBrokerStorage API that allows you to specify volume throughput during cluster creation and broker volume updates.
* api-change:``ec2``: X2ezn instances are powered by Intel Cascade Lake CPUs that deliver turbo all core frequency of up to 4.5 GHz and up to 100 Gbps of networking bandwidth
* api-change:``opensearch``: Allows customers to get progress updates for blue/green deployments
* api-change:``connect``: This release adds support for configuring a custom chat duration when starting a new chat session via the StartChatContact API. The default value for chat duration is 25 hours, minimum configurable value is 1 hour (60 minutes) and maximum configurable value is 7 days (10,080 minutes).


1.22.44
=======

* api-change:``ebs``: Documentation updates for Amazon EBS Direct APIs.
* api-change:``sagemaker``: API changes relating to Fail steps in model building pipeline and add PipelineExecutionFailureReason in PipelineExecutionSummary.
* api-change:``frauddetector``: Added new APIs for viewing past predictions and obtaining prediction metadata including prediction explanations: ListEventPredictions and GetEventPredictionMetadata
* api-change:``codeguru-reviewer``: Added failure state and adjusted timeout in waiter
* api-change:``securityhub``: Adding top level Sample boolean field


1.22.43
=======

* api-change:``connect``: This release adds support for custom vocabularies to be used with Contact Lens. Custom vocabularies improve transcription accuracy for one or more specific words.
* api-change:``guardduty``: Amazon GuardDuty expands threat detection coverage to protect Amazon Elastic Kubernetes Service (EKS) workloads.
* api-change:``fsx``: This release adds support for growing SSD storage capacity and growing/shrinking SSD IOPS for FSx for ONTAP file systems.
* api-change:``efs``: Update efs command to latest version


1.22.42
=======

* api-change:``route53-recovery-readiness``: Updated documentation for Route53 Recovery Readiness APIs.


1.22.41
=======

* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for 4K AV1 output resolutions & 10-bit AV1 color, the ability to ingest sidecar Dolby Vision XML metadata files, and the ability to flag WebVTT and IMSC tracks for accessibility in HLS.
* api-change:``transcribe``: Add support for granular PIIEntityTypes when using Batch ContentRedaction.


1.22.40
=======

* api-change:``ec2``: C6i, M6i and R6i instances are powered by a third-generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz
* api-change:``guardduty``: Amazon GuardDuty findings now include remoteAccountDetails under AwsApiCallAction section if instance credential is exfiltrated.
* api-change:``connect``: This release adds tagging support for UserHierarchyGroups resource.
* api-change:``mediatailor``: This release adds support for multiple Segment Delivery Configurations. Users can provide a list of names and URLs when creating or editing a source location. When retrieving content, users can send a header to choose which URL should be used to serve content.
* api-change:``fis``: Added action startTime and action endTime timestamp fields to the ExperimentAction object


1.22.39
=======

* api-change:``ec2-instance-connect``: Adds support for ED25519 keys. PushSSHPublicKey Availability Zone parameter is now optional. Adds EC2InstanceStateInvalidException for instances that are not running. This was previously a service exception, so this may require updating your code to handle this new exception.
* api-change:``macie2``: This release of the Amazon Macie API introduces stricter validation of requests to create custom data identifiers.


1.22.38
=======

* api-change:``ivs``: This release adds support for the new Thumbnail Configuration property for Recording Configurations. For more information see https://docs.aws.amazon.com/ivs/latest/userguide/record-to-s3.html
* api-change:``cloudtrail``: This release fixes a documentation bug in the description for the readOnly field selector in advanced event selectors. The description now clarifies that users omit the readOnly field selector to select both Read and Write management events.
* api-change:``ec2``: Add support for AWS Client VPN client login banner and session timeout.
* api-change:``location``: This release adds the CalculateRouteMatrix API which calculates routes for the provided departure and destination positions. The release also deprecates the use of pricing plan across all verticals.
* api-change:``storagegateway``: Documentation update for adding bandwidth throttling support for S3 File Gateways.


1.22.36
=======

* api-change:``config``: Update ResourceType enum with values for CodeDeploy, EC2 and Kinesis resources
* api-change:``ram``: This release adds the ListPermissionVersions API which lists the versions for a given permission.
* api-change:``honeycode``: Added read and write api support for multi-select picklist. And added errorcode field to DescribeTableDataImportJob API output, when import job fails.
* api-change:``application-insights``: Application Insights support for Active Directory and SharePoint
* api-change:``lookoutmetrics``: This release adds a new DeactivateAnomalyDetector API operation.


1.22.35
=======

* api-change:``elasticache``: AWS ElastiCache for Redis has added a new Engine Log LogType in LogDelivery feature. You can now publish the Engine Log from your Amazon ElastiCache for Redis clusters to Amazon CloudWatch Logs and Amazon Kinesis Data Firehose.
* api-change:``pinpoint``: Adds JourneyChannelSettings to WriteJourneyRequest
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``nimble``: Amazon Nimble Studio now supports validation for Launch Profiles. Launch Profiles now report static validation results after create/update to detect errors in network or active directory configuration.
* api-change:``glue``: This SDK release adds support to pass run properties when starting a workflow run
* api-change:``ssm``: AWS Systems Manager adds category support for DescribeDocument API


1.22.34
=======

* api-change:``ec2``: Hpc6a instances are powered by a third-generation AMD EPYC processors (Milan) delivering all-core turbo frequency of 3.4 GHz
* api-change:``pi``: This release adds three Performance Insights APIs. Use ListAvailableResourceMetrics to get available metrics, GetResourceMetadata to get feature metadata, and ListAvailableResourceDimensions to list available dimensions. The AdditionalMetrics field in DescribeDimensionKeys retrieves per-SQL metrics.
* api-change:``fms``: Shield Advanced policies for Amazon CloudFront resources now support automatic application layer DDoS mitigation. The max length for SecurityServicePolicyData ManagedServiceData is now 8192 characters, instead of 4096.
* api-change:``honeycode``: Honeycode is releasing new APIs to allow user to create, delete and list tags on resources.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``lexv2-models``: Update lexv2-models command to latest version


1.22.33
=======

* api-change:``iotevents-data``: This release provides documentation updates for Timer.timestamp in the IoT Events API Reference Guide.
* api-change:``kendra``: Amazon Kendra now supports advanced query language and query-less search.
* api-change:``ce``: Doc only update for Cost Explorer API that fixes missing clarifications for MatchOptions definitions
* api-change:``finspace-data``: Documentation updates for FinSpace.
* api-change:``rds``: This release adds the db-proxy event type to support subscribing to RDS Proxy events.
* api-change:``ec2``: EC2 Capacity Reservations now supports RHEL instance platforms (RHEL with SQL Server Standard, RHEL with SQL Server Enterprise, RHEL with SQL Server Web, RHEL with HA, RHEL with HA and SQL Server Standard, RHEL with HA and SQL Server Enterprise)
* api-change:``workspaces``: Introducing new APIs for Workspaces audio optimization with Amazon Connect: CreateConnectClientAddIn, DescribeConnectClientAddIns, UpdateConnectClientAddIn and DeleteConnectClientAddIn.


1.22.32
=======

* api-change:``lookoutmetrics``: This release adds FailureType in the response of DescribeAnomalyDetector.
* api-change:``compute-optimizer``: Adds support for new Compute Optimizer capability that makes it easier for customers to optimize their EC2 instances by leveraging multiple CPU architectures.
* api-change:``ec2``: New feature: Updated EC2 API to support faster launching for Windows images. Optimized images are pre-provisioned, using snapshots to launch instances up to 65% faster.
* api-change:``transcribe``: Documentation updates for Amazon Transcribe.
* api-change:``databrew``: This SDK release adds support for specifying a Bucket Owner for an S3 location.


1.22.31
=======

* api-change:``medialive``: This release adds support for selecting the Program Date Time (PDT) Clock source algorithm for HLS outputs.


1.22.30
=======

* api-change:``es``: Amazon OpenSearch Service adds support for Fine Grained Access Control for existing domains running Elasticsearch version 6.7 and above
* api-change:``ec2``: This release introduces On-Demand Capacity Reservation support for Cluster Placement Groups, adds Tags on instance Metadata, and includes documentation updates for Amazon EC2.
* api-change:``appsync``: AppSync: AWS AppSync now supports configurable batching sizes for AWS Lambda resolvers, Direct AWS Lambda resolvers and pipeline functions
* api-change:``iotwireless``: Downlink Queue Management feature provides APIs for customers to manage the queued messages destined to device inside AWS IoT Core for LoRaWAN. Customer can view, delete or purge the queued message(s). It allows customer to preempt the queued messages and let more urgent messages go through.
* api-change:``mwaa``: This release adds a "Source" field that provides the initiator of an update, such as due to an automated patch from AWS or due to modification via Console or API.
* api-change:``opensearch``: Amazon OpenSearch Service adds support for Fine Grained Access Control for existing domains running Elasticsearch version 6.7 and above
* api-change:``mediatailor``: This release adds support for filler slate when updating MediaTailor channels that use the linear playback mode.


1.22.29
=======

* api-change:``ec2``: This release adds a new API called ModifyVpcEndpointServicePayerResponsibility which allows VPC endpoint service owners to take payer responsibility of their VPC Endpoint connections.
* api-change:``sagemaker``: Amazon SageMaker now supports running training jobs on ml.g5 instance types.
* api-change:``iot``: This release adds an automatic retry mechanism for AWS IoT Jobs. You can now define a maximum number of retries for each Job rollout, along with the criteria to trigger the retry for FAILED/TIMED_OUT/ALL(both FAILED an TIMED_OUT) job.
* api-change:``glue``: Add Delta Lake target support for Glue Crawler and 3rd Party Support for Lake Formation
* api-change:``appstream``: Includes APIs for App Entitlement management regarding entitlement and entitled application association.
* api-change:``eks``: Amazon EKS now supports running applications using IPv6 address space
* api-change:``lakeformation``: Add new APIs for 3rd Party Support for Lake Formation
* api-change:``snowball``: Updating validation rules for interfaces used in the Snowball API to tighten security of service.
* api-change:``cloudtrail``: This release adds support for CloudTrail Lake, a new feature that lets you run SQL-based queries on events that you have aggregated into event data stores. New APIs have been added for creating and managing event data stores, and creating, running, and managing queries in CloudTrail Lake.
* api-change:``ecs``: Documentation update for ticket fixes.
* api-change:``quicksight``: Multiple Doc-only updates for Amazon QuickSight.


1.22.28
=======

* api-change:``s3control``: Documentation updates for the renaming of Glacier to Glacier Flexible Retrieval.
* api-change:``s3``: Minor doc-based updates based on feedback bugs received.
* api-change:``rekognition``: This release introduces a new field IndexFacesModelVersion, which is the version of the face detect and storage model that was used when indexing the face vector.


1.22.27
=======

* api-change:``sagemaker``: The release allows users to pass pipeline definitions as Amazon S3 locations and control the pipeline execution concurrency using ParallelismConfiguration. It also adds support of EMR jobs as pipeline steps.
* api-change:``rds``: Multiple doc-only updates for Relational Database Service (RDS)
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added strength levels to the Sharpness Filter and now permits OGG files to be specified as sidecar audio inputs.
* api-change:``detective``: Added and updated API operations to support the Detective integration with AWS Organizations. New actions are used to manage the delegated administrator account and the integration configuration.
* api-change:``greengrassv2``: This release adds the API operations to manage the Greengrass role associated with your account and to manage the core device connectivity information. Greengrass V2 customers can now depend solely on Greengrass V2 SDK for all the API operations needed to manage their fleets.


1.22.26
=======

* api-change:``qldb``: Amazon QLDB now supports journal exports in JSON and Ion Binary formats. This release adds an optional OutputFormat parameter to the ExportJournalToS3 API.
* api-change:``lookoutmetrics``: This release adds support for Causal Relationships. Added new ListAnomalyGroupRelatedMetrics API operation and InterMetricImpactDetails API data type
* api-change:``workmail``: This release allows customers to change their email monitoring configuration in Amazon WorkMail.
* api-change:``nimble``: Amazon Nimble Studio adds support for users to upload files during a streaming session using NICE DCV native client or browser.
* api-change:``transfer``: Property for Transfer Family used with the FTPS protocol. TLS Session Resumption provides a mechanism to resume or share a negotiated secret key between the control and data connection for an FTPS session.
* api-change:``imagebuilder``: Added a note to infrastructure configuration actions and data types concerning delivery of Image Builder event messages to encrypted SNS topics. The key that's used to encrypt the SNS topic must reside in the account that Image Builder runs under.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports updating message attributes via channel flows
* api-change:``mediaconnect``: You can now use the Fujitsu-QoS protocol for your MediaConnect sources and outputs to transport content to and from Fujitsu devices.


1.22.25
=======

* api-change:``devops-guru``: Adds Tags support to DescribeOrganizationResourceCollectionHealth
* api-change:``sagemaker``: This release adds a new ContentType field in AutoMLChannel for SageMaker CreateAutoMLJob InputDataConfig.
* api-change:``datasync``: AWS DataSync now supports FSx Lustre Locations.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``finspace-data``: Make dataset description optional and allow s3 export for dataviews
* api-change:``imagebuilder``: This release adds support for importing and exporting VM Images as part of the Image Creation workflow via EC2 VM Import/Export.
* api-change:``forecast``: Adds ForecastDimensions field to the DescribeAutoPredictorResponse
* api-change:``customer-profiles``: This release adds an optional parameter, ObjectTypeNames to the PutIntegration API to support multiple object types per integration option. Besides, this release introduces Standard Order Objects which contain data from third party systems and each order object belongs to a specific profile.
* api-change:``redshift``: This release adds API support for managed Redshift datashares. Customers can now interact with a Redshift datashare that is managed by a different service, such as AWS Data Exchange.
* api-change:``location``: Making PricingPlan optional as part of create resource API.
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for Firewall, and RuleGroup, FirewallPolicy Added additional details for AutoScalingGroup, LaunchConfiguration, and S3 buckets.


1.22.24
=======

* api-change:``secretsmanager``: Documentation updates for Secrets Manager


1.22.23
=======

* api-change:``savingsplans``: Adds the ability to specify Savings Plans hourly commitments using five digits after the decimal point.
* api-change:``sms``: This release adds SMS discontinuation information to the API and CLI references.
* api-change:``ec2``: Adds waiters support for internet gateways.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``route53domains``: Amazon Route 53 domain registration APIs now support filtering and sorting in the ListDomains API, deleting a domain by using the DeleteDomain API and getting domain pricing information by using the ListPrices API.
* api-change:``route53-recovery-control-config``: This release adds tagging supports to Route53 Recovery Control Configuration. New APIs: TagResource, UntagResource and ListTagsForResource. Updates: add optional field `tags` to support tagging while calling CreateCluster, CreateControlPanel and CreateSafetyRule.
* api-change:``network-firewall``: This release adds support for managed rule groups.
* bugfix:s3: Support for S3 Glacer Instant Retrieval storage class.  Fixes `#6587 <https://github.com/aws/aws-cli/issues/6587>`__


1.22.22
=======

* api-change:``health``: Documentation updates for AWS Health
* api-change:``logs``: This release adds AWS Organizations support as condition key in destination policy for cross account Subscriptions in CloudWatch Logs.
* api-change:``iot``: This release allows customer to enable caching of custom authorizer on HTTP protocol for clients that use persistent or Keep-Alive connection in order to reduce the number of Lambda invocations.
* api-change:``sagemaker``: This release added a new Ambarella device(amba_cv2) compilation support for Sagemaker Neo.
* api-change:``outposts``: This release adds the UpdateOutpost API.
* api-change:``lookoutvision``: This release adds new APIs for packaging an Amazon Lookout for Vision model as an AWS IoT Greengrass component.
* api-change:``comprehendmedical``: This release adds a new set of APIs (synchronous and batch) to support the SNOMED-CT ontology.
* api-change:``support``: Documentation updates for AWS Support.


1.22.21
=======

* api-change:``route53``: Add PriorRequestNotComplete exception to UpdateHostedZoneComment API
* api-change:``location``: This release adds support for Accuracy position filtering, position metadata and autocomplete for addresses and points of interest based on partial or misspelled free-form text.
* api-change:``appsync``: AWS AppSync now supports custom domain names, allowing you to associate a domain name that you own with an AppSync API in your account.


1.22.20
=======

* api-change:``rekognition``: This release added new KnownGender types for Celebrity Recognition.


1.22.19
=======

* api-change:``networkmanager``: This release adds API support for AWS Cloud WAN.
* api-change:``amplifyuibuilder``: This release introduces the actions and data types for the new Amplify UI Builder API. The Amplify UI Builder API provides a programmatic interface for creating and configuring user interface (UI) component libraries and themes for use in Amplify applications.
* api-change:``ram``: This release adds the ability to use the new ResourceRegionScope parameter on List operations that return lists of resources or resource types. This new parameter filters the results by letting you differentiate between global or regional resource types.


1.22.18
=======

* api-change:``devops-guru``: DevOps Guru now provides detailed, database-specific analyses of performance issues and recommends corrective actions for Amazon Aurora database instances with Performance Insights turned on. You can also use AWS tags to choose which resources to analyze and define your applications.
* api-change:``kendra``: Experience Builder allows customers to build search applications without writing code. Analytics Dashboard provides quality and usability metrics for Kendra indexes. Custom Document Enrichment allows customers to build a custom ingestion pipeline to pre-process documents and generate metadata.
* api-change:``dynamodb``: Add support for Table Classes and introduce the Standard Infrequent Access table class.
* api-change:``directconnect``: Adds SiteLink support to private and transit virtual interfaces. SiteLink is a new Direct Connect feature that allows routing between Direct Connect points of presence.
* api-change:``shield``: This release adds API support for Automatic Application Layer DDoS Mitigation for AWS Shield Advanced. Customers can now enable automatic DDoS mitigation in count or block mode for layer 7 protected resources.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: This release enables - 1/ Inference endpoint configuration recommendations and ability to run custom load tests to meet performance needs. 2/ Deploy serverless inference endpoints. 3/ Query, filter and retrieve end-to-end ML lineage graph, and incorporate model quality/bias detection in ML workflow.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``ec2``: This release adds support for Amazon VPC IP Address Manager (IPAM), which enables you to plan, track, and monitor IP addresses for your workloads. This release also adds support for VPC Network Access Analyzer, which enables you to analyze network access to resources in your Virtual Private Clouds.


1.22.17
=======

* api-change:``fsx``: This release adds support for the FSx for OpenZFS file system type, FSx for Lustre file systems with the Persistent_2 deployment type, and FSx for Lustre file systems with Amazon S3 data repository associations and automatic export policies.
* api-change:``s3``: Introduce Amazon S3 Glacier Instant Retrieval storage class and a new setting in S3 Object Ownership to disable ACLs for bucket and the objects in it.
* api-change:``storagegateway``: Added gateway type VTL_SNOW. Added new SNOWBALL HostEnvironment for gateways running on a Snowball device. Added new field HostEnvironmentId to serve as an identifier for the HostEnvironment on which the gateway is running.
* api-change:``kinesis``: Amazon Kinesis Data Streams now supports on demand streams.
* api-change:``accessanalyzer``: AWS IAM Access Analyzer now supports policy validation for resource policies attached to S3 buckets and access points. You can run additional policy checks by specifying the S3 resource type you want to attach to your resource policy.
* api-change:``kafka``: This release adds three new V2 APIs. CreateClusterV2 for creating both provisioned and serverless clusters. DescribeClusterV2 for getting information about provisioned and serverless clusters and ListClustersV2 for listing all clusters (both provisioned and serverless) in your account.
* api-change:``redshift-data``: Data API now supports serverless queries.
* api-change:``iot``: Added the ability to enable/disable IoT Fleet Indexing for Device Defender and Named Shadow information, and search them through IoT Fleet Indexing APIs.
* api-change:``snowball``: Tapeball is to integrate tape gateway onto snowball, it enables customer to transfer local data on the tape to snowball,and then ingest the data into tape gateway on the cloud.
* api-change:``glue``: Support for DataLake transactions
* api-change:``ec2``: This release adds support for Is4gen and Im4gn instances. This release also adds a new subnet attribute, enableLniAtDeviceIndex, to support local network interfaces, which are logical networking components that connect an EC2 instance to your on-premises network.
* api-change:``outposts``: This release adds the SupportedHardwareType parameter to CreateOutpost.
* api-change:``lakeformation``: This release adds support for row and cell-based access control in Lake Formation. It also adds support for Lake Formation Governed Tables, which support ACID transactions and automatic storage optimizations.
* api-change:``iottwinmaker``: AWS IoT TwinMaker makes it faster and easier to create, visualize and monitor digital twins of real-world systems like buildings, factories and industrial equipment to optimize operations. Learn more: https://docs.aws.amazon.com/iot-twinmaker/latest/apireference/Welcome.html (New Service) (Preview)
* api-change:``backup-gateway``: Initial release of AWS Backup gateway which enables you to centralize and automate protection of on-premises VMware and VMware Cloud on AWS workloads using AWS Backup.
* api-change:``workspaces-web``: This is the initial SDK release for Amazon WorkSpaces Web. Amazon WorkSpaces Web is a low-cost, fully managed WorkSpace built to deliver secure web-based workloads and software-as-a-service (SaaS) application access to users within existing web browsers.


1.22.16
=======

* api-change:``wellarchitected``: This update provides support for Well-Architected API users to use custom lens features.
* api-change:``inspector2``: This release adds support for the new Amazon Inspector API. The new Amazon Inspector can automatically discover and scan Amazon EC2 instances and Amazon ECR container images for software vulnerabilities and unintended network exposure, and report centralized findings across multiple AWS accounts.
* api-change:``ec2``: This release adds support for G5g and M6a instances. This release also adds support for Amazon EBS Snapshots Archive, a feature that enables you to archive your EBS snapshots; and Recycle Bin, a feature that enables you to protect your EBS snapshots against accidental deletion.
* api-change:``ecr``: This release adds supports for pull through cache rules and enhanced scanning.
* api-change:``rum``: This is the first public release of CloudWatch RUM
* api-change:``iotsitewise``: AWS IoT SiteWise now supports retention configuration for the hot tier storage.
* api-change:``dataexchange``: This release enables providers and subscribers to use Data Set, Job, and Asset operations to work with API assets from Amazon API Gateway. In addition, this release enables subscribers to use the SendApiAsset operation to invoke a provider's Amazon API Gateway API that they are entitled to.
* api-change:``ssm``: Added two new attributes to DescribeInstanceInformation called SourceId and SourceType along with new string filters SourceIds and SourceTypes to filter instance records.
* api-change:``rbin``: This release adds support for Recycle Bin.
* api-change:``s3``: Amazon S3 Event Notifications adds Amazon EventBridge as a destination and supports additional event types. The PutBucketNotificationConfiguration API can now skip validation of Amazon SQS, Amazon SNS and AWS Lambda destinations.
* api-change:``evidently``: Introducing Amazon CloudWatch Evidently. This is the first public release of Amazon CloudWatch Evidently.
* api-change:``compute-optimizer``: Adds support for the enhanced infrastructure metrics paid feature. Also adds support for two new sets of resource efficiency metrics, including savings opportunity metrics and performance improvement opportunity metrics.


1.22.15
=======

* api-change:``migration-hub-refactor-spaces``: This is the initial SDK release for AWS Migration Hub Refactor Spaces
* api-change:``textract``: This release adds support for synchronously analyzing identity documents through a new API: AnalyzeID
* api-change:``personalize``: This release adds API support for Recommenders and BatchSegmentJobs.
* api-change:``personalize-runtime``: This release adds inference support for Recommenders.


1.22.14
=======

* api-change:``pinpoint``: Added a One-Time Password (OTP) management feature. You can use the Amazon Pinpoint API to generate OTP codes and send them to your users as SMS messages. Your apps can then call the API to verify the OTP codes that your users input
* api-change:``iotdeviceadvisor``: Documentation update for Device Advisor GetEndpoint API
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``outposts``: This release adds new APIs for working with Outpost sites and orders.
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling.
* api-change:``mgn``: Application Migration Service now supports an additional replication method that does not require agent installation on each source server. This option is available for source servers running on VMware vCenter versions 6.7 and 7.0.


1.22.13
=======

* api-change:``autoscaling``: Customers can now configure predictive scaling policies to proactively scale EC2 Auto Scaling groups based on any CloudWatch metrics that more accurately represent the load on the group than the four predefined metrics. They can also use math expressions to further customize the metrics.
* api-change:``lambda``: Remove Lambda function url apis
* api-change:``imagebuilder``: This release adds support for sharing AMIs with Organizations within an EC2 Image Builder Distribution Configuration.
* api-change:``timestream-write``: This release adds support for multi-measure records and magnetic store writes. Multi-measure records allow customers to store multiple measures in a single table row. Magnetic store writes enable customers to write late arrival data (data with timestamp in the past) directly into the magnetic store.
* api-change:``timestream-query``: Releasing Amazon Timestream Scheduled Queries. It makes real-time analytics more performant and cost-effective for customers by calculating and storing frequently accessed aggregates, and other computations, typically used in operational dashboards, business reports, and other analytics applications
* api-change:``translate``: This release enables customers to use translation settings to mask profane words and phrases in their translation output.
* api-change:``iotsitewise``: AWS IoT SiteWise now accepts data streams that aren't associated with any asset properties. You can organize data by updating data stream associations.
* api-change:``proton``: This release adds APIs for getting the outputs and provisioned stacks for Environments, Pipelines, and ServiceInstances.  You can now add tags to EnvironmentAccountConnections.  It also adds APIs for working with PR-based provisioning.  Also, it adds APIs for syncing templates with a git repository.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``customer-profiles``: This release introduces a new auto-merging feature for profile matching. The auto-merging configurations can be set via CreateDomain API or UpdateDomain API. You can use GetIdentityResolutionJob API and ListIdentityResolutionJobs API to fetch job status.


1.22.12
=======

* api-change:``finspace-data``: Update documentation for createChangeset API.
* api-change:``redshift``: This release adds support for reserved node exchange with restore/resize
* api-change:``s3``: Introduce two new Filters to S3 Lifecycle configurations - ObjectSizeGreaterThan and ObjectSizeLessThan. Introduce a new way to trigger actions on noncurrent versions by providing the number of newer noncurrent versions along with noncurrent days.
* api-change:``ec2``: This release adds a new parameter ipv6Native to the allow creation of IPv6-only subnets using the CreateSubnet operation, and the operation ModifySubnetAttribute includes new parameters to modify subnet attributes to use resource-based naming and enable DNS resolutions for Private DNS name.
* api-change:``iotwireless``: Two new APIs, GetNetworkAnalyzerConfiguration and UpdateNetworkAnalyzerConfiguration, are added for the newly released Network Analyzer feature which enables customers to view real-time frame information and logs from LoRaWAN devices and gateways.
* api-change:``dynamodb``: DynamoDB PartiQL now supports ReturnConsumedCapacity, which returns capacity units consumed by PartiQL APIs if the request specified returnConsumedCapacity parameter. PartiQL APIs include ExecuteStatement, BatchExecuteStatement, and ExecuteTransaction.
* api-change:``lambda``: Release Lambda event source filtering for SQS, Kinesis Streams, and DynamoDB Streams.
* api-change:``rds``: Adds support for Multi-AZ DB clusters for RDS for MySQL and RDS for PostgreSQL.
* api-change:``sqs``: Amazon SQS adds a new queue attribute, SqsManagedSseEnabled, which enables server-side queue encryption using SQS owned encryption keys.
* api-change:``elasticache``: Adding support for r6gd instances for Redis with data tiering. In a cluster with data tiering enabled, when available memory capacity is exhausted, the least recently used data is automatically tiered to solid state drives for cost-effective capacity scaling with minimal performance impact.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``iotdeviceadvisor``: This release introduces a new feature for Device Advisor: ability to execute multiple test suites in parallel for given customer account. You can use GetEndpoint API to get the device-level test endpoint and call StartSuiteRun with "parallelRun=true" to run suites in parallel.
* api-change:``backup``: This release adds new opt-in settings for advanced features for DynamoDB backups
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ecs``: Documentation update for ARM support on Amazon ECS.
* api-change:``iot``: This release introduces a new feature, Managed Job Template, for AWS IoT Jobs Service. Customers can now use service provided managed job templates to easily create jobs for supported standard job actions.
* api-change:``macie2``: Documentation updates for Amazon Macie
* api-change:``workspaces``: Documentation updates for Amazon WorkSpaces
* api-change:``opensearch``: This release adds an optional parameter dry-run for the UpdateDomainConfig API to perform basic validation checks, and detect the deployment type that will be required for the configuration change, without actually applying the change.


1.22.11
=======

* api-change:``finspace-data``: Add new APIs for managing Datasets, Changesets, and Dataviews.
* api-change:``braket``: This release adds support for Amazon Braket Hybrid Jobs.
* api-change:``s3control``: Added Amazon CloudWatch publishing option for S3 Storage Lens metrics.
* api-change:``chime-sdk-meetings``: Added new APIs for enabling Echo Reduction with Voice Focus.
* api-change:``es``: This release adds an optional parameter dry-run for the UpdateElasticsearchDomainConfig API to perform basic validation checks, and detect the deployment type that will be required for the configuration change, without actually applying the change.
* api-change:``connect``: This release adds support for UpdateContactFlowMetadata, DeleteContactFlow and module APIs. For details, see the Release Notes in the Amazon Connect Administrator Guide.
* api-change:``ssm``: Adds new parameter to CreateActivation API . This parameter is for "internal use only".
* api-change:``eks``: Adding missing exceptions to RegisterCluster operation
* api-change:``dms``: Added new S3 endpoint settings to allow to convert the current UTC time into a specified time zone when a date partition folder is created. Using with 'DatePartitionedEnabled'.
* api-change:``rds``: Adds local backup support to Amazon RDS on AWS Outposts.
* api-change:``cloudformation``: This release include SDK changes for the feature launch of Stack Import to Service Managed StackSet.
* api-change:``quicksight``: Add support for Exasol data source, 1 click enterprise embedding and email customization.


1.22.10
=======

* api-change:``redshift``: Added support of default IAM role for CreateCluster, RestoreFromClusterSnapshot and ModifyClusterIamRoles APIs
* api-change:``appstream``: Includes APIs for managing resources for Elastic fleets: applications, app blocks, and application-fleet associations.
* api-change:``application-insights``: Application Insights now supports monitoring for HANA
* api-change:``lambda``: Add support for Lambda Function URLs. Customers can use Function URLs to create built-in HTTPS endpoints on their functions.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``batch``: Documentation updates for AWS Batch.
* api-change:``cloudformation``: The StackSets ManagedExecution feature will allow concurrency for non-conflicting StackSet operations and queuing the StackSet operations that conflict at a given time for later execution.
* api-change:``medialive``: This release adds support for specifying a SCTE-35 PID on input. MediaLive now supports SCTE-35 PID selection on inputs containing one or more active SCTE-35 PIDs.


1.22.9
======

* api-change:``databrew``: This SDK release adds the following new features: 1) PII detection in profile jobs, 2) Data quality rules, enabling validation of data quality in profile jobs, 3) SQL query-based datasets for Amazon Redshift and Snowflake data sources, and 4) Connecting DataBrew datasets with Amazon AppFlow flows.
* api-change:``ivs``: Add APIs for retrieving stream session information and support for filtering live streams by health.  For more information, see https://docs.aws.amazon.com/ivs/latest/userguide/stream-health.html
* api-change:``lambda``: Added support for CLIENT_CERTIFICATE_TLS_AUTH and SERVER_ROOT_CA_CERTIFICATE as SourceAccessType for MSK and Kafka event source mappings.
* api-change:``chime``: Adds new Transcribe API parameters to StartMeetingTranscription, including support for content identification and redaction (PII & PHI), partial results stabilization, and custom language models.
* api-change:``chime-sdk-meetings``: Adds new Transcribe API parameters to StartMeetingTranscription, including support for content identification and redaction (PII & PHI), partial results stabilization, and custom language models.
* api-change:``appconfig``: Add Type to support feature flag configuration profiles
* api-change:``forecast``: NEW CreateExplanability API that helps you understand how attributes such as price, promotion, etc. contributes to your forecasted values; NEW CreateAutoPredictor API that trains up to 40% more accurate forecasting model, saves up to 50% of retraining time, and provides model level explainability.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``kafka``: Amazon MSK has added a new API that allows you to update the connectivity settings for an existing cluster to enable public accessibility.
* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Dashboard views. You can now view insights data for your active assessments, and quickly identify non-compliant evidence that needs to be remediated.
* api-change:``redshift-data``: Rolling back Data API serverless features until dependencies are live.


1.22.8
======

* api-change:``apigateway``: Documentation updates for Amazon API Gateway.
* api-change:``amplifybackend``: New APIs to support the Amplify Storage category. Add and manage file storage in your Amplify app backend.
* api-change:``redshift-data``: Data API now supports serverless requests.
* api-change:``appconfigdata``: AWS AppConfig Data is a new service that allows you to retrieve configuration deployed by AWS AppConfig. See the AppConfig user guide for more details on getting started. https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
* api-change:``drs``: Introducing AWS Elastic Disaster Recovery (AWS DRS), a new service that minimizes downtime and data loss with fast, reliable recovery of on-premises and cloud-based applications using affordable storage, minimal compute, and point-in-time recovery.
* api-change:``sns``: Amazon SNS introduces the PublishBatch API, which enables customers to publish up to 10 messages per API request. The new API is valid for Standard and FIFO topics.


1.22.7
======

* api-change:``cloudtrail``: CloudTrail Insights now supports ApiErrorRateInsight, which enables customers to identify unusual activity in their AWS account based on API error codes and their rate.
* api-change:``location``: This release adds the support for Relevance, Distance, Time Zone, Language and Interpolated Address for Geocoding and Reverse Geocoding.


1.22.6
======

* api-change:``eks``: Adding Tags support to Cluster Registrations.
* api-change:``transfer``: AWS Transfer Family now supports integrating a custom identity provider using AWS Lambda
* api-change:``ec2``: Adds a new VPC Subnet attribute "EnableDns64." When enabled on IPv6 Subnets, the Amazon-Provided DNS Resolver returns synthetic IPv6 addresses for IPv4-only destinations.
* api-change:``ssm``: Adds support for Session Reason and Max Session Duration for Systems Manager Session Manager.
* api-change:``migrationhubstrategy``: AWS SDK for Migration Hub Strategy Recommendations. It includes APIs to start the portfolio assessment, import portfolio data for assessment, and to retrieve recommendations. For more information, see the AWS Migration Hub documentation at https://docs.aws.amazon.com/migrationhub/index.html
* api-change:``appstream``: This release includes support for images of AmazonLinux2 platform type.
* api-change:``wafv2``: Your options for logging web ACL traffic now include Amazon CloudWatch Logs log groups and Amazon S3 buckets.
* api-change:``dms``: Add Settings in JSON format for the source GCP MySQL endpoint


1.22.5
======

* api-change:``devops-guru``: Add support for cross account APIs.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added automatic modes for GOP configuration and added the ability to ingest screen recordings generated by Safari on MacOS 12 Monterey.
* api-change:``ec2``: C6i instances are powered by a third-generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz. G5 instances feature up to 8 NVIDIA A10G Tensor Core GPUs and second generation AMD EPYC processors.
* api-change:``ssm``: This Patch Manager release supports creating Patch Baselines for RaspberryPi OS (formerly Raspbian)
* api-change:``connect``: This release adds APIs for creating and managing scheduled tasks. Additionally, adds APIs to describe and update a contact and list associated references.


1.22.4
======

* api-change:``dynamodb``: Updated Help section for "dynamodb update-contributor-insights" API
* api-change:``translate``: This release enables customers to import Multi-Directional Custom Terminology and use Multi-Directional Custom Terminology in both real-time translation and asynchronous batch translation.
* api-change:``ec2``: This release provides an additional route target for the VPC route table.


1.22.3
======

* api-change:``backup``: AWS Backup SDK provides new options when scheduling backups: select supported services and resources that are assigned to a particular tag, linked to a combination of tags, or can be identified by a partial tag value, and exclude resources from their assignments.
* api-change:``resiliencehub``: Initial release of AWS Resilience Hub, a managed service that enables you to define, validate, and track the resilience of your applications on AWS
* api-change:``ecs``: This release adds support for container instance health.


1.22.2
======

* api-change:``greengrassv2``: This release adds support for Greengrass core devices running Windows. You can now specify name of a Windows user to run a component.
* api-change:``health``: Documentation updates for AWS Health.
* api-change:``batch``: Adds support for scheduling policy APIs.


1.22.0
======

* api-change:``wafv2``: You can now configure rules to run a CAPTCHA check against web requests and, as needed, send a CAPTCHA challenge to the client.
* api-change:``chime-sdk-meetings``: Updated format validation for ids and regions.
* api-change:``ec2``: This release adds internal validation on the GatewayAssociationState field
* api-change:``sagemaker``: SageMaker CreateEndpoint and UpdateEndpoint APIs now support additional deployment configuration to manage traffic shifting options and automatic rollback monitoring. DescribeEndpoint now shows new in-progress deployment details with stage status.
* feature:EndpointResolver: Adding support for resolving modeled FIPS and Dualstack endpoints. Added `AWS_USE_DUALSTACK_ENDPOINT` and `AWS_USE_FIPS_ENDPOINT` environment variables to enable these features.


1.21.12
=======

* api-change:``translate``: This release enable customers to use their own KMS keys to encrypt output files when they submit a batch transform job.
* api-change:``resourcegroupstaggingapi``: Documentation updates and improvements.
* api-change:``ec2``: DescribeInstances now returns customer-owned IP addresses for instances running on an AWS Outpost.


1.21.11
=======

* api-change:``sagemaker``: ListDevices and DescribeDevice now show Edge Manager agent version.
* api-change:``connect``: This release adds CRUD operation support for Security profile resource in Amazon Connect
* api-change:``chime-sdk-meetings``: The Amazon Chime SDK Meetings APIs allow software developers to create meetings and attendees for interactive audio, video, screen and content sharing in custom meeting applications which use the Amazon Chime SDK.
* api-change:``iotwireless``: Adding APIs for the FUOTA (firmware update over the air) and multicast for LoRaWAN devices and APIs to support event notification opt-in feature for Sidewalk related events. A few existing APIs need to be modified for this new feature.
* api-change:``ec2``: This release adds a new instance replacement strategy for EC2 Fleet, Spot Fleet. Now you can select an action to perform when your instance gets a rebalance notification. EC2 Fleet, Spot Fleet can launch a replacement then terminate the instance that received notification after a termination delay


1.21.10
=======

* api-change:``finspace``: Adds superuser and data-bundle parameters to CreateEnvironment API
* api-change:``macie2``: This release adds support for specifying the severity of findings that a custom data identifier produces, based on the number of occurrences of text that matches the detection criteria.
* api-change:``connectparticipant``: This release adds a new boolean attribute - Connect Participant - to the CreateParticipantConnection API, which can be used to mark the participant as connected.
* api-change:``datasync``: AWS DataSync now supports Hadoop Distributed File System (HDFS) Locations


1.21.9
======

* api-change:``nimble``: Amazon Nimble Studio adds support for users to stop and start streaming sessions.
* api-change:``cloudfront``: CloudFront now supports response headers policies to add HTTP headers to the responses that CloudFront sends to viewers. You can use these policies to add CORS headers, control browser caching, and more, without modifying your origin or writing any code.
* api-change:``connect``: Amazon Connect Chat now supports real-time message streaming.


1.21.8
======

* api-change:``lightsail``: This release adds support to enable access logging for buckets in the Lightsail object storage service.
* api-change:``rekognition``: This Amazon Rekognition Custom Labels release introduces the management of datasets with  projects
* api-change:``networkmanager``: This release adds API support to aggregate resources, routes, and telemetry data across a Global Network.
* api-change:``neptune``: Adds support for major version upgrades to ModifyDbCluster API


1.21.7
======

* api-change:``application-insights``: Added Monitoring support for SQL Server Failover Cluster Instance. Additionally, added a new API to allow one-click monitoring of containers resources.
* api-change:``rekognition``: This release added new attributes to Rekognition Video GetCelebrityRecognition API operations.
* api-change:``ec2``: Support added for AMI sharing with organizations and organizational units in ModifyImageAttribute API
* api-change:``transcribe``: Transcribe and Transcribe Call Analytics now support automatic language identification along with custom vocabulary, vocabulary filter, custom language model and PII redaction.
* api-change:``connect``: Amazon Connect Chat now supports real-time message streaming.


1.21.6
======

* api-change:``gamelift``: Added support for Arm-based AWS Graviton2 instances, such as M6g, C6g, and R6g.
* api-change:``connectparticipant``: This release adds a new boolean attribute - Connect Participant - to the CreateParticipantConnection API, which can be used to mark the participant as connected.
* api-change:``ssm-incidents``: Updating documentation, adding new field to ConflictException to indicate earliest retry timestamp for some operations, increase maximum length of nextToken fields
* api-change:``ec2``: Added new read-only DenyAllIGWTraffic network interface attribute. Added support for DL1 24xlarge instances powered by Habana Gaudi Accelerators for deep learning model training workloads
* api-change:``ecs``: Amazon ECS now supports running Fargate tasks on Windows Operating Systems Families which includes Windows Server 2019 Core and Windows Server 2019 Full.
* api-change:``sagemaker``: This release adds support for RStudio on SageMaker.


1.21.5
======

* api-change:``ec2``: This release adds: attribute-based instance type selection for EC2 Fleet, Spot Fleet, a feature that lets customers express instance requirements as attributes like vCPU, memory, and storage; and Spot placement score, a feature that helps customers identify an optimal location to run Spot workloads.
* api-change:``autoscaling``: This release adds support for attribute-based instance type selection, a new EC2 Auto Scaling feature that lets customers express their instance requirements as a set of attributes, such as vCPU, memory, and storage.
* api-change:``sagemaker``: This release allows customers to describe one or more versioned model packages through BatchDescribeModelPackage, update project via UpdateProject, modify and read customer metadata properties using Create, Update and Describe ModelPackage and enables cross account registration of model packages.
* api-change:``eks``: EKS managed node groups now support BOTTLEROCKET_x86_64 and BOTTLEROCKET_ARM_64 AMI types.
* api-change:``textract``: This release adds support for asynchronously analyzing invoice and receipt documents through two new APIs: StartExpenseAnalysis and GetExpenseAnalysis


1.21.4
======

* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports push notifications through Amazon Pinpoint
* api-change:``emr-containers``: This feature enables auto-generation of certificate  to secure the managed-endpoint and removes the need for customer provided certificate-arn during managed-endpoint setup.
* api-change:``chime-sdk-identity``: The Amazon Chime SDK now supports push notifications through Amazon Pinpoint


1.21.3
======

* api-change:``route53resolver``: New API for ResolverConfig, which allows autodefined rules for reverse DNS resolution to be disabled for a VPC
* api-change:``ec2``: This release adds support to create a VPN Connection that is not attached to a Gateway at the time of creation. Use this to create VPNs associated with Core Networks, or modify your VPN and attach a gateway using the modify API after creation.
* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Custom framework sharing. You can now share your custom frameworks with another AWS account, or replicate them into another AWS Region under your own account.
* api-change:``rds``: This release adds support for Amazon RDS Custom, which is a new RDS management type that gives you full access to your database and operating system. For more information, see https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-custom.html


1.21.2
======

* api-change:``chime``: Chime VoiceConnector and VoiceConnectorGroup APIs will now return an ARN.
* api-change:``quicksight``: Added QSearchBar option for GenerateEmbedUrlForRegisteredUser ExperienceConfiguration to support Q search bar embedding
* api-change:``auditmanager``: This release introduces character restrictions for ControlSet names. We updated regex patterns for the following attributes: ControlSet, CreateAssessmentFrameworkControlSet, and UpdateAssessmentFrameworkControlSet.


1.21.1
======

* api-change:``connect``: Released Amazon Connect hours of operation API for general availability (GA). This API also supports AWS CloudFormation. For more information, see Amazon Connect Resource Type Reference in the AWS CloudFormation User Guide.


1.21.0
======

* feature:Serialization: rest-json serialization defaults aligned across AWS SDKs
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for specifying caption time delta in milliseconds and the ability to apply color range legalization to source content other than AVC video.
* api-change:``panorama``: General availability for AWS Panorama. AWS SDK for Panorama includes APIs to manage your devices and nodes, and deploy computer vision applications to the edge. For more information, see the AWS Panorama documentation at http://docs.aws.amazon.com/panorama
* api-change:``directconnect``: This release adds 4 new APIS, which needs to be public able
* api-change:``appflow``: Feature to add support for  JSON-L format for S3 as a source.
* api-change:``securityhub``: Added support for cross-Region finding aggregation, which replicates findings from linked Regions to a single aggregation Region. Added operations to view, enable, update, and delete the finding aggregation.
* api-change:``mediapackage``: When enabled, MediaPackage passes through digital video broadcasting (DVB) subtitles into the output.
* api-change:``mediapackage-vod``: MediaPackage passes through digital video broadcasting (DVB) subtitles into the output.


1.20.65
=======

* api-change:``dataexchange``: This release adds support for our public preview of AWS Data Exchange for Amazon Redshift. This enables data providers to list products including AWS Data Exchange datashares for Amazon Redshift, giving subscribers read-only access to provider data in Amazon Redshift.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now allows developers to execute business logic on in-flight messages before they are delivered to members of a messaging channel with channel flows.


1.20.64
=======

* api-change:``quicksight``: AWS QuickSight Service  Features    - Add IP Restriction UI and public APIs support.
* api-change:``ivs``: Bug fix: remove unsupported maxResults and nextToken pagination parameters from ListTagsForResource


1.20.63
=======

* api-change:``glue``: Enable S3 event base crawler API.
* api-change:``efs``: Update efs command to latest version


1.20.62
=======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``sagemaker``: This release updates the provisioning artifact ID to an optional parameter in CreateProject API. The provisioning artifact ID defaults to the latest provisioning artifact ID of the product if you don't provide one.
* api-change:``robomaker``: Adding support to GPU simulation jobs as well as non-ROS simulation jobs.
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now supports filtering describe Auto Scaling groups API using tags


1.20.61
=======

* api-change:``workmail``: This release adds APIs for adding, removing and retrieving details of mail domains
* api-change:``ec2``: This release adds support for additional VPC Flow Logs delivery options to S3, such as Apache Parquet formatted files, Hourly partitions and Hive-compatible S3 prefixes
* api-change:``kinesisanalyticsv2``: Support for Apache Flink 1.13 in Kinesis Data Analytics. Changed the required status of some Update properties to better fit the corresponding Create properties.
* api-change:``config``: Adding Config support for AWS::OpenSearch::Domain
* api-change:``storagegateway``: Adding support for Audit Logs on NFS shares and Force Closing Files on SMB shares.


1.20.60
=======

* api-change:``ecs``: Documentation only update to address tickets.
* api-change:``mediatailor``: MediaTailor now supports ad prefetching.
* api-change:``cloudsearch``: Adds an additional validation exception for Amazon CloudSearch configuration APIs for better error handling.
* api-change:``ec2``: EncryptionSupport for InstanceStorageInfo added to DescribeInstanceTypes API


1.20.59
=======

* api-change:``frauddetector``: New model type: Transaction Fraud Insights, which is optimized for online transaction fraud. Stored Events, which allows customers to send and store data directly within Amazon Fraud Detector. Batch Import, which allows customers to upload a CSV file of historic event data for processing and storage
* api-change:``ec2``: Documentation update for Amazon EC2.
* api-change:``medialive``: This release adds support for Transport Stream files as an input type to MediaLive encoders.
* api-change:``elbv2``: Update elbv2 command to latest version


1.20.58
=======

* api-change:``mediaconvert``: AWS Elemental MediaConvert has added the ability to set account policies which control access restrictions for HTTP, HTTPS, and S3 content sources.
* api-change:``ec2``: This release removes a requirement for filters on SearchLocalGatewayRoutes operations.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for WAF rate-based rules, EC2 VPC endpoints, ECR repositories, EKS clusters, X-Ray encryption, and OpenSearch domains. Added additional details for CloudFront distributions, CodeBuild projects, ELB V2 load balancers, and S3 buckets.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version


1.20.57
=======

* api-change:``backup``: Launch of AWS Backup Vault Lock, which protects your backups from malicious and accidental actions, works with existing backup policies, and helps you meet compliance requirements.
* api-change:``grafana``: Initial release of the SDK for Amazon Managed Grafana API.
* api-change:``schemas``: Removing unused request/response objects.
* api-change:``firehose``: Allow support for Amazon Opensearch Service(successor to Amazon Elasticsearch Service) as a Kinesis Data Firehose delivery destination.
* api-change:``chime``: This release enables customers to configure Chime MediaCapturePipeline via API.
* api-change:``kendra``: Amazon Kendra now supports indexing and querying documents in different languages.


1.20.56
=======

* api-change:``sagemaker``: This release adds a new TrainingInputMode FastFile for SageMaker Training APIs.
* api-change:``amplifybackend``: Adding a new field 'AmplifyFeatureFlags' to the response of the GetBackend operation. It will return a stringified version of the cli.json file for the given Amplify project.
* api-change:``kendra``: Amazon Kendra now supports integration with AWS SSO
* api-change:``fsx``: This release adds support for Lustre 2.12 to FSx for Lustre.


1.20.55
=======

* api-change:``glue``: This release adds tag as an input of CreateConnection
* api-change:``location``: Add support for PositionFiltering.
* api-change:``ec2``: Released Capacity Reservation Fleet, a feature of Amazon EC2 Capacity Reservations, which provides a way to manage reserved capacity across instance types. For more information: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cr-fleets.html
* api-change:``workmail``: This release allows customers to change their inbound DMARC settings in Amazon WorkMail.
* api-change:``application-autoscaling``: With this release, Application Auto Scaling adds support for Amazon Neptune. Customers can now automatically add or remove Read Replicas of their Neptune clusters to keep the average CPU Utilization at the target value specified by the customers.
* api-change:``backup``: AWS Backup Audit Manager framework report.


1.20.54
=======

* api-change:``kms``: Added SDK examples for ConnectCustomKeyStore, CreateCustomKeyStore, CreateKey, DeleteCustomKeyStore, DescribeCustomKeyStores, DisconnectCustomKeyStore, GenerateDataKeyPair, GenerateDataKeyPairWithoutPlaintext, GetPublicKey, ReplicateKey, Sign, UpdateCustomKeyStore and Verify APIs
* api-change:``efs``: Update efs command to latest version
* api-change:``codebuild``: CodeBuild now allows you to select how batch build statuses are sent to the source provider for a project.


1.20.53
=======

* api-change:``synthetics``: CloudWatch Synthetics now enables customers to choose a customer managed AWS KMS key or an Amazon S3-managed key instead of an AWS managed key (default) for the encryption of artifacts that the canary stores in Amazon S3. CloudWatch Synthetics also supports artifact S3 location updation now.
* api-change:``apprunner``: This release contains several minor bug fixes.
* api-change:``ssm``: When "AutoApprovable" is true for a Change Template, then specifying --auto-approve (boolean) in Start-Change-Request-Execution will create a change request that bypasses approver review. (except for change calendar restrictions)


1.20.52
=======

* api-change:``account``: This release of the Account Management API enables customers to manage the alternate contacts for their AWS accounts. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/accounts-welcome.html
* api-change:``workmail``: This release adds support for mobile device access overrides management in Amazon WorkMail.
* api-change:``dataexchange``: This release enables subscribers to set up automatic exports of newly published revisions using the new EventAction API.
* api-change:``macie2``: Amazon S3 bucket metadata now indicates whether an error or a bucket's permissions settings prevented Amazon Macie from retrieving data about the bucket or the bucket's objects.
* api-change:``network-firewall``: This release adds support for strict ordering for stateful rule groups. Using strict ordering, stateful rules are evaluated in the exact order in which you provide them.
* api-change:``workspaces``: Added CreateUpdatedWorkspaceImage API to update WorkSpace images with latest software and drivers. Updated DescribeWorkspaceImages API to display if there are updates available for WorkSpace images.
* api-change:``cloudcontrol``: Initial release of the SDK for AWS Cloud Control API


1.20.51
=======

* api-change:``lambda``: Adds support for Lambda functions powered by AWS Graviton2 processors. Customers can now select the CPU architecture for their functions.
* api-change:``sesv2``: This release includes the ability to use 2048 bits RSA key pairs for DKIM in SES, either with Easy DKIM or Bring Your Own DKIM.
* api-change:``amp``: This release adds alert manager and rule group namespace APIs


1.20.50
=======

* api-change:``imagebuilder``: Fix description for AmiDistributionConfiguration Name property, which actually refers to the output AMI name. Also updated for consistent terminology to use "base" image, and another update to fix description text.
* api-change:``transfer``: Added changes for managed workflows feature APIs.


1.20.49
=======

* api-change:``appintegrations``: The Amazon AppIntegrations service enables you to configure and reuse connections to external applications.
* api-change:``wisdom``: Released Amazon Connect Wisdom, a feature of Amazon Connect, which provides real-time recommendations and search functionality in general availability (GA).  For more information, see https://docs.aws.amazon.com/wisdom/latest/APIReference/Welcome.html.
* api-change:``voice-id``: Released the Amazon Voice ID SDK, for usage with the Amazon Connect Voice ID feature released for Amazon Connect.
* api-change:``connect``: This release updates a set of APIs: CreateIntegrationAssociation, ListIntegrationAssociations, CreateUseCase, and StartOutboundVoiceContact. You can use it to create integrations with Amazon Pinpoint for the Amazon Connect Campaigns use case, Amazon Connect Voice ID, and Amazon Connect Wisdom.
* api-change:``pinpoint``: Added support for journey with contact center activity
* api-change:``elbv2``: Update elbv2 command to latest version


1.20.48
=======

* api-change:``license-manager``: AWS License Manager now allows customers to get the LicenseArn in the Checkout API Response.
* api-change:``ec2``: DescribeInstances now returns Platform Details, Usage Operation, and Usage Operation Update Time.


1.20.47
=======

* api-change:``mediaconvert``: This release adds style and positioning support for caption or subtitle burn-in from rich text sources such as TTML. This release also introduces configurable image-based trick play track generation.
* api-change:``appsync``: Documented the new OpenSearchServiceDataSourceConfig data type. Added deprecation notes to the ElasticsearchDataSourceConfig data type.
* api-change:``ssm``: Added cutoff behavior support for preventing new task invocations from starting when the maintenance window cutoff time is reached.


1.20.46
=======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``wafv2``: Added the regex match rule statement, for matching web requests against a single regular expression.
* api-change:``imagebuilder``: This feature adds support for specifying GP3 volume throughput and configuring instance metadata options for instances launched by EC2 Image Builder.
* api-change:``iam``: Added changes to OIDC API about not using port numbers in the URL.
* api-change:``mediapackage-vod``: MediaPackage VOD will now return the current processing statuses of an asset's endpoints. The status can be QUEUED, PROCESSING, PLAYABLE, or FAILED.
* api-change:``mediatailor``: This release adds support to configure logs for playback configuration.
* api-change:``license-manager``: AWS License Manager now allows customers to change their Windows Server or SQL license types from Bring-Your-Own-License (BYOL) to License Included or vice-versa (using the customer's media).


1.20.45
=======

* api-change:``ecr``: This release adds additional support for repository replication
* api-change:``comprehend``: Amazon Comprehend now supports versioning of custom models, improved training with ONE_DOC_PER_FILE text documents for custom entity recognition, ability to provide specific test sets during training, and live migration to new model endpoints.
* api-change:``ec2``: This update adds support for downloading configuration templates using new APIs (GetVpnConnectionDeviceTypes and GetVpnConnectionDeviceSampleConfiguration) and Internet Key Exchange version 2 (IKEv2) parameters for many popular CGW devices.
* api-change:``iot``: This release adds support for verifying, viewing and filtering AWS IoT Device Defender detect violations with four verification states.


1.20.44
=======

* api-change:``dms``: Optional flag force-planned-failover added to reboot-replication-instance API call. This flag can be used to test a planned failover scenario used during some maintenance operations.
* api-change:``es``: This release adds an optional parameter in the ListDomainNames API to filter domains based on the engine type (OpenSearch/Elasticsearch).
* api-change:``opensearch``: This release adds an optional parameter in the ListDomainNames API to filter domains based on the engine type (OpenSearch/Elasticsearch).


1.20.43
=======

* api-change:``pinpoint``: This SDK release adds a new feature for Pinpoint campaigns, in-app messaging.
* api-change:``sagemaker``: Add API for users to retry a failed pipeline execution or resume a stopped one.
* api-change:``transcribe``: This release adds support for subtitling with Amazon Transcribe batch jobs.
* api-change:``s3``: Add support for access point arn filtering in S3 CW Request Metrics
* api-change:``robomaker``: Adding support to create container based Robot and Simulation applications by introducing an environment field
* api-change:``macie2``: This release adds support for specifying which managed data identifiers are used by a classification job, and retrieving a list of managed data identifiers that are available.
* api-change:``kafkaconnect``: This is the initial SDK release for Amazon Managed Streaming for Apache Kafka Connect (MSK Connect).


1.20.42
=======

* api-change:``wafv2``: This release adds support for including rate based rules in a rule group.
* api-change:``sagemaker``: This release adds support for "Project Search"
* api-change:``ec2``: This release adds support for vt1 3xlarge, 6xlarge and 24xlarge instances powered by Xilinx Alveo U30 Media Accelerators for video transcoding workloads
* api-change:``chime``: Adds support for SipHeaders parameter for CreateSipMediaApplicationCall.
* api-change:``comprehend``: Amazon Comprehend now allows you to train and run PDF and Word documents for custom entity recognition. With PDF and Word formats, you can extract information from documents containing headers, lists and tables.


1.20.41
=======

* api-change:``iot``: AWS IoT Rules Engine adds OpenSearch action. The OpenSearch rule action lets you stream data from IoT sensors and applications to Amazon OpenSearch Service which is a successor to Amazon Elasticsearch Service.
* api-change:``ec2``: Adds support for T3 instances on Amazon EC2 Dedicated Hosts.


1.20.40
=======

* api-change:``rds``: This release adds support for providing a custom timeout value for finding a scaling point during autoscaling in Aurora Serverless v1.
* api-change:``sagemaker``: This release adds support for "Lifecycle Configurations" to SageMaker Studio
* api-change:``transcribe``: This release adds an API option for startTranscriptionJob and startMedicalTranscriptionJob that allows the user to specify encryption context key value pairs for batch jobs.
* api-change:``cloudformation``: Doc only update for CloudFormation that fixes several customer-reported issues.
* api-change:``ecr``: This release updates terminology around KMS keys.
* api-change:``quicksight``: Add new data source type for Amazon OpenSearch (successor to Amazon ElasticSearch).


1.20.39
=======

* api-change:``emr``: Update emr command to latest version
* api-change:``codeguru-reviewer``: The Amazon CodeGuru Reviewer API now includes the RuleMetadata data object and a Severity attribute on a RecommendationSummary object. A RuleMetadata object contains information about a rule that generates a recommendation. Severity indicates how severe the issue associated with a recommendation is.
* api-change:``lookoutequipment``: Added OffCondition parameter to CreateModel API


1.20.38
=======

* api-change:``ram``: A minor text-only update that fixes several customer issues.
* api-change:``opensearch``: Updated Configuration APIs for Amazon OpenSearch Service (successor to Amazon Elasticsearch Service)
* api-change:``kafka``: Amazon MSK has added a new API that allows you to update the encrypting and authentication settings for an existing cluster.


1.20.37
=======

* api-change:``forecast``: Predictor creation now supports selecting an accuracy metric to optimize in AutoML and hyperparameter optimization. This release adds additional accuracy metrics for predictors - AverageWeightedQuantileLoss, MAPE and MASE.
* api-change:``ssm-contacts``: Added SDK examples for SSM-Contacts.
* api-change:``amp``: This release adds tagging support for Amazon Managed Service for Prometheus workspace.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``mediapackage``: SPEKE v2 support for live CMAF packaging type. SPEKE v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, it supports live DASH currently.
* api-change:``xray``: Updated references to AWS KMS keys and customer managed keys to reflect current terminology.
* api-change:``eks``: Adding RegisterCluster and DeregisterCluster operations, to support connecting external clusters to EKS.


1.20.36
=======

* api-change:``chime-sdk-identity``: Documentation updates for Chime
* api-change:``codeguru-reviewer``: Added support for CodeInconsistencies detectors
* api-change:``frauddetector``: Enhanced GetEventPrediction API response to include risk scores from imported SageMaker models
* api-change:``chime-sdk-messaging``: Documentation updates for Chime
* api-change:``outposts``: This release adds a new API CreateOrder.


1.20.35
=======

* api-change:``securityhub``: New ASFF Resources: AwsAutoScalingLaunchConfiguration, AwsEc2VpnConnection, AwsEcrContainerImage. Added KeyRotationStatus to AwsKmsKey. Added AccessControlList, BucketLoggingConfiguration,BucketNotificationConfiguration and BucketNotificationConfiguration to AwsS3Bucket.
* api-change:``s3control``: S3 Multi-Region Access Points provide a single global endpoint to access a data set that spans multiple S3 buckets in different AWS Regions.
* api-change:``schemas``: This update include the support for Schema Discoverer to discover the events sent to the bus from another account. The feature will be enabled by default when discoverer is created or updated but can also be opt-in or opt-out  by specifying the value for crossAccount.
* api-change:``transfer``: AWS Transfer Family introduces Managed Workflows for creating, executing, monitoring, and standardizing post file transfer processing
* enhancement:``s3``: Add support for multi-region access points.
* api-change:``lex-models``: Lex now supports Korean (ko-KR) locale.
* api-change:``acm-pca``: Private Certificate Authority Service now allows customers to enable an online certificate status protocol (OCSP) responder service on their private certificate authorities. Customers can also optionally configure a custom CNAME for their OCSP responder.
* api-change:``fsx``: Announcing Amazon FSx for NetApp ONTAP, a new service that provides fully managed shared storage in the AWS Cloud with the data access and management capabilities of ONTAP.
* api-change:``accessanalyzer``: Updates service API, documentation, and paginators to support multi-region access points from Amazon S3.
* api-change:``ebs``: Documentation updates for Amazon EBS direct APIs.
* api-change:``quicksight``: This release adds support for referencing parent datasets as sources in a child dataset.
* api-change:``efs``: Update efs command to latest version


1.20.34
=======

* api-change:``mediatailor``: This release adds support for wall clock programs in LINEAR channels.
* api-change:``servicecatalog-appregistry``: Introduction of GetAssociatedResource API and GetApplication response extension for Resource Groups support.
* api-change:``cloudtrail``: Documentation updates for CloudTrail
* api-change:``config``: Documentation updates for config
* api-change:``ec2``: Added LaunchTemplate support for the IMDS IPv6 endpoint
* enhancement:emr-containers: Adds addition aws partition support for update-role-trust-policy


1.20.33
=======

* api-change:``iot``: Added Create/Update/Delete/Describe/List APIs for a new IoT resource named FleetMetric. Added a new Fleet Indexing query API named GetBucketsAggregation. Added a new field named DisconnectedReason in Fleet Indexing query response. Updated their related documentations.
* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer
* api-change:``sqs``: Amazon SQS adds a new queue attribute, RedriveAllowPolicy, which includes the dead-letter queue redrive permission parameters. It defines which source queues can specify dead-letter queues as a JSON object.
* api-change:``memorydb``: Documentation updates for MemoryDB
* api-change:``polly``: Amazon Polly adds new South African English voice - Ayanda. Ayanda is available as Neural voice only.


1.20.32
=======

* api-change:``cloudformation``: AWS CloudFormation allows you to iteratively develop your applications when failures are encountered without rolling back successfully provisioned resources. By specifying stack failure options, you can troubleshoot resources in a CREATE_FAILED or UPDATE_FAILED status.
* api-change:``codebuild``: Documentation updates for CodeBuild
* api-change:``kms``: This release has changes to KMS nomenclature to remove the word master from both the "Customer master key" and "CMK" abbreviation and replace those naming conventions with "KMS key".
* api-change:``firehose``: This release adds the Dynamic Partitioning feature to Kinesis Data Firehose service for S3 destinations.


1.20.31
=======

* api-change:``ec2``: This release adds the BootMode flag to the ImportImage API and showing the detected BootMode of an ImportImage task.
* api-change:``s3``: Documentation updates for Amazon S3.
* api-change:``emr``: Update emr command to latest version


1.20.30
=======

* api-change:``ec2``: Support added for resizing VPC prefix lists
* api-change:``rekognition``: This release added new attributes to Rekognition RecognizeCelebities and GetCelebrityInfo API operations.
* api-change:``compute-optimizer``: Adds support for 1) the AWS Graviton (AWS_ARM64) recommendation preference for Amazon EC2 instance and Auto Scaling group recommendations, and 2) the ability to get the enrollment statuses for all member accounts of an organization.
* api-change:``transcribe``: This release adds support for batch transcription in six new languages - Afrikaans, Danish, Mandarin Chinese (Taiwan), New Zealand English, South African English, and Thai.


1.20.29
=======

* api-change:``ec2``: Support added for IMDS IPv6 endpoint
* api-change:``events``: AWS CWEvents adds an enum of EXTERNAL for EcsParameters LaunchType for PutTargets API
* api-change:``fms``: AWS Firewall Manager now supports triggering resource cleanup workflow when account or resource goes out of policy scope for AWS WAF, Security group, AWS Network Firewall, and Amazon Route 53 Resolver DNS Firewall policies.
* api-change:``datasync``: Added include filters to CreateTask and UpdateTask, and added exclude filters to StartTaskExecution, giving customers more granular control over how DataSync transfers files, folders, and objects.


1.20.28
=======

* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added MBAFF encoding support for AVC video and the ability to pass encryption context from the job settings to S3.
* api-change:``iot-data``: Updated Publish with support for new Retain flag and added two new API operations: GetRetainedMessage, ListRetainedMessages.
* api-change:``ssm``: Updated Parameter Store property for logging improvements.
* api-change:``transcribe``: This release adds support for feature tagging with Amazon Transcribe batch jobs.
* api-change:``polly``: Amazon Polly adds new New Zealand English voice - Aria. Aria is available as Neural voice only.


1.20.27
=======

* api-change:``dlm``: Added AMI deprecation support for Amazon Data Lifecycle Manager EBS-backed AMI policies.
* api-change:``iotsitewise``: Documentation updates for AWS IoT SiteWise
* api-change:``glue``: Add support for Custom Blueprints
* api-change:``dms``: Amazon AWS DMS service now support Redis target endpoint migration. Now S3 endpoint setting is capable to setup features which are used to be configurable only in extract connection attributes.
* api-change:``backup``: AWS Backup - Features: Evaluate your backup activity and generate audit reports.
* api-change:``apigateway``: Adding some of the pending releases (1) Adding WAF Filter to GatewayResponseType enum (2) Ensuring consistent error model for all operations (3) Add missing BRE to GetVpcLink operation
* api-change:``frauddetector``: Updated an element of the DescribeModelVersion API response (LogitMetrics -> logOddsMetrics) for clarity. Added new exceptions to several APIs to protect against unlikely scenarios.


1.20.26
=======

* api-change:``eks``: Adds support for EKS add-ons "preserve" flag, which allows customers to maintain software on their EKS clusters after removing it from EKS add-ons management.
* api-change:``ec2``: encryptionInTransitSupported added to DescribeInstanceTypes API
* api-change:``robomaker``: Documentation updates for RoboMaker
* api-change:``comprehend``: Add tagging support for Comprehend async inference job.


1.20.25
=======

* api-change:``memorydb``: AWS MemoryDB  SDK now supports all APIs for newly launched MemoryDB service.
* api-change:``ec2``: The ImportImage API now supports the ability to create AMIs with AWS-managed licenses for Microsoft SQL Server for both Windows and Linux.
* api-change:``application-autoscaling``: This release extends Application Auto Scaling support for replication group of Amazon ElastiCache Redis clusters. Auto Scaling monitors and automatically expands node group count and number of replicas per node group when a critical usage threshold is met or according to customer-defined schedule.
* api-change:``appflow``: This release adds support for SAPOData connector and extends Veeva connector for document extraction.


1.20.24
=======

* api-change:``codebuild``: CodeBuild now allows you to make the build results for your build projects available to the public without requiring access to an AWS account.
* api-change:``route53resolver``: Documentation updates for Route 53 Resolver
* api-change:``route53``: Documentation updates for route53
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: Amazon SageMaker now supports Asynchronous Inference endpoints. Adds PlatformIdentifier field that allows Notebook Instance creation with different platform selections. Increases the maximum number of containers in multi-container endpoints to 15. Adds more instance types to InstanceType field.


1.20.23
=======

* api-change:``ce``: This release is a new feature for Cost Categories: Split charge rules. Split charge rules enable you to allocate shared costs between your cost category values.
* api-change:``clouddirectory``: Documentation updates for clouddirectory
* api-change:``cloud9``: Added DryRun parameter to CreateEnvironmentEC2 API. Added ManagedCredentialsActions parameter to UpdateEnvironment API
* api-change:``ec2``: This release adds support for EC2 ED25519 key pairs for authentication
* api-change:``logs``: Documentation-only update for CloudWatch Logs


1.20.22
=======

* api-change:``config``: Update ResourceType enum with values for Backup Plan, Selection, Vault, RecoveryPoint; ECS Cluster, Service, TaskDefinition; EFS AccessPoint, FileSystem; EKS Cluster; ECR Repository resources
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``license-manager``: AWS License Manager now allows end users to call CheckoutLicense API using new CheckoutType PERPETUAL. Perpetual checkouts allow sellers to check out a quantity of entitlements to be drawn down for consumption.
* api-change:``iotsitewise``: AWS IoT SiteWise added query window for the interpolation interval. AWS IoT SiteWise computes each interpolated value by using data points from the timestamp of each interval minus the window to the timestamp of each interval plus the window.
* api-change:``ds``: This release adds support for describing client authentication settings.
* api-change:``codebuild``: CodeBuild now allows you to select how batch build statuses are sent to the source provider for a project.


1.20.21
=======

* api-change:``customer-profiles``: This release introduces Standard Profile Objects, namely Asset and Case which contain values populated by data from third party systems and belong to a specific profile. This release adds an optional parameter, ObjectFilter to the ListProfileObjects API in order to search for these Standard Objects.
* api-change:``elasticache``: This release adds ReplicationGroupCreateTime field to ReplicationGroup which indicates the UTC time when ElastiCache ReplicationGroup is created
* api-change:``emr``: Update emr command to latest version
* api-change:``quicksight``: Documentation updates for QuickSight.


1.20.20
=======

* api-change:``sagemaker``: Amazon SageMaker Autopilot adds new metrics for all candidate models generated by Autopilot experiments.
* api-change:``databrew``: This SDK release adds support for the output of a recipe job results to Tableau Hyper format.
* api-change:``apigatewayv2``: Adding support for ACM imported or private CA certificates for mTLS enabled domain names
* api-change:``apigateway``: Adding support for ACM imported or private CA certificates for mTLS enabled domain names
* api-change:``lambda``: Lambda Python 3.9 runtime launch


1.20.19
=======

* api-change:``codebuild``: CodeBuild now allows you to make the build results for your build projects available to the public without requiring access to an AWS account.
* api-change:``route53``: Documentation updates for route53
* api-change:``snow-device-management``: AWS Snow Family customers can remotely monitor and operate their connected AWS Snowcone devices.
* api-change:``ecs``: Documentation updates for ECS.
* api-change:``nimble``: Add new attribute 'ownedBy' in Streaming Session APIs. 'ownedBy' represents the AWS SSO Identity Store User ID of the owner of the Streaming Session resource.
* api-change:``ebs``: Documentation updates for Amazon EBS direct APIs.


1.20.18
=======

* api-change:``chime``: Add support for "auto" in Region field of StartMeetingTranscription API request.


1.20.17
=======

* api-change:``wafv2``: This release adds APIs to support versioning feature of AWS WAF Managed rule groups
* api-change:``rekognition``: This release adds support for four new types of segments (opening credits, content segments, slates, and studio logos), improved accuracy for credits and shot detection and new filters to control black frame detection.
* api-change:``ssm``: Documentation updates for AWS Systems Manager.


1.20.16
=======

* api-change:``athena``: Documentation updates for Athena.
* api-change:``synthetics``: Documentation updates for Visual Monitoring feature and other doc ticket fixes.
* api-change:``chime-sdk-identity``: The Amazon Chime SDK Identity APIs allow software developers to create and manage unique instances of their messaging applications.
* api-change:``connect``: This release adds support for agent status and hours of operation. For details, see the Release Notes in the Amazon Connect Administrator Guide.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK Messaging APIs allow software developers to send and receive messages in custom messaging applications.
* api-change:``lightsail``: This release adds support to track when a bucket access key was last used.


1.20.15
=======

* api-change:``autoscaling``: EC2 Auto Scaling adds configuration checks and Launch Template validation to Instance Refresh.
* api-change:``lexv2-models``: Update lexv2-models command to latest version


1.20.14
=======

* api-change:``events``: Update events command to latest version
* api-change:``ssm-incidents``: Documentation updates for Incident Manager.
* api-change:``imagebuilder``: Updated list actions to include a list of valid filters that can be used in the request.
* api-change:``rds``: This release adds AutomaticRestartTime to the DescribeDBInstances and DescribeDBClusters operations. AutomaticRestartTime indicates the time when a stopped DB instance or DB cluster is restarted automatically.
* api-change:``transcribe``: This release adds support for call analytics (batch) within Amazon Transcribe.


1.20.13
=======

* api-change:``proton``: Docs only add idempotent create apis
* api-change:``iotsitewise``: My AWS Service (placeholder) - This release introduces custom Intervals and offset for tumbling window in metric for AWS IoT SiteWise.
* api-change:``glue``: Add ConcurrentModificationException to create-table, delete-table, create-database, update-database, delete-database
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added control over the passthrough of XDS captions metadata to outputs.
* api-change:``redshift``: API support for Redshift Data Sharing feature.


1.20.12
=======

* api-change:``ssm-contacts``: Added new attribute in AcceptCode API. AcceptCodeValidation takes in two values - ENFORCE, IGNORE. ENFORCE forces validation of accept code and IGNORE ignores it which is also the default behavior; Corrected TagKeyList length from 200 to 50
* api-change:``greengrassv2``: This release adds support for component system resource limits and idempotent Create operations. You can now specify the maximum amount of CPU and memory resources that each component can use.
* bugfix:``eks``: Fixes `#6308 <https://github.com/aws/aws-cli/issues/6308>`__ version mismatch running eks get-login without eks update-config


1.20.11
=======

* api-change:``secretsmanager``: Add support for KmsKeyIds in the ListSecretVersionIds API response
* api-change:``appsync``: AWS AppSync now supports a new authorization mode allowing you to define your own authorization logic using an AWS Lambda function.
* api-change:``sagemaker``: API changes with respect to Lambda steps in model building pipelines. Adds several waiters to async Sagemaker Image APIs. Add more instance types to AppInstanceType field
* api-change:``elbv2``: Update elbv2 command to latest version


1.20.10
=======

* api-change:``iot``: Increase maximum credential duration of role alias to 12 hours.
* api-change:``chime``: Adds support for live transcription of meetings with Amazon Transcribe and Amazon Transcribe Medical.  The new APIs, StartMeetingTranscription and StopMeetingTranscription, control the generation of user-attributed transcriptions sent to meeting clients via Amazon Chime SDK data messages.
* api-change:``ec2``: This release adds support for G4ad xlarge and 2xlarge instances powered by AMD Radeon Pro V520 GPUs and AMD 2nd Generation EPYC processors
* api-change:``iotsitewise``: Added support for AWS IoT SiteWise Edge. You can now create an AWS IoT SiteWise gateway that runs on AWS IoT Greengrass V2. With the gateway,  you can collect local server and equipment data, process the data, and export the selected data from the edge to the AWS Cloud.
* api-change:``savingsplans``: Documentation update for valid Savings Plans offering ID pattern


1.20.9
======

* api-change:``sso-admin``: Documentation updates for arn:aws:trebuchet:::service:v1:03a2216d-1cda-4696-9ece-1387cb6f6952
* api-change:``cloudformation``: SDK update to support Importing existing Stacks to new/existing Self Managed StackSet - Stack Import feature.
* enhancement:eks: Updated Kubernetes client authentication API version


1.20.8
======

* api-change:``route53``: This release adds support for the RECOVERY_CONTROL health check type to be used in conjunction with Route53 Application Recovery Controller.
* api-change:``route53-recovery-control-config``: Amazon Route 53 Application Recovery Controller's routing control - Routing Control Configuration APIs help you create and delete clusters, control panels, routing controls and safety rules. State changes (On/Off) of routing controls are not part of configuration APIs.
* api-change:``iotwireless``: Add SidewalkManufacturingSn as an identifier to allow Customer to query WirelessDevice, in the response, AmazonId is added in the case that Sidewalk device is return.
* api-change:``iotanalytics``: IoT Analytics now supports creating a dataset resource with IoT SiteWise MultiLayerStorage data stores, enabling customers to query industrial data within the service. This release includes adding JOIN functionality for customers to query multiple data sources in a dataset.
* api-change:``route53-recovery-cluster``: Amazon Route 53 Application Recovery Controller's routing control - Routing Control Data Plane APIs help you update the state (On/Off) of the routing controls to reroute traffic across application replicas in a 100% available manner.
* api-change:``route53-recovery-readiness``: Amazon Route 53 Application Recovery Controller's readiness check capability continually monitors resource quotas, capacity, and network routing policies to ensure that the recovery environment is scaled and configured to take over when needed.
* api-change:``redshift-data``: Added structures to support new Data API operation BatchExecuteStatement, used to execute multiple SQL statements within a single transaction.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``quicksight``: Add support to use row-level security with tags when embedding dashboards for users not provisioned in QuickSight
* api-change:``batch``: Add support for ListJob filters
* api-change:``shield``: Change name of DDoS Response Team (DRT) to Shield Response Team (SRT)


1.20.7
======

* api-change:``identitystore``: Documentation updates for SSO API Ref.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``synthetics``: CloudWatch Synthetics now supports visual testing in its canaries.
* api-change:``s3control``: S3 Access Point aliases can be used anywhere you use S3 bucket names to access data in S3
* api-change:``proton``: Documentation-only update links
* api-change:``textract``: Adds support for AnalyzeExpense, a new API to extract relevant data such as contact information, items purchased, and vendor name, from almost any invoice or receipt without the need for any templates or configuration.


1.20.6
======

* api-change:``s3outposts``: Add on-premise access type support for endpoints
* api-change:``securityhub``: Added product name, company name, and Region fields for security findings. Added details objects for RDS event subscriptions and AWS ECS services. Added fields to the details for AWS Elasticsearch domains.
* api-change:``imagebuilder``: Update to documentation to reapply missing change to SSM uninstall switch default value and improve description.


1.20.5
======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``databrew``: This SDK release adds two new features: 1) Output to Native JDBC destinations and 2) Adding configurations to profile jobs
* api-change:``s3control``: Documentation updates for Amazon S3-control
* api-change:``qldb``: Amazon QLDB now supports ledgers encrypted with customer managed KMS keys. Changes in CreateLedger, UpdateLedger and DescribeLedger APIs to support the changes.
* api-change:``medialive``: MediaLive now supports passing through style data on WebVTT caption outputs.
* api-change:``ec2``: This release allows customers to assign prefixes to their elastic network interface and to reserve IP blocks in their subnet CIDRs. These reserved blocks can be used to assign prefixes to elastic network interfaces or be excluded from auto-assignment.


1.20.4
======

* api-change:``lambda``: New ResourceConflictException error code for PutFunctionEventInvokeConfig, UpdateFunctionEventInvokeConfig, and DeleteFunctionEventInvokeConfig operations.
* api-change:``emr``: Update emr command to latest version
* api-change:``personalize``: My AWS Service (placeholder) - Making minProvisionedTPS an optional parameter when creating a campaign. If not provided, it defaults to 1.
* api-change:``rds``: Adds the OriginalSnapshotCreateTime field to the DBSnapshot response object. This field timestamps the underlying data of a snapshot and doesn't change when the snapshot is copied.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Amazon WorkDocs. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-workdocs.html
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``codebuild``: AWS CodeBuild now allows you to set the access permissions for build artifacts, project artifacts, and log files that are uploaded to an Amazon S3 bucket that is owned by another account.
* api-change:``proton``: Documentation updates for AWS Proton
* api-change:``elbv2``: Update elbv2 command to latest version


1.20.3
======

* api-change:``ec2``: Added idempotency to the CreateVolume API using the ClientToken request parameter
* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer


1.20.2
======

* api-change:``health``: In the Health API, the maximum number of entities for the EventFilter and EntityFilter data types has changed from 100 to 99. This change is related to an internal optimization of the AWS Health service.
* api-change:``location``: Add five new API operations: UpdateGeofenceCollection, UpdateMap, UpdatePlaceIndex, UpdateRouteCalculator, UpdateTracker.
* api-change:``directconnect``: Documentation updates for directconnect
* api-change:``imagebuilder``: Documentation updates for reversal of default value for additional instance configuration SSM switch, plus improved descriptions for semantic versioning.
* api-change:``robomaker``: This release allows customers to create a new version of WorldTemplates with support for Doors.
* api-change:``emr-containers``: Updated DescribeManagedEndpoint and ListManagedEndpoints to return failureReason and stateDetails in API response.


1.20.1
======

* api-change:``appintegrations``: Documentation update for AppIntegrations Service
* api-change:``chime``: This SDK release adds Account Status as one of the attributes in Account API response
* api-change:``auditmanager``: This release relaxes the S3 URL character restrictions in AWS Audit Manager. Regex patterns have been updated for the following attributes: s3RelativePath, destination, and s3ResourcePath. 'AWS' terms have also been replaced with entities to align with China Rebrand documentation efforts.


1.20.0
======

* feature:Python: Drop support for Python 2.7
* api-change:``lex-models``: Lex now supports the en-IN locale
* api-change:``ec2``: This feature enables customers  to specify weekly recurring time window(s) for scheduled events that reboot, stop or terminate EC2 instances.
* api-change:``cognito-idp``: Documentation updates for cognito-idp
* api-change:``ecs``: Documentation updates for support of awsvpc mode on Windows.
* api-change:``iotsitewise``: Update the default endpoint for the APIs used to manage asset models, assets, gateways, tags, and account configurations. If you have firewalls with strict egress rules, configure the rules to grant you access to api.iotsitewise.[region].amazonaws.com or api.iotsitewise.[cn-region].amazonaws.com.cn.


1.19.112
========

* api-change:``dms``: Release of feature needed for ECA-Endpoint settings. This allows customer to delete a field in endpoint settings by using --exact-settings flag in modify-endpoint api. This also displays default values for certain required fields of endpoint settings in describe-endpoint-settings api.
* api-change:``wellarchitected``: This update provides support for Well-Architected API users to mark answer choices as not applicable.
* api-change:``healthlake``: General availability for Amazon HealthLake. StartFHIRImportJob and StartFHIRExportJob APIs now require AWS KMS parameter. For more information, see the Amazon HealthLake Documentation https://docs.aws.amazon.com/healthlake/index.html.
* api-change:``acm``: Added support for RSA 3072 SSL certificate import
* api-change:``glue``: Add support for Event Driven Workflows
* api-change:``lightsail``: This release adds support for the Amazon Lightsail object storage service, which allows you to create buckets and store objects.


1.19.111
========

* api-change:``amplifybackend``: Added Sign in with Apple OAuth provider.
* api-change:``ssm``: Changes to OpsCenter APIs to support a new feature, operational insights.
* api-change:``directconnect``: This release adds a new filed named awsLogicalDeviceId that it displays the AWS Direct Connect endpoint which terminates a physical connection's BGP Sessions.
* api-change:``lex-models``: Customers can now migrate bots built with Lex V1 APIs to V2 APIs. This release adds APIs to initiate and manage the migration of a bot.
* api-change:``redshift``: Release new APIs to support new Redshift feature - Authentication Profile
* api-change:``pricing``: Documentation updates for api.pricing


1.19.110
========

* api-change:``kendra``: Amazon Kendra now supports Principal Store
* api-change:``eks``: Documentation updates for Wesley to support the parallel node upgrade feature.


1.19.109
========

* api-change:``mediaconvert``: MediaConvert now supports color, style and position information passthrough from 608 and Teletext to SRT and WebVTT subtitles. MediaConvert now also supports Automatic QVBR quality levels for QVBR RateControlMode.
* api-change:``frauddetector``: This release adds support for ML Explainability to display model variable importance value in Amazon Fraud Detector.
* api-change:``sagemaker``: Releasing new APIs related to Tuning steps in model building pipelines.


1.19.108
========

* api-change:``eks``: Added waiters for EKS FargateProfiles.
* api-change:``devops-guru``: Add AnomalyReportedTimeRange field to include open and close time of anomalies.
* api-change:``ssm-contacts``: Updated description for CreateContactChannel contactId.
* api-change:``mediatailor``: Add ListAlerts for Channel, Program, Source Location, and VOD Source to return alerts for resources.
* api-change:``fms``: AWS Firewall Manager now supports route table monitoring, and provides remediation action recommendations to security administrators for AWS Network Firewall policies with misconfigured routes.
* api-change:``outposts``: Added property filters for listOutposts


1.19.107
========

* api-change:``cloudfront``: Amazon CloudFront now provides two new APIs, ListConflictingAliases and AssociateAlias, that help locate and move Alternate Domain Names (CNAMEs) if you encounter the CNAMEAlreadyExists error code.
* api-change:``storagegateway``: Adding support for oplocks for SMB file shares,  S3 Access Point and S3 Private Link for all file shares and IP address support for file system associations
* api-change:``mq``: adds support for modifying the maintenance window for brokers.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``chime``: Releasing new APIs for AWS Chime MediaCapturePipeline
* api-change:``iotsitewise``: This release add storage configuration APIs for AWS IoT SiteWise.
* api-change:``ec2``: This release adds resource ids and tagging support for VPC security group rules.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).


1.19.106
========

* api-change:``sns``: Documentation updates for Amazon SNS.
* api-change:``eks``: Adding new error code UnsupportedAddonModification for Addons in EKS
* api-change:``macie2``: Sensitive data findings in Amazon Macie now include enhanced location data for JSON and JSON Lines files
* api-change:``lambda``: Added support for AmazonMQRabbitMQ as an event source. Added support for VIRTUAL_HOST as SourceAccessType for streams event source mappings.
* api-change:``imagebuilder``: Adds support for specifying parameters to customize components for recipes. Expands configuration of the Amazon EC2 instances that are used for building and testing images, including the ability to specify commands to run on launch, and more control over installation and removal of the SSM agent.
* api-change:``mgn``: Bug fix: Remove not supported EBS encryption type "NONE"


1.19.105
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ec2``: This release removes network-insights-boundary


1.19.104
========

* api-change:``ec2``: Adding a new reserved field to support future infrastructure improvements for Amazon EC2 Fleet.
* api-change:``sagemaker``: SageMaker model registry now supports up to 5 containers and associated environment variables.
* api-change:``sqs``: Documentation updates for Amazon SQS.


1.19.103
========

* api-change:``servicediscovery``: AWS Cloud Map now allows configuring the TTL of the SOA record for a hosted zone to control the negative caching for new services.
* api-change:``kendra``: Amazon Kendra Enterprise Edition now offered in smaller more granular units to enable customers with smaller workloads. Virtual Storage Capacity units now offer scaling in increments of 100,000 documents (up to 30GB) per unit and Virtual Query Units offer scaling increments of 8,000 queries per day.
* api-change:``ssm-contacts``: Fixes the tag key length range to 128 chars,  tag value length to 256 chars; Adds support for UTF-8 chars for contact and channel names, Allows users to unset name in UpdateContact API; Adds throttling exception to StopEngagement API, validation exception to APIs UntagResource, ListTagsForResource
* api-change:``databrew``: Adds support for the output of job results to the AWS Glue Data Catalog.
* api-change:``mediapackage-vod``: Add support for Widevine DRM on CMAF packaging configurations. Both Widevine and FairPlay DRMs can now be used simultaneously, with CBCS encryption.
* api-change:``autoscaling``: Amazon EC2 Auto Scaling infrastructure improvements and optimizations.


1.19.102
========

* api-change:``redshift``: Added InvalidClusterStateFault to the DisableLogging API, thrown when calling the API on a non available cluster.
* api-change:``glue``: Add JSON Support for Glue Schema Registry
* api-change:``sagemaker``: Sagemaker Neo now supports running compilation jobs using customer's Amazon VPC
* api-change:``mediaconvert``: MediaConvert adds support for HDR10+, ProRes 4444,  and XAVC outputs, ADM/DAMF support for Dolby Atmos ingest, and alternative audio and WebVTT caption ingest via HLS inputs. MediaConvert also now supports creating trickplay outputs for Roku devices for HLS, CMAF, and DASH output groups.


1.19.101
========

* api-change:``snowball``: AWS Snow Family customers can remotely monitor and operate their connected AWS Snowcone devices. AWS Snowball Edge Storage Optimized customers can now import and export their data using NFS.
* api-change:``proton``: Added waiters for template registration, service operations, and environment deployments.
* api-change:``amplifybackend``: Imports an existing backend authentication resource.


1.19.100
========

* api-change:``dax``: Add support for encryption in transit to DAX clusters.
* api-change:``transfer``: Customers can successfully use legacy clients with Transfer Family endpoints enabled for FTPS and FTP behind routers, firewalls, and load balancers by providing a Custom IP address used for data channel communication.
* api-change:``wafv2``: Added support for 15 new text transformation.
* api-change:``connect``: Released Amazon Connect quick connects management API for general availability (GA). For more information, see https://docs.aws.amazon.com/connect/latest/APIReference/Welcome.html
* api-change:``cloud9``: Minor update to AWS Cloud9 documentation to allow correct parsing of outputted text
* api-change:``chime``: Adds EventIngestionUrl field to MediaPlacement
* api-change:``codebuild``: BucketOwnerAccess is currently not supported
* api-change:``securityhub``: Added new resource details for ECS clusters and ECS task definitions. Added additional information for S3 buckets, Elasticsearch domains, and API Gateway V2 stages.
* api-change:``kendra``: Amazon Kendra now supports SharePoint 2013 and SharePoint 2016 when using a SharePoint data source.


1.19.99
=======

* api-change:``codeguru-reviewer``: Adds support for S3 based full repository analysis and changed lines scan.
* api-change:``events``: Added the following parameters to ECS targets: CapacityProviderStrategy, EnableECSManagedTags, EnableExecuteCommand, PlacementConstraints, PlacementStrategy, PropagateTags, ReferenceId, and Tags
* api-change:``cloudsearch``: This release replaces previous generation CloudSearch instances with equivalent new instances that provide better stability at the same price.
* api-change:``license-manager``: AWS License Manager now allows license administrators and end users to communicate to each other by setting custom status reasons when updating the status on a granted license.
* api-change:``cloud9``: Updated documentation for CreateEnvironmentEC2 to explain that because Amazon Linux AMI has ended standard support as of December 31, 2020, we recommend you choose Amazon Linux 2--which includes long term support through 2023--for new AWS Cloud9 environments.
* api-change:``docdb``: DocumentDB documentation-only edits
* api-change:``mediatailor``: Update GetChannelSchedule to return information on ad breaks.
* api-change:``quicksight``: Releasing new APIs for AWS QuickSight Folders
* api-change:``cloudfront``: Amazon CloudFront adds support for a new security policy, TLSv1.2_2021.
* api-change:``ec2``: This release adds support for provisioning your own IP (BYOIP) range in multiple regions. This feature is in limited Preview for this release. Contact your account manager if you are interested in this feature.


1.19.98
=======

* api-change:``cloudformation``: CloudFormation registry service now supports 3rd party public type sharing


1.19.97
=======

* api-change:``chime``: This release adds a new API UpdateSipMediaApplicationCall, to update an in-progress call for SipMediaApplication.
* api-change:``sagemaker``: Enable ml.g4dn instance types for SageMaker Batch Transform and SageMaker Processing
* api-change:``kendra``: Amazon Kendra now supports the indexing of web documents for search through the web crawler.
* api-change:``rds``: This release enables Database Activity Streams for RDS Oracle


1.19.96
=======

* api-change:``ec2``: This release adds support for VLAN-tagged network traffic over an Elastic Network Interface (ENI). This feature is in limited Preview for this release. Contact your account manager if you are interested in this feature.
* api-change:``kms``: Adds support for multi-Region keys
* api-change:``mediatailor``: Adds AWS Secrets Manager Access Token Authentication for Source Locations
* api-change:``rds``: This release enables fast cloning in Aurora Serverless. You can now clone between Aurora Serverless clusters and Aurora Provisioned clusters.


1.19.95
=======

* api-change:``ec2``: EC2 M5n, M5dn, R5n, R5dn metal instances with 100 Gbps network performance and Elastic Fabric Adapter (EFA) for ultra low latency
* api-change:``redshift-data``: Redshift Data API service now supports SQL parameterization.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``connect``: This release adds new sets of APIs: AssociateBot, DisassociateBot, and ListBots. You can use it to programmatically add an Amazon Lex bot or Amazon Lex V2 bot on the specified Amazon Connect instance
* api-change:``lexv2-models``: Update lexv2-models command to latest version


1.19.94
=======

* api-change:``greengrassv2``: We have verified the APIs being released here and are ready to release
* api-change:``lookoutmetrics``: Added "LEARNING" status for anomaly detector and updated description for "Offset" parameter in MetricSet APIs.
* api-change:``iotanalytics``: Adds support for data store partitions.


1.19.93
=======

* api-change:``ec2``: Amazon EC2 adds new AMI property to flag outdated AMIs
* api-change:``medialive``: AWS MediaLive now supports OCR-based conversion of DVB-Sub and SCTE-27 image-based source captions to WebVTT, and supports ingest of ad avail decorations in HLS input manifests.
* api-change:``mediaconnect``: When you enable source failover, you can now designate one of two sources as the primary source. You can choose between two failover modes to prevent any disruption to the video stream. Merge combines the sources into a single stream. Failover allows switching between a primary and a backup stream.


1.19.92
=======

* api-change:``sagemaker-featurestore-runtime``: Release BatchGetRecord API for AWS SageMaker Feature Store Runtime.
* api-change:``appmesh``: AppMesh now supports additional routing capabilities in match and rewrites for Gateway Routes and Routes. Additionally, App Mesh also supports specifying DNS Response Types in Virtual Nodes.
* api-change:``redshift``: Added InvalidClusterStateFault to the ModifyAquaConfiguration API, thrown when calling the API on a non available cluster.
* api-change:``appflow``: Adding MAP_ALL task type support.
* api-change:``chime``: This SDK release adds support for UpdateAccount API to allow users to update their default license on Chime account.
* api-change:``managedblockchain``: This release supports KMS customer-managed Customer Master Keys (CMKs) on member-specific Hyperledger Fabric resources.
* api-change:``ec2``: This release adds a new optional parameter connectivityType (public, private) for the CreateNatGateway API. Private NatGateway does not require customers to attach an InternetGateway to the VPC and can be used for communication with other VPCs and on-premise networks.
* api-change:``ram``: AWS Resource Access Manager (RAM) is releasing new field isResourceTypeDefault in ListPermissions and GetPermission response, and adding permissionArn parameter to GetResourceShare request to filter by permission attached
* api-change:``cognito-idp``: Amazon Cognito now supports targeted sign out through refresh token revocation
* api-change:``sagemaker``: Using SageMaker Edge Manager with AWS IoT Greengrass v2 simplifies accessing, maintaining, and deploying models to your devices. You can now create deployable IoT Greengrass components during edge packaging jobs. You can choose to create a device fleet with or without creating an AWS IoT role alias.


1.19.91
=======

* api-change:``proton``: This is the initial SDK release for AWS Proton
* api-change:``transfer``: Documentation updates for the AWS Transfer Family service.
* api-change:``personalize-events``: Support for unstructured text inputs in the items dataset to to automatically extract key information from product/content description as an input when creating solution versions.
* api-change:``kendra``: AWS Kendra now supports checking document status.


1.19.90
=======

* api-change:``cognito-idp``: Documentation updates for cognito-idp
* api-change:``macie2``: This release of the Amazon Macie API introduces stricter validation of S3 object criteria for classification jobs.
* api-change:``fsx``: This release adds support for auditing end-user access to files, folders, and file shares using Windows event logs, enabling customers to meet their security and compliance needs.
* api-change:``servicecatalog``: increase max pagesize for List/Search apis


1.19.89
=======

* api-change:``eks``: Added updateConfig option that allows customers to control upgrade velocity in Managed Node Group.
* api-change:``sagemaker``: AWS SageMaker - Releasing new APIs related to Callback steps in model building pipelines. Adds experiment integration to model building pipelines.
* api-change:``glue``: Add SampleSize variable to S3Target to enable s3-sampling feature through API.
* api-change:``personalize``: Update regex validation in kmsKeyArn and s3 path API parameters for AWS Personalize APIs


1.19.88
=======

* api-change:``medialive``: Add support for automatically setting the H.264 adaptive quantization and GOP B-frame fields.
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling
* api-change:``qldb``: Documentation updates for Amazon QLDB
* api-change:``rds``: Documentation updates for RDS: fixing an outdated link to the RDS documentation in DBInstance$DBInstanceStatus
* api-change:``pi``: The new GetDimensionKeyDetails action retrieves the attributes of the specified dimension group for a DB instance or data source.
* api-change:``cloudtrail``: AWS CloudTrail supports data events on new service resources, including Amazon DynamoDB tables and S3 Object Lambda access points.


1.19.87
=======

* api-change:``ssm``: Documentation updates for ssm to fix customer reported issue
* api-change:``forecast``: Added optional field AutoMLOverrideStrategy to CreatePredictor API that allows users to customize AutoML strategy. If provided in CreatePredictor request, this field is visible in DescribePredictor and GetAccuracyMetrics responses.
* api-change:``route53resolver``: Documentation updates for Route 53 Resolver
* api-change:``s3``: S3 Inventory now supports Bucket Key Status
* api-change:``s3control``: Amazon S3 Batch Operations now supports S3 Bucket Keys.


1.19.86
=======

* api-change:``docdb``: This SDK release adds support for DocDB global clusters.
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``ecs``: Documentation updates for Amazon ECS.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``braket``: Introduction of a RETIRED status for devices.
* api-change:``autoscaling``: You can now launch EC2 instances with GP3 volumes when using Auto Scaling groups with Launch Configurations


1.19.85
=======

* api-change:``servicediscovery``: Bugfixes - The DiscoverInstances API operation now provides an option to return all instances for health-checked services when there are no healthy instances available.
* api-change:``polly``: Amazon Polly adds new Canadian French voice - Gabrielle. Gabrielle is available as Neural voice only.
* api-change:``ec2``: Added idempotency to CreateNetworkInterface using the ClientToken parameter.
* api-change:``sns``: This release adds SMS sandbox in Amazon SNS and the ability to view all configured origination numbers. The SMS sandbox provides a safe environment for sending SMS messages, without risking your reputation as an SMS sender.
* api-change:``iotwireless``: Added six new public customer logging APIs to allow customers to set/get/reset log levels at resource type and resource id level. The log level set from the APIs will be used to filter log messages that can be emitted to CloudWatch in customer accounts.


1.19.84
=======

* api-change:``datasync``: Added SecurityDescriptorCopyFlags option that allows for control of which components of SMB security descriptors are copied from source to destination objects.
* api-change:``lookoutmetrics``: Allowing dot(.) character in table name for RDS and Redshift as source connector.
* api-change:``location``: Adds support for calculation of routes, resource tagging and customer provided KMS keys.


1.19.83
=======

* api-change:``iotsitewise``: IoT SiteWise Monitor Portal API updates to add alarms feature configuration.
* api-change:``devicefarm``: Introduces support for using our desktop testing service with applications hosted within your Virtual Private Cloud (VPC).
* api-change:``iotevents-data``: Releasing new APIs for AWS IoT Events Alarms
* api-change:``fsx``: This release adds LZ4 data compression support to FSx for Lustre to reduce storage consumption of both file system storage and file system backups.
* api-change:``iotevents``: Releasing new APIs for AWS IoT Events Alarms
* api-change:``resource-groups``: Documentation updates for Resource Groups.
* api-change:``sqs``: Documentation updates for Amazon SQS for General Availability of high throughput for FIFO queues.
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``kendra``: Amazon Kendra now suggests popular queries in order to help guide query typing and help overall accuracy.


1.19.82
=======

* api-change:``ec2``: This release removes resource ids and tagging support for VPC security group rules.


1.19.81
=======

* api-change:``acm-pca``: This release enables customers to store CRLs in S3 buckets with Block Public Access enabled. The release adds the S3ObjectAcl parameter to the CreateCertificateAuthority and UpdateCertificateAuthority APIs to allow customers to choose whether their CRL will be publicly available.
* api-change:``cloudfront``: Documentation fix for CloudFront
* api-change:``qldb``: Support STANDARD permissions mode in CreateLedger and DescribeLedger. Add UpdateLedgerPermissionsMode to update permissions mode on existing ledgers.
* api-change:``ec2``: This release adds resource ids and tagging support for VPC security group rules.
* api-change:``outposts``: Add ConflictException to DeleteOutpost, CreateOutpost
* api-change:``ecs``: The release adds support for registering External instances to your Amazon ECS clusters.
* api-change:``mwaa``: Adds scheduler count selection for Environments using Airflow version 2.0.2 or later.


1.19.80
=======

* api-change:``workspaces``: Adds support for Linux device types in WorkspaceAccessProperties
* api-change:``iot``: This release includes support for a new feature: Job templates for AWS IoT Device Management Jobs. The release includes job templates as a new resource and APIs for managing job templates.
* api-change:``transfer``: AWS Transfer Family customers can now use AWS Managed Active Directory or AD Connector to authenticate their end users, enabling seamless migration of file transfer workflows that rely on AD authentication, without changing end users' credentials or needing a custom authorizer.


1.19.79
=======

* api-change:``logs``: This release provides dimensions and unit support for metric filters.
* api-change:``quicksight``: Add new parameters on RegisterUser and UpdateUser APIs to assign or update external ID associated to QuickSight users federated through web identity.
* api-change:``ce``: Introduced FindingReasonCodes, PlatformDifferences, DiskResourceUtilization and NetworkResourceUtilization to GetRightsizingRecommendation action
* api-change:``compute-optimizer``: Adds support for 1) additional instance types, 2) additional instance metrics, 3) finding reasons for instance recommendations, and 4) platform differences between a current instance and a recommended instance type.
* api-change:``ec2``: This release adds support for creating and managing EC2 On-Demand Capacity Reservations on Outposts.


1.19.78
=======

* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``opsworkscm``: New PUPPET_API_CRL attribute returned by DescribeServers API; new EngineVersion of 2019 available for Puppet Enterprise servers.
* api-change:``forecast``: Updated attribute statistics in DescribeDatasetImportJob response to support Long values
* api-change:``efs``: Update efs command to latest version


1.19.77
=======

* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``personalize``: Added new API to stop a solution version creation that is pending or in progress for Amazon Personalize
* api-change:``quicksight``: Add ARN based Row Level Security support to CreateDataSet/UpdateDataSet APIs.


1.19.76
=======

* api-change:``iam``: Add pagination to ListUserTags operation
* api-change:``eks``: Update the EKS AddonActive waiter.
* api-change:``autoscaling``: With this release, customers can easily use Predictive Scaling as a policy directly through Amazon EC2 Auto Scaling configurations to proactively scale their applications ahead of predicted demand.
* api-change:``kinesisanalyticsv2``: Kinesis Data Analytics now allows rapid iteration on Apache Flink stream processing through the Kinesis Data Analytics Studio feature.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``rekognition``: Amazon Rekognition Custom Labels adds support for customer managed encryption, using AWS Key Management Service, of image files copied into the service and files written back to the customer.


1.19.75
=======

* api-change:``license-manager``: AWS License Manager now supports periodic report generation.
* api-change:``personalize``: Amazon Personalize now supports the ability to optimize a solution for a custom objective in addition to maximizing relevance.
* api-change:``iotsitewise``: Documentation updates for AWS IoT SiteWise.
* api-change:``apprunner``: AWS App Runner is a service that provides a fast, simple, and cost-effective way to deploy from source code or a container image directly to a scalable and secure web application in the AWS Cloud.
* api-change:``compute-optimizer``: This release enables compute optimizer to support exporting  recommendations to Amazon S3 for EBS volumes and Lambda Functions.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``support``: Documentation updates for support


1.19.74
=======

* api-change:``neptune``: Neptune support for CopyTagsToSnapshots
* api-change:``iotdeviceadvisor``: AWS IoT Core Device Advisor is fully managed test capability for IoT devices. Device manufacturers can use Device Advisor to test their IoT devices for reliable and secure connectivity with AWS IoT.
* api-change:``sagemaker-a2i-runtime``: Documentation updates for Amazon A2I Runtime model
* api-change:``mediaconnect``: MediaConnect now supports JPEG XS for AWS Cloud Digital Interface (AWS CDI) uncompressed workflows, allowing you to establish a bridge between your on-premises live video network and the AWS Cloud.
* api-change:``elasticache``: Documentation updates for elasticache
* api-change:``applicationcostprofiler``: APIs for AWS Application Cost Profiler.


1.19.73
=======

* api-change:``imagebuilder``: Text-only updates for bundled documentation feedback tickets - spring 2021.
* api-change:``macie2``: This release of the Amazon Macie API adds support for defining run-time, S3 bucket criteria for classification jobs. It also adds resources for querying data about AWS resources that Macie monitors.
* api-change:``securityhub``: Updated descriptions to add notes on array lengths.
* api-change:``es``: Adds support for cold storage.
* api-change:``events``: Update InputTransformer variable limit from 10 to 100 variables.
* api-change:``transcribe``: Transcribe Medical now supports identification of PHI entities within transcripts
* api-change:``detective``: Updated descriptions of array parameters to add the restrictions on the array and value lengths.


1.19.72
=======

* api-change:``ec2``: High Memory virtual instances are powered by Intel Sky Lake CPUs and offer up to 12TB of memory.


1.19.71
=======

* api-change:``s3control``: Documentation updates for Amazon S3-control
* api-change:``ssm-contacts``: AWS Systems Manager Incident Manager enables faster resolution of critical application availability and performance issues, management of contacts and post incident analysis
* api-change:``ssm-incidents``: AWS Systems Manager Incident Manager enables faster resolution of critical application availability and performance issues, management of contacts and post-incident analysis


1.19.70
=======

* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for Kantar SNAP File Audio Watermarking with a Kantar Watermarking account, and Display Definition Segment(DDS) segment data controls for DVB-Sub caption outputs.
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``kinesisanalyticsv2``: Amazon Kinesis Analytics now supports ListApplicationVersions and DescribeApplicationVersion API for Apache Flink applications
* api-change:``eks``: This release updates create-nodegroup and update-nodegroup-config APIs for adding/updating taints on managed nodegroups.
* api-change:``iotwireless``: Add three new optional fields to support filtering and configurable sub-band in WirelessGateway APIs. The filtering is for all the RF region supported. The sub-band configuration is only applicable to LoRa gateways of US915 or AU915 RF region.
* api-change:``config``: Adds paginator to multiple APIs: By default, the paginator allows user to iterate over the results and allows the CLI to return up to 1000 results.
* api-change:``ssm``: This release adds new APIs to associate, disassociate and list related items in SSM OpsCenter; and this release adds DisplayName as a version-level attribute for SSM Documents and introduces two new document types: ProblemAnalysis, ProblemAnalysisTemplate.
* api-change:``ecs``: This release contains updates for Amazon ECS.


1.19.69
=======

* api-change:``lakeformation``: This release adds Tag Based Access Control to AWS Lake Formation service
* api-change:``connect``: Adds tagging support for Connect APIs CreateIntegrationAssociation and CreateUseCase.
* api-change:``lookoutmetrics``: Enforcing UUID style for parameters that are already in UUID format today. Documentation specifying eventual consistency of lookoutmetrics resources.


1.19.68
=======

* api-change:``snowball``: AWS Snow Family adds APIs for ordering and managing Snow jobs with long term pricing
* api-change:``servicediscovery``: Bugfix: Improved input validation for RegisterInstance action, InstanceId field
* api-change:``ssm``: SSM feature release - ChangeCalendar integration with StateManager.
* api-change:``kafka``: IAM Access Control for Amazon MSK enables you to create clusters that use IAM to authenticate clients and to allow or deny Apache Kafka actions for those clients.


1.19.67
=======

* api-change:``kinesisanalyticsv2``: Amazon Kinesis Analytics now supports RollbackApplication for Apache Flink applications to revert the application to the previous running version
* api-change:``sagemaker``: Amazon SageMaker Autopilot now provides the ability to automatically deploy the best model to an endpoint
* api-change:``auditmanager``: This release updates the CreateAssessmentFrameworkControlSet and UpdateAssessmentFrameworkControlSet API data types. For both of these data types, the control set name is now a required attribute.
* api-change:``nimble``: Documentation Updates for Amazon Nimble Studio.


1.19.66
=======

* api-change:``finspace-data``: Documentation updates for FinSpaceData API.
* api-change:``finspace``: Documentation updates for FinSpace API.


1.19.65
=======

* api-change:``health``: Documentation updates for health
* api-change:``devops-guru``: Added GetCostEstimation and StartCostEstimation to get the monthly resource usage cost and added ability to view resource health by AWS service name and to search insights be AWS service name.
* api-change:``chime``: This release adds the ability to search for and order international phone numbers for Amazon Chime SIP media applications.
* api-change:``acm-pca``: This release adds the KeyStorageSecurityStandard parameter to the CreateCertificateAuthority API to allow customers to mandate a security standard to which the CA key will be stored within.
* api-change:``sagemaker``: Enable retrying Training and Tuning Jobs that fail with InternalServerError by setting RetryStrategy.


1.19.64
=======

* api-change:``finspace-data``: Update FinSpace Data serviceAbbreviation


1.19.63
=======

* api-change:``securityhub``: Updated ASFF to add the following new resource details objects: AwsEc2NetworkAcl, AwsEc2Subnet, and AwsElasticBeanstalkEnvironment.
* api-change:``finspace``: This is the initial SDK release for the management APIs for Amazon FinSpace. Amazon FinSpace is a data management and analytics service for the financial services industry (FSI).
* api-change:``mturk``: Update mturk command to latest version
* api-change:``finspace-data``: This is the initial SDK release for the data APIs for Amazon FinSpace. Amazon FinSpace is a data management and analytics application for the financial services industry (FSI).
* api-change:``chime``: Added new BatchCreateChannelMembership API to support multiple membership creation for channels


1.19.62
=======

* api-change:``customer-profiles``: This release introduces GetMatches and MergeProfiles APIs to fetch and merge duplicate profiles
* api-change:``cloudfront``: CloudFront now supports CloudFront Functions, a native feature of CloudFront that enables you to write lightweight functions in JavaScript for high-scale, latency-sensitive CDN customizations.
* api-change:``personalize``: Update URL for dataset export job documentation.
* api-change:``forecast``: Added new DeleteResourceTree operation that helps in deleting all the child resources of a given resource including the given resource.
* api-change:``robomaker``: Adds ROS2 Foxy as a supported Robot Software Suite Version and Gazebo 11 as a supported Simulation Software Suite Version
* api-change:``marketplace-catalog``: Allows user defined names for Changes in a ChangeSet. Users can use ChangeNames to reference properties in another Change within a ChangeSet. This feature allows users to make changes to an entity when the entity identifier is not yet available while constructing the StartChangeSet request.


1.19.61
=======

* enhancement:arguments: Remove redundant '-' from two character pluralized acronyms in argument names
* api-change:``macie2``: The Amazon Macie API now provides S3 bucket metadata that indicates whether a bucket policy requires server-side encryption of objects when objects are uploaded to the bucket.
* api-change:``ecs``: Add support for EphemeralStorage on TaskDefinition and TaskOverride
* api-change:``chime``: Increase AppInstanceUserId length to 64 characters
* api-change:``organizations``: Minor text updates for AWS Organizations API Reference
* bugfix:``configure``: Fix `list` command to show correct profile location when AWS_DEFAULT_PROFILE set, fixes `#6119 <https://github.com/aws/aws-cli/issues/6119>`__


1.19.60
=======

* api-change:``iotsitewise``: AWS IoT SiteWise interpolation API will get interpolated values for an asset property per specified time interval during a period of time.
* api-change:``connect``: Updated max number of tags that can be attached from 200 to 50. MaxContacts is now an optional parameter for the UpdateQueueMaxContact API.
* api-change:``mediapackage-vod``: MediaPackage now offers the option to place your Sequence Parameter Set (SPS), Picture Parameter Set (PPS), and Video Parameter Set (VPS) encoder metadata in every video segment instead of in the init fragment for DASH and CMAF endpoints.
* api-change:``cloudformation``: Add CallAs parameter to GetTemplateSummary to enable use with StackSets delegated administrator integration
* api-change:``nimble``: Amazon Nimble Studio is a virtual studio service that empowers visual effects, animation, and interactive content teams to create content securely within a scalable, private cloud service.


1.19.59
=======

* api-change:``auditmanager``: This release restricts using backslashes in control, assessment, and framework names. The controlSetName field of the UpdateAssessmentFrameworkControlSet API now allows strings without backslashes.


1.19.58
=======

* api-change:``kinesisanalyticsv2``: Amazon Kinesis Data Analytics now supports custom application maintenance configuration using UpdateApplicationMaintenanceConfiguration API for Apache Flink applications. Customers will have visibility when their application is under maintenance status using 'MAINTENANCE' application status.
* api-change:``personalize``: Added support for exporting data imported into an Amazon Personalize dataset to a specified data source (Amazon S3 bucket).
* api-change:``codeguru-reviewer``: Include KMS Key Details in Repository Association APIs to enable usage of customer managed KMS Keys.
* api-change:``mediaconvert``: Documentation updates for mediaconvert
* api-change:``iotwireless``: Add a new optional field MessageType to support Sidewalk devices in SendDataToWirelessDevice API
* api-change:``glue``: Adding Kafka Client Auth Related Parameters
* api-change:``eks``: This release updates existing Amazon EKS input validation so customers will see an InvalidParameterException instead of a ParamValidationError when they enter 0 for minSize and/or desiredSize. It also adds LaunchTemplate information to update responses and a new "CUSTOM" value for AMIType.
* api-change:``ec2``: Adding support for Red Hat Enterprise Linux with HA for Reserved Instances.


1.19.57
=======

* api-change:``sns``: Amazon SNS adds two new attributes, TemplateId and EntityId, for using sender IDs to send SMS messages to destinations in India.
* api-change:``mediapackage``: Add support for Widevine DRM on CMAF origin endpoints. Both Widevine and FairPlay DRMs can now be used simultaneously, with CBCS encryption.


1.19.56
=======

* api-change:``forecast``: This release adds EstimatedTimeRemaining minutes field to the DescribeDatasetImportJob, DescribePredictor, DescribeForecast API response which denotes the time remaining to complete the job IN_PROGRESS.
* api-change:``cognito-idp``: Documentation updates for cognito-idp
* api-change:``elasticache``: This release introduces log delivery of Redis slow log from Amazon ElastiCache.
* api-change:``securityhub``: Replaced the term "master" with "administrator". Added new actions to replace AcceptInvitation, GetMasterAccount, and DisassociateFromMasterAccount. In Member, replaced MasterId with AdministratorId.


1.19.55
=======

* api-change:``detective``: Added parameters to track the data volume in bytes for a member account. Deprecated the existing parameters that tracked the volume as a percentage of the allowed volume for a behavior graph. Changes reflected in MemberDetails object.
* api-change:``groundstation``: Support new S3 Recording Config allowing customers to write downlink data directly to S3.
* api-change:``cloudformation``: Added support for creating and updating stack sets with self-managed permissions from templates that reference macros.
* api-change:``redshift``: Add operations: AddPartner, DescribePartners, DeletePartner, and UpdatePartnerStatus to support tracking integration status with data partners.
* api-change:``kendra``: Amazon Kendra now enables users to override index-level boosting configurations for each query.


1.19.54
=======

* api-change:``ce``: Adding support for Sagemaker savings plans in GetSavingsPlansPurchaseRecommendation API
* api-change:``savingsplans``: Added support for Amazon SageMaker in Machine Learning Savings Plans


1.19.53
=======

* api-change:``dms``: AWS DMS added support of TLS for Kafka endpoint. Added Describe endpoint setting API for DMS endpoints.
* api-change:``sts``: STS now supports assume role with Web Identity using JWT token length upto 20000 characters


1.19.52
=======

* api-change:``config``: Add exception for DeleteRemediationConfiguration and DescribeRemediationExecutionStatus
* api-change:``mediaconnect``: For flows that use Listener protocols, you can now easily locate an output's outbound IP address for a private internet. Additionally, MediaConnect now supports the Waiters feature that makes it easier to poll for the status of a flow until it reaches its desired state.
* api-change:``codestar-connections``: This release adds tagging support for CodeStar Connections Host resources
* api-change:``route53``: Documentation updates for route53


1.19.51
=======

* api-change:``sts``: This release adds the SourceIdentity parameter that can be set when assuming a role.
* api-change:``redshift``: Added support to enable AQUA in Amazon Redshift clusters.
* api-change:``comprehendmedical``: The InferICD10CM API now returns TIME_EXPRESSION entities that refer to medical conditions.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``rds``: Clarify that enabling or disabling automated backups causes a brief downtime, not an outage.


1.19.50
=======

* api-change:``fsx``: Support for cross-region and cross-account backup copies
* api-change:``codebuild``: AWS CodeBuild now allows you to set the access permissions for build artifacts, project artifacts, and log files that are uploaded to an Amazon S3 bucket that is owned by another account.


1.19.49
=======

* api-change:``redshift``: Add support for case sensitive table level restore
* api-change:``ec2``: Add paginator support to DescribeStoreImageTasks and update documentation.
* api-change:``shield``: CreateProtection now throws InvalidParameterException instead of InternalErrorException when system tags (tag with keys prefixed with "aws:") are passed in.


1.19.48
=======

* api-change:``autoscaling``: Amazon EC2 Auto Scaling announces Warm Pools that help applications to scale out faster by pre-initializing EC2 instances and save money by requiring fewer continuously running instances
* api-change:``appstream``: This release provides support for image updates
* api-change:``kinesis-video-archived-media``: Documentation updates for archived.kinesisvideo
* api-change:``robomaker``: This release allows RoboMaker customers to specify custom tools to run with their simulation job
* api-change:``lookoutequipment``: This release introduces support for Amazon Lookout for Equipment.
* api-change:``ram``: Documentation updates for AWS RAM resource sharing
* api-change:``customer-profiles``: Documentation updates for Put-Integration API


1.19.47
=======

* api-change:``accessanalyzer``: IAM Access Analyzer now analyzes your CloudTrail events to identify actions and services that have been used by an IAM entity (user or role) and generates an IAM policy that is based on that activity.
* api-change:``elasticache``: This release adds tagging support for all AWS ElastiCache resources except Global Replication Groups.
* api-change:``ivs``: This release adds support for the Auto-Record to S3 feature. Amazon IVS now enables you to save your live video to Amazon S3.
* bugfix:``profile``: Fix bug in profile resolution order when AWS_PROFILE environment variable contains non-existing profile but `--profile` command line argument contains correct profile name
* api-change:``mgn``: Add new service - Application Migration Service.
* api-change:``storagegateway``: File Gateway APIs now support FSx for Windows as a cloud storage.


1.19.46
=======

* api-change:``medialive``: MediaLive VPC outputs update to include Availability Zones, Security groups, Elastic Network Interfaces, and Subnet Ids in channel response
* api-change:``ssm``: Supports removing a label or labels from a parameter, enables ScheduledEndTime and ChangeDetails for StartChangeRequestExecution API, supports critical/security/other noncompliant count for patch API.
* api-change:``ec2``: This release adds support for storing EBS-backed AMIs in S3 and restoring them from S3 to enable cross-partition copying of AMIs
* api-change:``cloud9``: Documentation updates for Cloud9


1.19.45
=======

* api-change:``medialive``: MediaLive now support HTML5 Motion Graphics overlay
* api-change:``auditmanager``: AWS Audit Manager has updated the GetAssessment API operation to include a new response field called userRole. The userRole field indicates the role information and IAM ARN of the API caller.
* api-change:``appflow``: Added destination properties for Zendesk.


1.19.44
=======

* api-change:``imagebuilder``: This release adds support for Block Device Mappings for container image builds, and adds distribution configuration support for EC2 launch templates in AMI builds.
* api-change:``mediapackage``: SPEKE v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, based on an encryption contract selected by the customer.


1.19.43
=======

* api-change:``mediaconvert``: MediaConvert now supports HLS ingest, sidecar WebVTT ingest, Teletext color & style passthrough to TTML subtitles, TTML to WebVTT subtitle conversion with style, & DRC profiles in AC3 audio.
* api-change:``wafv2``: Added support for ScopeDownStatement for ManagedRuleGroups, Labels, LabelMatchStatement, and LoggingFilter. For more information on these features, see the AWS WAF Developer Guide.
* api-change:``lex-models``: Lex now supports the ja-JP locale
* api-change:``kendra``: AWS Kendra's ServiceNow data source now supports OAuth 2.0 authentication and knowledge article filtering via a ServiceNow query.
* api-change:``route53resolver``: Route 53 Resolver DNS Firewall is a firewall service that allows you to filter and regulate outbound DNS traffic for your VPCs.
* bugfix:Configuration: Fixed an issue when using the aws configure set command to update profiles with a space in the profile name.
* api-change:``fms``: Added Firewall Manager policy support for AWS Route 53 Resolver DNS Firewall.
* api-change:``ec2``: VPC Flow Logs Service adds a new API, GetFlowLogsIntegrationTemplate, which generates CloudFormation templates for Athena. For more info, see https://docs.aws.amazon.com/console/vpc/flow-logs/athena
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``lightsail``: - This release adds support for state detail for Amazon Lightsail container services.


1.19.42
=======

* api-change:``workmail``: This release adds support for mobile device access rules management in Amazon WorkMail.
* api-change:``machinelearning``: Minor documentation updates and link updates.
* api-change:``pricing``: Minor documentation and link updates.
* api-change:``iotwireless``: Add Sidewalk support to APIs: GetWirelessDevice, ListWirelessDevices, GetWirelessDeviceStatistics. Add Gateway connection status in GetWirelessGatewayStatistics API.
* api-change:``cloudformation``: 1. Added a new parameter RegionConcurrencyType in OperationPreferences. 2. Changed the name of AccountUrl to AccountsUrl in DeploymentTargets parameter.
* api-change:``cloud9``: Add ImageId input parameter to CreateEnvironmentEC2 endpoint. New parameter enables creation of environments with different AMIs.
* api-change:``redshift``: Enable customers to share access to their Redshift clusters from other VPCs (including VPCs from other accounts).
* api-change:``cognito-sync``: Minor documentation updates and link updates.
* api-change:``detective``: Added the ability to assign tag values to Detective behavior graphs. Tag values can be used for attribute-based access control, and for cost allocation for billing.
* api-change:``datapipeline``: Minor documentation updates and link updates.
* api-change:``comprehend``: Support for customer managed KMS encryption of Comprehend custom models
* api-change:``transcribe``: Amazon Transcribe now supports creating custom language models in the following languages: British English (en-GB), Australian English (en-AU), Indian Hindi (hi-IN), and US Spanish (es-US).
* api-change:``iot``: Added ability to prefix search on attribute value for ListThings API.
* api-change:``cloudhsm``: Minor documentation and link updates.
* api-change:``directconnect``: This release adds MACsec support to AWS Direct Connect
* api-change:``batch``: AWS Batch adds support for Amazon EFS File System


1.19.41
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``databrew``: This SDK release adds two new dataset features: 1) support for specifying a database connection as a dataset input 2) support for dynamic datasets that accept configurable parameters in S3 path.
* api-change:``sagemaker``: Amazon SageMaker Autopilot now supports 1) feature importance reports for AutoML jobs and 2) PartialFailures for AutoML jobs
* api-change:``ec2-instance-connect``: Adding support to push SSH keys to the EC2 serial console in order to allow an SSH connection to your Amazon EC2 instance's serial port.
* api-change:``ec2``: ReplaceRootVolume feature enables customers to replace the EBS root volume of a running instance to a previously known state. Add support to grant account-level access to the EC2 serial console
* api-change:``config``: Adding new APIs to support ConformancePack Compliance CI in Aggregators
* api-change:``pinpoint``: Added support for journey pause/resume, journey updatable import segment and journey quiet time wait.
* api-change:``frauddetector``: This release adds support for Batch Predictions in Amazon Fraud Detector.


1.19.40
=======

* api-change:``docdb``: This release adds support for Event Subscriptions to DocumentDB.
* api-change:``glue``: Allow Dots in Registry and Schema Names for CreateRegistry, CreateSchema; Fixed issue when duplicate keys are present and not returned as part of QuerySchemaVersionMetadata.
* api-change:``wafv2``: Added custom request handling and custom response support in rule actions and default action; Added the option to inspect the web request body as parsed and filtered JSON.
* api-change:``iam``: AWS Identity and Access Management GetAccessKeyLastUsed API will throw a custom error if customer public key is not found for access keys.
* api-change:``location``: Amazon Location added support for specifying pricing plan information on resources in alignment with our cost model.


1.19.39
=======

* api-change:``iotwireless``: Support tag-on-create for WirelessDevice.
* api-change:``customer-profiles``: This release adds an optional parameter named FlowDefinition in PutIntegrationRequest.
* api-change:``events``: Add support for SageMaker Model Builder Pipelines Targets to EventBridge
* api-change:``transcribe``: Amazon Transcribe now supports tagging words that match your vocabulary filter for batch transcription.


1.19.38
=======

* api-change:``lookoutmetrics``: Allowing uppercase alphabets for RDS and Redshift database names.


1.19.37
=======

* api-change:``medialive``: EML now supports handling HDR10 and HLG 2020 color space from a Link input.
* api-change:``lookoutmetrics``: Amazon Lookout for Metrics is now generally available. You can use Lookout for Metrics to monitor your data for anomalies. For more information, see the Amazon Lookout for Metrics Developer Guide.
* api-change:``sagemaker``: This feature allows customer to specify the environment variables in their CreateTrainingJob requests.
* api-change:``sqs``: Documentation updates for Amazon SQS
* api-change:``alexaforbusiness``: Added support for enabling and disabling data retention in the CreateProfile and UpdateProfile APIs and retrieving the state of data retention for a profile in the GetProfile API.
* api-change:``rekognition``: This release introduces AWS tagging support for Amazon Rekognition collections, stream processors, and Custom Label models.


1.19.36
=======

* api-change:``ssm``: This release allows SSM Explorer customers to enable OpsData sources across their organization when creating a resource data sync.
* api-change:``s3control``: Documentation updates for s3-control
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``ec2``: maximumEfaInterfaces added to DescribeInstanceTypes API
* api-change:``route53``: Documentation updates for route53
* api-change:``greengrass``: Updated the parameters to make name required for CreateGroup API.


1.19.35
=======

* api-change:``redshift``: Removed APIs to control AQUA on clusters.
* api-change:``ce``: You can now create cost categories with inherited value rules and specify default values for any uncategorized costs.
* api-change:``gamelift``: GameLift adds support for using event notifications to monitor game session placements. Specify an SNS topic or use CloudWatch Events to track activity for a game session queue.
* api-change:``iam``: Documentation updates for IAM operations and descriptions.
* api-change:``fis``: Updated maximum allowed size of action parameter from 64 to 1024


1.19.34
=======

* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``macie2``: This release of the Amazon Macie API adds support for publishing sensitive data findings to AWS Security Hub and specifying which categories of findings to publish to Security Hub.
* api-change:``redshift``: Added support to enable AQUA in Amazon Redshift clusters.
* api-change:``ec2``: This release adds support for UEFI boot on selected AMD- and Intel-based EC2 instances.


1.19.33
=======

* api-change:``ec2``: X2gd instances are the next generation of memory-optimized instances powered by AWS-designed, Arm-based AWS Graviton2 processors.
* api-change:``sagemaker``: Adding authentication support for pulling images stored in private Docker registries to build containers for real-time inference.


1.19.31
=======

* api-change:``autoscaling``: Amazon EC2 Auto Scaling Instance Refresh now supports phased deployments.
* api-change:``securityhub``: New object for separate provider and customer values. New objects track S3 Public Access Block configuration and identify sensitive data. BatchImportFinding requests are limited to 100 findings.
* api-change:``s3``: S3 Object Lambda is a new S3 feature that enables users to apply their own custom code to process the output of a standard S3 GET request by automatically invoking a Lambda function with a GET request
* api-change:``redshift``: Add new fields for additional information about VPC endpoint for clusters with reallocation enabled, and a new field for total storage capacity for all clusters.
* api-change:``s3control``: S3 Object Lambda is a new S3 feature that enables users to apply their own custom code to process the output of a standard S3 GET request by automatically invoking a Lambda function with a GET request


1.19.30
=======

* api-change:``batch``: Making serviceRole an optional parameter when creating a compute environment. If serviceRole is not provided then Service Linked Role will be created (or reused if it already exists).
* api-change:``sagemaker``: Support new target device ml_eia2 in SageMaker CreateCompilationJob API


1.19.29
=======

* api-change:``mwaa``: This release adds UPDATE_FAILED and UNAVAILABLE MWAA environment states.
* api-change:``gamelift``: GameLift expands to six new AWS Regions, adds support for multi-location fleets to streamline management of hosting resources, and lets you customize more of the game session placement process.
* api-change:``mediaconnect``: This release adds support for the SRT-listener protocol on sources and outputs.
* api-change:``lambda``: Allow empty list for function response types
* api-change:``mediatailor``: MediaTailor channel assembly is a new manifest-only service that allows you to assemble linear streams using your existing VOD content.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``accessanalyzer``: This release adds support for the ValidatePolicy API. IAM Access Analyzer is adding over 100 policy checks and actionable recommendations that help you validate your policies during authoring.


1.19.28
=======

* api-change:``fis``: Initial release of AWS Fault Injection Simulator, a managed service that enables you to perform fault injection experiments on your AWS workloads
* api-change:``codedeploy``: AWS CodeDeploy can now detect instances running an outdated revision of your application and automatically update them with the latest revision.
* api-change:``emr``: Update emr command to latest version
* api-change:``ecs``: This is for ecs exec feature release which includes two new APIs - execute-command and update-cluster and an AWS CLI customization for execute-command API


1.19.27
=======

* api-change:``workspaces``: Adds API support for WorkSpaces bundle management operations.
* api-change:``mediatailor``: MediaTailor channel assembly is a new manifest-only service that allows you to assemble linear streams using your existing VOD content.
* api-change:``cur``: - Added optional billingViewArn field for OSG.


1.19.26
=======

* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


1.19.25
=======

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.19.24
=======

* api-change:``efs``: Update efs command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


1.19.23
=======

* api-change:``s3``: Update s3 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


1.19.22
=======

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``shield``: Update shield command to latest version


1.19.21
=======

* api-change:``mwaa``: Update mwaa command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.19.20
=======

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``wellarchitected``: Update wellarchitected command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``forecast``: Update forecast command to latest version


1.19.19
=======

* api-change:``events``: Update events command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version


1.19.18
=======

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.19.17
=======

* api-change:``eks``: Update eks command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``emr``: Update emr command to latest version


1.19.16
=======

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``transfer``: Update transfer command to latest version


1.19.15
=======

* api-change:``appflow``: Update appflow command to latest version
* api-change:``ecr-public``: Update ecr-public command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``es``: Update es command to latest version


1.19.14
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``s3control``: Update s3control command to latest version


1.19.13
=======

* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.19.12
=======

* api-change:``rds``: Update rds command to latest version


1.19.11
=======

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``health``: Update health command to latest version


1.19.10
=======

* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``config``: Update config command to latest version


1.19.9
======

* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.19.8
======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``workmailmessageflow``: Update workmailmessageflow command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version


1.19.7
======

* api-change:``detective``: Update detective command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``iam``: Update iam command to latest version


1.19.6
======

* api-change:``databrew``: Update databrew command to latest version
* api-change:``rds``: Update rds command to latest version


1.19.5
======

* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.19.4
======

* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.19.3
======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``macie``: Update macie command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.19.2
======

* api-change:``emr-containers``: Update emr-containers command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appflow``: Update appflow command to latest version


1.19.1
======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version
* api-change:``databrew``: Update databrew command to latest version


1.19.0
======

* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``location``: Update location command to latest version
* api-change:``route53``: Update route53 command to latest version
* feature:Python: Dropped support for Python 3.4 and 3.5
* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.18.223
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``macie2``: Update macie2 command to latest version


1.18.222
========

* api-change:``wellarchitected``: Update wellarchitected command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version


1.18.221
========

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``customer-profiles``: Update customer-profiles command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.18.220
========

* api-change:``backup``: Update backup command to latest version


1.18.219
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``greengrassv2``: Update greengrassv2 command to latest version


1.18.218
========

* api-change:``kafka``: Update kafka command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* enhancement:codeartifact: Added login support for NuGet client v4.9.4
* api-change:``securityhub``: Update securityhub command to latest version


1.18.217
========

* api-change:``chime``: Update chime command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.18.216
========

* api-change:``sns``: Update sns command to latest version


1.18.215
========

* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``s3control``: Update s3control command to latest version


1.18.214
========

* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``personalize``: Update personalize command to latest version


1.18.213
========

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.212
========

* api-change:``rds``: Update rds command to latest version
* api-change:``kms``: Update kms command to latest version


1.18.211
========

* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.18.210
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version


1.18.209
========

* api-change:``ce``: Update ce command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.18.208
========

* api-change:``healthlake``: Update healthlake command to latest version
* api-change:``cloudsearch``: Update cloudsearch command to latest version


1.18.207
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.18.206
========

* api-change:``macie2``: Update macie2 command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.18.205
========

* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version


1.18.204
========

* api-change:``cloudfront``: Update cloudfront command to latest version


1.18.203
========

* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``dms``: Update dms command to latest version


1.18.202
========

* api-change:``connect``: Update connect command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``glue``: Update glue command to latest version


1.18.201
========

* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``service-quotas``: Update service-quotas command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``connectparticipant``: Update connectparticipant command to latest version


1.18.200
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version


1.18.199
========

* api-change:``route53resolver``: Update route53resolver command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.198
========

* api-change:``amp``: Update amp command to latest version
* api-change:``location``: Update location command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``wellarchitected``: Update wellarchitected command to latest version


1.18.197
========

* api-change:``iot``: Update iot command to latest version
* api-change:``amp``: Update amp command to latest version
* api-change:``iotfleethub``: Update iotfleethub command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``iotdeviceadvisor``: Update iotdeviceadvisor command to latest version
* api-change:``greengrassv2``: Update greengrassv2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.18.196
========

* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version


1.18.195
========

* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``pi``: Update pi command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version


1.18.194
========

* api-change:``networkmanager``: Update networkmanager command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.193
========

* api-change:``redshift``: Update redshift command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version


1.18.192
========

* api-change:``sagemaker-edge``: Update sagemaker-edge command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``healthlake``: Update healthlake command to latest version
* api-change:``emr-containers``: Update emr-containers command to latest version


1.18.191
========

* api-change:``dms``: Update dms command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version


1.18.190
========

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kafka``: Update kafka command to latest version


1.18.189
========

* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``amplifybackend``: Update amplifybackend command to latest version
* api-change:``license-manager``: Update license-manager command to latest version


1.18.188
========

* api-change:``customer-profiles``: Update customer-profiles command to latest version


1.18.187
========

* api-change:``amplifybackend``: Update amplifybackend command to latest version
* api-change:``ecr-public``: Update ecr-public command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``honeycode``: Update honeycode command to latest version
* api-change:``connect-contact-lens``: Update connect-contact-lens command to latest version
* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``sagemaker-featurestore-runtime``: Update sagemaker-featurestore-runtime command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``appintegrations``: Update appintegrations command to latest version
* api-change:``profile``: Update profile command to latest version


1.18.186
========

* api-change:``ec2``: Update ec2 command to latest version


1.18.185
========

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``timestream-write``: Update timestream-write command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``mwaa``: Update mwaa command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.18.184
========

* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``timestream-query``: Update timestream-query command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version
* api-change:``signer``: Update signer command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``translate``: Update translate command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.18.183
========

* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``kafka``: Update kafka command to latest version


1.18.182
========

* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.18.181
========

* api-change:``outposts``: Update outposts command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.180
========

* api-change:``connect``: Update connect command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``macie2``: Update macie2 command to latest version


1.18.179
========

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``iotsecuretunneling``: Update iotsecuretunneling command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.18.178
========

* api-change:``textract``: Update textract command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.18.177
========

* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version


1.18.176
========

* api-change:``amplify``: Update amplify command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``forecast``: Update forecast command to latest version


1.18.175
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.174
========

* api-change:``s3``: Update s3 command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``fsx``: Update fsx command to latest version


1.18.173
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.172
========

* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``es``: Update es command to latest version


1.18.171
========

* api-change:``iot``: Update iot command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version


1.18.170
========

* api-change:``ec2``: Update ec2 command to latest version


1.18.169
========

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``sns``: Update sns command to latest version


1.18.168
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version


1.18.167
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``iot``: Update iot command to latest version


1.18.166
========

* api-change:``glue``: Update glue command to latest version


1.18.165
========

* api-change:``neptune``: Update neptune command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.18.164
========

* api-change:``macie2``: Update macie2 command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.18.163
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version


1.18.162
========

* api-change:``glue``: Update glue command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kendra``: Update kendra command to latest version


1.18.161
========

* api-change:``batch``: Update batch command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


1.18.160
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``docdb``: Update docdb command to latest version
* api-change:``backup``: Update backup command to latest version


1.18.159
========

* api-change:``organizations``: Update organizations command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.18.158
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``xray``: Update xray command to latest version


1.18.157
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``snowball``: Update snowball command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``eks``: Update eks command to latest version


1.18.156
========

* api-change:``events``: Update events command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``sns``: Update sns command to latest version


1.18.155
========

* api-change:``ce``: Update ce command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.18.154
========

* api-change:``marketplace-catalog``: Update marketplace-catalog command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.153
========

* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.18.152
========

* api-change:``s3``: Update s3 command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.18.151
========

* api-change:``glue``: Update glue command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version


1.18.150
========

* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``s3outposts``: Update s3outposts command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``emr``: Update emr command to latest version


1.18.149
========

* api-change:``schemas``: Update schemas command to latest version
* api-change:``timestream-query``: Update timestream-query command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``timestream-write``: Update timestream-write command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``connect``: Update connect command to latest version


1.18.148
========

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``rds``: Update rds command to latest version


1.18.147
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``docdb``: Update docdb command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``batch``: Update batch command to latest version


1.18.146
========

* api-change:``eks``: Update eks command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``savingsplans``: Update savingsplans command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.18.145
========

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``translate``: Update translate command to latest version


1.18.144
========

* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version


1.18.143
========

* api-change:``rds``: Update rds command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version


1.18.142
========

* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version


1.18.141
========

* api-change:``kendra``: Update kendra command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


1.18.140
========

* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.18.139
========

* api-change:``kendra``: Update kendra command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.18.138
========

* api-change:``docdb``: Update docdb command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.137
========

* api-change:``workspaces``: Update workspaces command to latest version


1.18.136
========

* api-change:``s3``: Update s3 command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``ebs``: Update ebs command to latest version


1.18.135
========

* api-change:``glue``: Update glue command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version


1.18.134
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.18.133
========

* api-change:``xray``: Update xray command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.132
========

* api-change:``kendra``: Update kendra command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version


1.18.131
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``macie2``: Update macie2 command to latest version


1.18.130
========

* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version


1.18.129
========

* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sqs``: Update sqs command to latest version


1.18.128
========

* api-change:``cur``: Update cur command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``route53``: Update route53 command to latest version


1.18.127
========

* api-change:``redshift``: Update redshift command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``gamelift``: Update gamelift command to latest version


1.18.126
========

* api-change:``route53resolver``: Update route53resolver command to latest version
* api-change:``appflow``: Update appflow command to latest version


1.18.125
========

* api-change:``xray``: Update xray command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``logs``: Update logs command to latest version


1.18.124
========

* api-change:``chime``: Update chime command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``fsx``: Update fsx command to latest version


1.18.123
========

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``lakeformation``: Update lakeformation command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.18.122
========

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``identitystore``: Update identitystore command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version


1.18.121
========

* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``elb``: Update elb command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.18.120
========

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.119
========

* api-change:``rds``: Update rds command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``eks``: Update eks command to latest version


1.18.118
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``lambda``: Update lambda command to latest version


1.18.117
========

* api-change:``organizations``: Update organizations command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``s3``: Update s3 command to latest version
* enhancement:``codeartifact login``: Add support for ``--namespace`` parameter `#5291 <https://github.com/aws/aws-cli/issues/5291>`__


1.18.116
========

* api-change:``savingsplans``: Update savingsplans command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version


1.18.115
========

* api-change:``organizations``: Update organizations command to latest version
* api-change:``sms``: Update sms command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``glue``: Update glue command to latest version


1.18.114
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version


1.18.113
========

* api-change:``appsync``: Update appsync command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``fsx``: Update fsx command to latest version


1.18.112
========

* api-change:``health``: Update health command to latest version


1.18.111
========

* api-change:``ssm``: Update ssm command to latest version


1.18.110
========

* api-change:``chime``: Update chime command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version


1.18.109
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.18.108
========

* api-change:``ecr``: Update ecr command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version


1.18.107
========

* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``rds``: Update rds command to latest version


1.18.106
========

* api-change:``datasync``: Update datasync command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.105
========

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.18.104
========

* api-change:``config``: Update config command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``directconnect``: Update directconnect command to latest version


1.18.103
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.18.102
========

* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version


1.18.101
========

* api-change:``rds``: Update rds command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.100
========

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``appsync``: Update appsync command to latest version


1.18.99
=======

* bugfix:``codeartifact login``: Fix issue with displaying expiration times


1.18.98
=======

* enhancement:``codeartifact login``: Add expiration duration support
* enhancement:docs: Improve AWS CLI docs to include documentation strings for parameters in nested input structures
* api-change:``ivs``: Update ivs command to latest version


1.18.97
=======

* api-change:``ebs``: Update ebs command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


1.18.96
=======

* api-change:``organizations``: Update organizations command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``forecast``: Update forecast command to latest version


1.18.95
=======

* api-change:``efs``: Update efs command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``lakeformation``: Update lakeformation command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


1.18.94
=======

* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


1.18.93
=======

* api-change:``connect``: Update connect command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.18.92
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``chime``: Update chime command to latest version


1.18.91
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.18.90
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version


1.18.89
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.18.88
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version


1.18.87
=======

* api-change:``fsx``: Update fsx command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``honeycode``: Update honeycode command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.18.86
=======

* api-change:``organizations``: Update organizations command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version


1.18.85
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.84
=======

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.83
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``support``: Update support command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* enchancement:``codeartifact``: Backport ``login`` command to AWS CLI v1
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.82
=======

* api-change:``route53``: Update route53 command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``snowball``: Update snowball command to latest version


1.18.81
=======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``qldb``: Update qldb command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``polly``: Update polly command to latest version


1.18.80
=======

* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``iot``: Update iot command to latest version


1.18.79
=======

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version


1.18.78
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``iot-data``: Update iot-data command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version


1.18.77
=======

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version


1.18.76
=======

* api-change:``transfer``: Update transfer command to latest version
* bugfix:config file: Improve config parsing to handle values with square brackets. fixes `#5263 <https://github.com/aws/aws-cli/issues/5263>`__


1.18.75
=======

* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``shield``: Update shield command to latest version


1.18.74
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


1.18.73
=======

* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.72
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.18.71
=======

* api-change:``guardduty``: Update guardduty command to latest version


1.18.70
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``worklink``: Update worklink command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``athena``: Update athena command to latest version


1.18.69
=======

* api-change:``workmail``: Update workmail command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``marketplace-catalog``: Update marketplace-catalog command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version


1.18.68
=======

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.18.67
=======

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``macie``: Update macie command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.66
=======

* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


1.18.65
=======

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``synthetics``: Update synthetics command to latest version


1.18.64
=======

* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``appmesh``: Update appmesh command to latest version


1.18.63
=======

* api-change:``health``: Update health command to latest version
* bugfix:s3: Mute warnings for not restored glacier deep archive objects if --ignore-glacier-warnings option enabled. Fixes `#4039 <https://github.com/aws/aws-cli/issues/4039>`__
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``chime``: Update chime command to latest version


1.18.62
=======

* api-change:``qldb``: Update qldb command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.61
=======

* api-change:``ecr``: Update ecr command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``sts``: Update sts command to latest version


1.18.60
=======

* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.59
=======

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``macie2``: Update macie2 command to latest version


1.18.58
=======

* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``workmail``: Update workmail command to latest version


1.18.57
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``kendra``: Update kendra command to latest version


1.18.56
=======

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``guardduty``: Update guardduty command to latest version


1.18.55
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``route53``: Update route53 command to latest version


1.18.54
=======

* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version


1.18.53
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``support``: Update support command to latest version


1.18.52
=======

* api-change:``s3control``: Update s3control command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``apigateway``: Update apigateway command to latest version


1.18.51
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``efs``: Update efs command to latest version


1.18.50
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``schemas``: Update schemas command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.18.49
=======

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``waf``: Update waf command to latest version


1.18.48
=======

* api-change:``ecr``: Update ecr command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version


1.18.47
=======

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* bugfix:cloudformation: Fixed an issue with ``cloudformation package`` where virtual style S3 URLs were incorrectly validated for a stack resource's template URL.
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``dms``: Update dms command to latest version


1.18.46
=======

* api-change:``dlm``: Update dlm command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``elastic-inference``: Update elastic-inference command to latest version


1.18.45
=======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ram``: Update ram command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``transfer``: Update transfer command to latest version


1.18.44
=======

* api-change:``fms``: Update fms command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version


1.18.43
=======

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``route53domains``: Update route53domains command to latest version
* api-change:``ce``: Update ce command to latest version


1.18.42
=======

* api-change:``ce``: Update ce command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``synthetics``: Update synthetics command to latest version


1.18.41
=======

* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version


1.18.40
=======

* api-change:``snowball``: Update snowball command to latest version
* api-change:``sagemaker-a2i-runtime``: Update sagemaker-a2i-runtime command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``mgh``: Update mgh command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.18.39
=======

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``migrationhub-config``: Update migrationhub-config command to latest version


1.18.38
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version


1.18.37
=======

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


1.18.36
=======

* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``robomaker``: Update robomaker command to latest version


1.18.35
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.18.34
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version


1.18.33
=======

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``elastic-inference``: Update elastic-inference command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``lambda``: Update lambda command to latest version


1.18.32
=======

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version


1.18.31
=======

* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``kendra``: Update kendra command to latest version


1.18.30
=======

* api-change:``fsx``: Update fsx command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.18.29
=======

* enhancement:shorthand: The CLI now no longer allows a key to be spcified twice in a shorthand parameter. For example foo=bar,foo=baz would previously be accepted, with only baz being set, and foo=bar silently being ignored. Now an error will be raised pointing out the issue, and suggesting a fix.
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``ce``: Update ce command to latest version


1.18.28
=======

* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``athena``: Update athena command to latest version


1.18.27
=======

* api-change:``route53``: Update route53 command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version


1.18.26
=======

* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.18.25
=======

* api-change:``outposts``: Update outposts command to latest version
* api-change:``acm``: Update acm command to latest version


1.18.24
=======

* api-change:``personalize``: Update personalize command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version


1.18.23
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.18.22
=======

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.18.21
=======

* api-change:``appconfig``: Update appconfig command to latest version


1.18.20
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.18.19
=======

* api-change:``efs``: Update efs command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.18.18
=======

* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version


1.18.17
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.18.16
=======

* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``signer``: Update signer command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``guardduty``: Update guardduty command to latest version


1.18.15
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``guardduty``: Update guardduty command to latest version


1.18.14
=======

* api-change:``pinpoint``: Update pinpoint command to latest version


1.18.13
=======

* enhancement:PyYAML: Increased the uppber bound on the PyYAML dependency to 5.3.
* api-change:``ec2``: Update ec2 command to latest version


1.18.12
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version


1.18.11
=======

* api-change:``config``: Update config command to latest version


1.18.10
=======

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``sagemaker-a2i-runtime``: Update sagemaker-a2i-runtime command to latest version
* api-change:``workdocs``: Update workdocs command to latest version
* api-change:``config``: Update config command to latest version


1.18.9
======

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version


1.18.8
======

* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* bugfix:codecommit: Fix codecommit credential-helper input parsing to allow a trailing newline.
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.18.7
======

* api-change:``kafka``: Update kafka command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``outposts``: Update outposts command to latest version


1.18.6
======

* api-change:``events``: Update events command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``snowball``: Update snowball command to latest version
* api-change:``docdb``: Update docdb command to latest version


1.18.5
======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version


1.18.4
======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``savingsplans``: Update savingsplans command to latest version


1.18.3
======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.18.2
======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``rds``: Update rds command to latest version


1.18.1
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.18.0
======

* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* feature:retries: Add support for retry modes including ``standard`` and ``adaptive`` (boto/botocore`#1972 <https://github.com/aws/aws-cli/issues/1972>`__)


1.17.17
=======

* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version


1.17.16
=======

* api-change:``es``: Update es command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``neptune``: Update neptune command to latest version


1.17.15
=======

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.17.14
=======

* api-change:``docdb``: Update docdb command to latest version
* api-change:``kms``: Update kms command to latest version


1.17.13
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version


1.17.12
=======

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ebs``: Update ebs command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.17.11
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* bugfix:ec2: Fixed a paramter validation bug for the ec2 bundle-instance parameter --storage.
* api-change:``forecastquery``: Update forecastquery command to latest version


1.17.10
=======

* api-change:``workmail``: Update workmail command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``iot``: Update iot command to latest version
* enhancement:``ecr``: Add ``get-login-password``, alternative to ``get-login`` (`#4874 <https://github.com/aws/aws-cli/issues/4874>`__)


1.17.9
======

* api-change:``eks``: Update eks command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.17.8
======

* api-change:``rds``: Update rds command to latest version
* api-change:``iam``: Update iam command to latest version


1.17.7
======

* api-change:``discovery``: Update discovery command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.17.6
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.17.5
======

* api-change:``batch``: Update batch command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``neptune``: Update neptune command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.17.4
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ds``: Update ds command to latest version


1.17.3
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.17.2
======

* api-change:``ec2``: Update ec2 command to latest version


1.17.1
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``efs``: Update efs command to latest version


1.17.0
======

* api-change:``sagemaker``: Update sagemaker command to latest version
* feature:Python: Dropped support for Python 2.6 and 3.3.
* api-change:``transfer``: Update transfer command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.314
========

* api-change:``logs``: Update logs command to latest version
* bugfix:dynamodb: Fixed an issue that could cause paginated scans and queries to not fetch the complete list of results on tables with a binary primary key.


1.16.313
========

* api-change:``translate``: Update translate command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``fms``: Update fms command to latest version


1.16.312
========

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``mgh``: Update mgh command to latest version


1.16.311
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.16.310
========

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.16.309
========

* api-change:``detective``: Update detective command to latest version
* api-change:``health``: Update health command to latest version
* api-change:``fsx``: Update fsx command to latest version


1.16.308
========

* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.307
========

* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.16.306
========

* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version


1.16.305
========

* api-change:``iot``: Update iot command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.304
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version


1.16.303
========

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``detective``: Update detective command to latest version


1.16.302
========

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version


1.16.301
========

* api-change:``ec2``: Update ec2 command to latest version


1.16.300
========

* api-change:``kendra``: Update kendra command to latest version


1.16.299
========

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.16.297
========

* api-change:``kinesis-video-signaling``: Update kinesis-video-signaling command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version


1.16.296
========

* api-change:``ebs``: Update ebs command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``lambda``: Update lambda command to latest version


1.16.295
========

* api-change:``ecs``: Update ecs command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker-a2i-runtime``: Update sagemaker-a2i-runtime command to latest version
* api-change:``networkmanager``: Update networkmanager command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``kendra``: Update kendra command to latest version


1.16.294
========

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version


1.16.293
========

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``schemas``: Update schemas command to latest version


1.16.292
========

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``elastic-inference``: Update elastic-inference command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.16.291
========

* api-change:``athena``: Update athena command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``ram``: Update ram command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``iotsecuretunneling``: Update iotsecuretunneling command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.16.290
========

* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.288
========

* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``connectparticipant``: Update connectparticipant command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.16.287
========

* api-change:``fsx``: Update fsx command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``mgh``: Update mgh command to latest version
* api-change:``migrationhub-config``: Update migrationhub-config command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version


1.16.285
========

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``iot``: Update iot command to latest version


1.16.284
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version


1.16.283
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.16.282
========

* api-change:``personalize``: Update personalize command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version


1.16.281
========

* api-change:``dlm``: Update dlm command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``cloudsearch``: Update cloudsearch command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version


1.16.280
========

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``marketplace-catalog``: Update marketplace-catalog command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.16.279
========

* api-change:``ce``: Update ce command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version


1.16.278
========

* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.16.277
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``sso``: Update sso command to latest version
* api-change:``sso-oidc``: Update sso-oidc command to latest version


1.16.276
========

* api-change:``savingsplans``: Update savingsplans command to latest version


1.16.275
========

* api-change:``budgets``: Update budgets command to latest version
* api-change:``savingsplans``: Update savingsplans command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``signer``: Update signer command to latest version


1.16.274
========

* api-change:``codestar-notifications``: Update codestar-notifications command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.273
========

* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``dax``: Update dax command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.272
========

* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


1.16.271
========

* api-change:``s3``: Update s3 command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``support``: Update support command to latest version


1.16.270
========

* api-change:``elasticache``: Update elasticache command to latest version


1.16.269
========

* api-change:``appstream``: Update appstream command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version


1.16.268
========

* api-change:``s3``: Update s3 command to latest version


1.16.267
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.16.266
========

* enhancement:``eks get-token``: Refactor ``get-token`` implementation and add support for non-aws partitions and regions.
* api-change:``chime``: Update chime command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* enhancement:``sts``: Add support for configuring the use of regional STS endpoints.


1.16.265
========

* api-change:``polly``: Update polly command to latest version
* api-change:``connect``: Update connect command to latest version


1.16.264
========

* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``iotevents``: Update iotevents command to latest version


1.16.263
========

* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.16.262
========

* api-change:``batch``: Update batch command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.261
========

* api-change:``kafka``: Update kafka command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version


1.16.260
========

* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version


1.16.259
========

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``personalize``: Update personalize command to latest version


1.16.258
========

* api-change:``greengrass``: Update greengrass command to latest version


1.16.257
========

* api-change:``fms``: Update fms command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version


1.16.256
========

* api-change:``kafka``: Update kafka command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.255
========

* api-change:``firehose``: Update firehose command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.16.254
========

* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``snowball``: Update snowball command to latest version


1.16.253
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version
* enhancment:colorama: Increased the upper bound on the colorama dependency to 0.4.2.
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.16.252
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version


1.16.251
========

* api-change:``lightsail``: Update lightsail command to latest version


1.16.250
========

* api-change:``docdb``: Update docdb command to latest version


1.16.249
========

* api-change:``mq``: Update mq command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``waf``: Update waf command to latest version


1.16.248
========

* api-change:``amplify``: Update amplify command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.247
========

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.16.246
========

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version


1.16.245
========

* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``datasync``: Update datasync command to latest version


1.16.244
========

* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.16.243
========

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.242
========

* api-change:``ecs``: Update ecs command to latest version
* enhancement:``cloudtrail validate-logs``: Add support for validating logs from organizational trails
* api-change:``glue``: Update glue command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version


1.16.241
========

* api-change:``ram``: Update ram command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``apigateway``: Update apigateway command to latest version


1.16.240
========

* api-change:``personalize``: Update personalize command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``iam``: Update iam command to latest version


1.16.239
========

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.238
========

* api-change:``workmailmessageflow``: Update workmailmessageflow command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.16.237
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``ses``: Update ses command to latest version
* api-change:``config``: Update config command to latest version


1.16.236
========

* api-change:``storagegateway``: Update storagegateway command to latest version


1.16.235
========

* api-change:``appstream``: Update appstream command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``qldb``: Update qldb command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.234
========

* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version


1.16.233
========

* api-change:``config``: Update config command to latest version


1.16.232
========

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version


1.16.231
========

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``gamelift``: Update gamelift command to latest version


1.16.230
========

* api-change:``mq``: Update mq command to latest version
* api-change:``apigatewaymanagementapi``: Update apigatewaymanagementapi command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.229
========

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.228
========

* api-change:``sqs``: Update sqs command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.227
========

* api-change:``organizations``: Update organizations command to latest version


1.16.226
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.16.225
========

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.224
========

* api-change:``rds``: Update rds command to latest version
* api-change:``datasync``: Update datasync command to latest version


1.16.223
========

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``forecastquery``: Update forecastquery command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.16.222
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.16.221
========

* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``cur``: Update cur command to latest version


1.16.220
========

* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.219
========

* api-change:``glue``: Update glue command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version


1.16.218
========

* api-change:``ec2``: Update ec2 command to latest version


1.16.217
========

* api-change:``appsync``: Update appsync command to latest version


1.16.216
========

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* enhancement:Shorthand: Support colon char in shorthand syntax key names (#4348)
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.16.215
========

* api-change:``redshift``: Update redshift command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``iot``: Update iot command to latest version


1.16.214
========

* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``lakeformation``: Update lakeformation command to latest version


1.16.213
========

* api-change:``application-insights``: Update application-insights command to latest version
* bugfix:MSI: Fix race condition when running S3 commands on windows `#4247 <https://github.com/aws/aws-cli/issues/4247>`__


1.16.212
========

* api-change:``batch``: Update batch command to latest version


1.16.211
========

* api-change:``iot``: Update iot command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``datasync``: Update datasync command to latest version


1.16.210
========

* api-change:``sts``: Update sts command to latest version
* enhancement:Credentials: Add support for a credential provider that handles resolving credentials via STS AssumeRoleWithWebIdentity


1.16.209
========

* api-change:``route53``: Update route53 command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.208
========

* api-change:``codecommit``: Update codecommit command to latest version


1.16.207
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``glue``: Update glue command to latest version


1.16.206
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.16.205
========

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version


1.16.204
========

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.16.203
========

* api-change:``shield``: Update shield command to latest version
* api-change:``mq``: Update mq command to latest version


1.16.202
========

* bugfix:Dependency: Fixed dependency issue with broken docutils aws/aws-cli`#4332 <https://github.com/aws/aws-cli/issues/4332>`__


1.16.201
========

* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``sqs``: Update sqs command to latest version


1.16.200
========

* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.16.199
========

* api-change:``dms``: Update dms command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


1.16.198
========

* api-change:``es``: Update es command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version


1.16.197
========

* api-change:``events``: Update events command to latest version


1.16.196
========

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``glacier``: Update glacier command to latest version


1.16.195
========

* api-change:``amplify``: Update amplify command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version
* api-change:``efs``: Update efs command to latest version


1.16.194
========

* api-change:``ce``: Update ce command to latest version


1.16.193
========

* api-change:``rds``: Update rds command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``swf``: Update swf command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.192
========

* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.16.191
========

* api-change:``organizations``: Update organizations command to latest version
* api-change:``docdb``: Update docdb command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.190
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``workspaces``: Update workspaces command to latest version


1.16.189
========

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``ec2-instance-connect``: Update ec2-instance-connect command to latest version


1.16.188
========

* api-change:``dynamodb``: Update dynamodb command to latest version


1.16.187
========

* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``codecommit``: Update codecommit command to latest version


1.16.186
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.185
========

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``service-quotas``: Update service-quotas command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.16.184
========

* api-change:``mediapackage``: Update mediapackage command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``kinesis-video-media``: Update kinesis-video-media command to latest version
* api-change:``iam``: Update iam command to latest version


1.16.183
========

* api-change:``rds``: Update rds command to latest version
* api-change:``opsworks``: Update opsworks command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``health``: Update health command to latest version
* api-change:``iotevents-data``: Update iotevents-data command to latest version


1.16.182
========

* api-change:``eks``: Update eks command to latest version


1.16.181
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version


1.16.180
========

* api-change:``neptune``: Update neptune command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``robomaker``: Update robomaker command to latest version


1.16.179
========

* api-change:``appstream``: Update appstream command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.178
========

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.177
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.16.176
========

* api-change:``sagemaker``: Update sagemaker command to latest version


1.16.175
========

* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.174
========

* api-change:``ec2``: Update ec2 command to latest version


1.16.173
========

* api-change:``ecs``: Update ecs command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``ses``: Update ses command to latest version


1.16.172
========

* api-change:``glue``: Update glue command to latest version


1.16.171
========

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.170
========

* api-change:``rds``: Update rds command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.169
========

* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``iotevents-data``: Update iotevents-data command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``iotevents``: Update iotevents command to latest version


1.16.168
========

* api-change:``dlm``: Update dlm command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``iotthingsgraph``: Update iotthingsgraph command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.167
========

* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``chime``: Update chime command to latest version


1.16.166
========

* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``mediastore-data``: Update mediastore-data command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version


1.16.165
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version


1.16.164
========

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``worklink``: Update worklink command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.163
========

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``datasync``: Update datasync command to latest version


1.16.162
========

* api-change:``kafka``: Update kafka command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version


1.16.161
========

* api-change:``appstream``: Update appstream command to latest version


1.16.160
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``s3``: Update s3 command to latest version


1.16.159
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.16.158
========

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.157
========

* api-change:``datasync``: Update datasync command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.16.156
========

* api-change:``glue``: Update glue command to latest version
* api-change:``sts``: Update sts command to latest version


1.16.155
========

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version


1.16.154
========

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``appsync``: Update appsync command to latest version


1.16.153
========

* api-change:``config``: Update config command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``sts``: Update sts command to latest version


1.16.152
========

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.16.151
========

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``kms``: Update kms command to latest version


1.16.150
========

* api-change:``xray``: Update xray command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.149
========

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``neptune``: Update neptune command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``directconnect``: Update directconnect command to latest version


1.16.148
========

* api-change:``transfer``: Update transfer command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.147
========

* api-change:``iam``: Update iam command to latest version
* api-change:``sns``: Update sns command to latest version


1.16.146
========

* api-change:``batch``: Update batch command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``inspector``: Update inspector command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``workspaces``: Update workspaces command to latest version


1.16.145
========

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* bugfix:Cloudformation: Support non-AWS partition regions in CloudFormation deploy and package. Fixes `#3635 <https://github.com/aws/aws-cli/issues/3635>`__.
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version


1.16.144
========

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version


1.16.143
========

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``worklink``: Update worklink command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``discovery``: Update discovery command to latest version


1.16.142
========

* api-change:``polly``: Update polly command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.141
========

* api-change:``redshift``: Update redshift command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.16.140
========

* api-change:``medialive``: Update medialive command to latest version
* api-change:``iot1click-devices``: Update iot1click-devices command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.139
========

* api-change:``eks``: Update eks command to latest version
* api-change:``iam``: Update iam command to latest version


1.16.138
========

* api-change:``batch``: Update batch command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


1.16.137
========

* api-change:``acm``: Update acm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


1.16.136
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``emr``: Update emr command to latest version


1.16.135
========

* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


1.16.134
========

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.16.133
========

* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``transfer``: Update transfer command to latest version


1.16.132
========

* api-change:``glue``: Update glue command to latest version
* api-change:``workmail``: Update workmail command to latest version


1.16.131
========

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``iot1click-devices``: Update iot1click-devices command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``fms``: Update fms command to latest version


1.16.130
========

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``iot1click-projects``: Update iot1click-projects command to latest version


1.16.129
========

* api-change:``iot``: Update iot command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``lightsail``: Update lightsail command to latest version


1.16.128
========

* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version


1.16.127
========

* api-change:``config``: Update config command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.126
========

* api-change:``dms``: Update dms command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``chime``: Update chime command to latest version


1.16.125
========

* api-change:``acm``: Update acm command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version


1.16.124
========

* api-change:``config``: Update config command to latest version
* api-change:``logs``: Update logs command to latest version


1.16.123
========

* api-change:``serverlessrepo``: Update serverlessrepo command to latest version


1.16.122
========

* api-change:``glue``: Update glue command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``iot``: Update iot command to latest version


1.16.121
========

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.120
========

* api-change:``rds``: Update rds command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.119
========

* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.118
========

* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.16.117
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.16.116
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version


1.16.115
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.16.114
========

* api-change:``waf``: Update waf command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version


1.16.113
========

* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``cur``: Update cur command to latest version


1.16.112
========

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``mediastore``: Update mediastore command to latest version


1.16.111
========

* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``glue``: Update glue command to latest version


1.16.110
========

* api-change:``kinesisvideo``: Update kinesisvideo command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``kinesis-video-media``: Update kinesis-video-media command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``workdocs``: Update workdocs command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``transfer``: Update transfer command to latest version


1.16.109
========

* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``directconnect``: Update directconnect command to latest version


1.16.108
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``ds``: Update ds command to latest version


1.16.107
========

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``athena``: Update athena command to latest version


1.16.106
========

* api-change:``iot``: Update iot command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.16.105
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version


1.16.104
========

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version


1.16.103
========

* api-change:``lambda``: Update lambda command to latest version


1.16.102
========

* api-change:``appstream``: Update appstream command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.101
========

* api-change:``ecs``: Update ecs command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.16.100
========

* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.16.99
=======

* api-change:``fsx``: Update fsx command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.98
=======

* api-change:``shield``: Update shield command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.16.97
=======

* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.16.96
=======

* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.16.95
=======

* api-change:``logs``: Update logs command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``sms-voice``: Update sms-voice command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.94
=======

* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``apigatewaymanagementapi``: Update apigatewaymanagementapi command to latest version
* api-change:``worklink``: Update worklink command to latest version


1.16.93
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.16.92
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.91
=======

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


1.16.90
=======

* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``ce``: Update ce command to latest version


1.16.89
=======

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.88
=======

* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``emr``: Update emr command to latest version


1.16.87
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.86
=======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``docdb``: Update docdb command to latest version


1.16.85
=======

* api-change:``appmesh``: Update appmesh command to latest version


1.16.84
=======

* api-change:``ecs``: Update ecs command to latest version
* enhancment:cloudformation: Unroll yaml anchors in cloudformation package.
* api-change:``devicefarm``: Update devicefarm command to latest version


1.16.83
=======

* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.16.82
=======

* api-change:``opsworkscm``: Update opsworkscm command to latest version


1.16.81
=======

* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``sms-voice``: Update sms-voice command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version


1.16.80
=======

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.16.79
=======

* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.16.78
=======

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``apigatewaymanagementapi``: Update apigatewaymanagementapi command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version


1.16.77
=======

* api-change:``quicksight``: Update quicksight command to latest version
* enhancement:``cloudformation``: Update ``cloudformation package`` command to upload readme and license files
* api-change:``ecr``: Update ecr command to latest version


1.16.76
=======

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.16.75
=======

* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.16.74
=======

* bugfix:appstream: Fix issue where --feedback-url was loading the content of the url to use as the input value.
* api-change:``glue``: Update glue command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.16.73
=======

* api-change:``connect``: Update connect command to latest version
* api-change:``mediastore``: Update mediastore command to latest version
* enhancement:AssumeRole: Add support for duration_seconds in CLI config profiles (boto/botocore`#1600 <https://github.com/aws/aws-cli/issues/1600>`__).
* api-change:``ecs``: Update ecs command to latest version


1.16.72
=======

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iam``: Update iam command to latest version


1.16.71
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.16.70
=======

* api-change:``ce``: Update ce command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``mq``: Update mq command to latest version


1.16.69
=======

* api-change:``s3``: Update s3 command to latest version
* api-change:``health``: Update health command to latest version


1.16.68
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.16.67
=======

* api-change:``s3``: Update s3 command to latest version


1.16.66
=======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``s3``: Update s3 command to latest version


1.16.65
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version


1.16.64
=======

* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.63
=======

* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``translate``: Update translate command to latest version


1.16.62
=======

* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``sms``: Update sms command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.16.61
=======

* api-change:``amplify``: Update amplify command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``snowball``: Update snowball command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``datasync``: Update datasync command to latest version


1.16.60
=======

* api-change:``rekognition``: Update rekognition command to latest version


1.16.59
=======

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.16.58
=======

* api-change:``config``: Update config command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``workdocs``: Update workdocs command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.57
=======

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.16.56
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``route53resolver``: Update route53resolver command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``ram``: Update ram command to latest version
* api-change:``sms-voice``: Update sms-voice command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.55
=======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.16.54
=======

* api-change:``chime``: Update chime command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.16.53
=======

* api-change:``budgets``: Update budgets command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version


1.16.52
=======

* api-change:``mediapackage``: Update mediapackage command to latest version


1.16.51
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.16.50
=======

* api-change:``ce``: Update ce command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.49
=======

* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``pinpoint-email``: Update pinpoint-email command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.48
=======

* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.47
=======

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.16.46
=======

* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.16.45
=======

* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``mediastore-data``: Update mediastore-data command to latest version


1.16.44
=======

* api-change:``chime``: Update chime command to latest version
* bugfix:Credentials: Fix issue where incorrect region was being used when using assume role credentials outside of the `aws` partition.
* api-change:``rds``: Update rds command to latest version
* api-change:``dms``: Update dms command to latest version


1.16.43
=======

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.16.42
=======

* api-change:``ec2``: Update ec2 command to latest version


1.16.41
=======

* api-change:``codestar``: Update codestar command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.16.40
=======

* api-change:``ec2``: Update ec2 command to latest version


1.16.39
=======

* api-change:``shield``: Update shield command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.16.38
=======

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.16.37
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``route53``: Update route53 command to latest version


1.16.36
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``events``: Update events command to latest version


1.16.35
=======

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version


1.16.34
=======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.33
=======

* api-change:``cloudtrail``: Update cloudtrail command to latest version


1.16.32
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.16.31
=======

* api-change:``es``: Update es command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.16.30
=======

* api-change:``ssm``: Update ssm command to latest version


1.16.29
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``iot-jobs-data``: Update iot-jobs-data command to latest version


1.16.28
=======

* api-change:``ds``: Update ds command to latest version


1.16.27
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.26
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.16.25
=======

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``guardduty``: Update guardduty command to latest version


1.16.24
=======

* api-change:``codestar``: Update codestar command to latest version
* bugfix:s3: Fixed a bug where `--sse-c-key` and `--sse-c-copy-source-key` were modeled as string values rather than bytes values, which make them impossible to use on python 3 unless your key happened to be all unicode.
* api-change:``ec2``: Update ec2 command to latest version


1.16.23
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``mq``: Update mq command to latest version


1.16.22
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``sqs``: Update sqs command to latest version


1.16.21
=======

* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ds``: Update ds command to latest version


1.16.20
=======

* api-change:``connect``: Update connect command to latest version
* api-change:``rds``: Update rds command to latest version


1.16.19
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.16.18
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ds``: Update ds command to latest version


1.16.17
=======

* api-change:``s3``: Update s3 command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.16.16
=======

* api-change:``es``: Update es command to latest version
* api-change:``rekognition``: Update rekognition command to latest version


1.16.15
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elastictranscoder``: Update elastictranscoder command to latest version
* enhancement:s3: ``aws s3`` subcommands that list objects will use ListObjectsV2 instead of ListObjects `#3549 <https://github.com/aws/aws-cli/issues/3549>`__.
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.16.14
=======

* api-change:``polly``: Update polly command to latest version


1.16.13
=======

* api-change:``fms``: Update fms command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ses``: Update ses command to latest version


1.16.12
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version


1.16.11
=======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version


1.16.10
=======

* api-change:``config``: Update config command to latest version
* api-change:``logs``: Update logs command to latest version


1.16.9
======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``codecommit``: Update codecommit command to latest version


1.16.8
======

* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``elb``: Update elb command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``s3``: Update s3 command to latest version


1.16.7
======

* api-change:``rds``: Update rds command to latest version
* api-change:``rekognition``: Update rekognition command to latest version


1.16.6
======

* api-change:``waf``: Update waf command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``eks``: Update eks command to latest version


1.16.5
======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.16.4
======

* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.16.3
======

* api-change:``glue``: Update glue command to latest version
* api-change:``xray``: Update xray command to latest version


1.16.2
======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``signer``: Update signer command to latest version


1.16.1
======

* api-change:``glue``: Update glue command to latest version


1.16.0
======

* api-change:``events``: Update events command to latest version
* feature:urllib3: Add support for ipv6 proxies by upgrading urllib3 version.
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.15.85
=======

* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.15.84
=======

* api-change:``snowball``: Update snowball command to latest version


1.15.83
=======

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.15.82
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.15.81
=======

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``dax``: Update dax command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.15.80
=======

* api-change:``discovery``: Update discovery command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.15.79
=======

* api-change:``devicefarm``: Update devicefarm command to latest version


1.15.78
=======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``es``: Update es command to latest version


1.15.77
=======

* api-change:``sagemaker``: Update sagemaker command to latest version


1.15.76
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``rds``: Update rds command to latest version


1.15.75
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``dax``: Update dax command to latest version
* api-change:``rds``: Update rds command to latest version


1.15.74
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.15.73
=======

* api-change:``logs``: Update logs command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.15.72
=======

* api-change:``health``: Update health command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.15.71
=======

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.15.70
=======

* api-change:``polly``: Update polly command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``kinesis``: Update kinesis command to latest version


1.15.69
=======

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.15.68
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``connect``: Update connect command to latest version


1.15.67
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``glacier``: Update glacier command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``mq``: Update mq command to latest version


1.15.66
=======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``inspector``: Update inspector command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.15.65
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.15.64
=======

* api-change:``dynamodb``: Update dynamodb command to latest version


1.15.63
=======

* api-change:``dlm``: Update dlm command to latest version
* api-change:``config``: Update config command to latest version


1.15.62
=======

* bugfix:datapipeline: Fixed an issue with multiple values for the same key when using the parameter-values option for datapipeline commands.
* api-change:``mediapackage``: Update mediapackage command to latest version


1.15.61
=======

* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.15.60
=======

* api-change:``snowball``: Update snowball command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* enhancement:rekognition: Added top level parameters to rekognition to make it possible to supply images to the operations that require bytes.


1.15.59
=======

* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version


1.15.58
=======

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``dlm``: Update dlm command to latest version


1.15.57
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``s3``: Update s3 command to latest version


1.15.56
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``opsworks``: Update opsworks command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.15.55
=======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.15.54
=======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.15.53
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version


1.15.52
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


1.15.51
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``acm``: Update acm command to latest version


1.15.50
=======

* api-change:``ssm``: Update ssm command to latest version


1.15.49
=======

* enhancement:emr: Support on demand pricing for emr clusters.


1.15.48
=======

* enhancement:Argument processing: Added cli_follow_urlparam option in the config file which can be set to false to disable the automatic following of string parameters prefixed with http:// or https://. closes #2507 #3076 #2577. Further discussion #3398.
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version


1.15.47
=======

* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


1.15.46
=======

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.15.45
=======

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.15.44
=======

* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.15.43
=======

* api-change:``macie``: Update macie command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``neptune``: Update neptune command to latest version


1.15.42
=======

* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``medialive``: Update medialive command to latest version


1.15.41
=======

* api-change:``rekognition``: Update rekognition command to latest version


1.15.40
=======

* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.15.39
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version


1.15.38
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.15.37
=======

* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.15.36
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.15.35
=======

* api-change:``mediatailor``: Update mediatailor command to latest version


1.15.34
=======

* api-change:``medialive``: Update medialive command to latest version


1.15.33
=======

* api-change:``polly``: Update polly command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.15.32
=======

* api-change:``appstream``: Update appstream command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``mgh``: Update mgh command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.15.31
=======

* api-change:``sns``: Update sns command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``redshift``: Update redshift command to latest version


1.15.30
=======

* api-change:``neptune``: Update neptune command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.15.29
=======

* api-change:``pi``: Update pi command to latest version


1.15.28
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``config``: Update config command to latest version


1.15.27
=======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``rds``: Update rds command to latest version


1.15.26
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.15.25
=======

* api-change:``cloudformation``: Update cloudformation command to latest version


1.15.24
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``ses``: Update ses command to latest version


1.15.23
=======

* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version


1.15.22
=======

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.15.21
=======

* api-change:``config``: Update config command to latest version


1.15.20
=======

* api-change:``organizations``: Update organizations command to latest version
* enhancement:colorama: Increased the upper bound on the colorama dependency to 0.3.9.
* api-change:``iot1click-devices``: Update iot1click-devices command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``iot1click-projects``: Update iot1click-projects command to latest version


1.15.19
=======

* api-change:``firehose``: Update firehose command to latest version


1.15.18
=======

* api-change:``gamelift``: Update gamelift command to latest version


1.15.17
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``budgets``: Update budgets command to latest version


1.15.16
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version


1.15.15
=======

* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``s3``: Update s3 command to latest version


1.15.14
=======

* api-change:``guardduty``: Update guardduty command to latest version


1.15.13
=======

* api-change:``appsync``: Update appsync command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.15.12
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.15.11
=======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``route53domains``: Update route53domains command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.15.10
=======

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``glacier``: Update glacier command to latest version


1.15.9
======

* api-change:``xray``: Update xray command to latest version
* bugfix:bundled-installer: Fixes an issue causing the bundled installer to fail to build on python2.6.
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* enhancement:s3: Add ONEZONE_IA option to the --storage-class argument of the s3 transfer commands


1.15.8
======

* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* bugfix:bundled-installer: Fixes a bug in the bundled installer caused by a dependency using `setup_requires`. pip doesn't manage these setup time dependencies, so we have to manually handle them. This fixes the issue where running the bundled installer on a machine without internet access would fail since we were not bundling all the transitive dependencies.


1.15.7
======

* api-change:``iot``: Update iot command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version


1.15.6
======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``firehose``: Update firehose command to latest version


1.15.5
======

* api-change:``ce``: Update ce command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version


1.15.4
======

* api-change:``glue``: Update glue command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.15.3
======

* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.15.2
======

* api-change:``batch``: Update batch command to latest version


1.15.1
======

* api-change:``ssm``: Update ssm command to latest version


1.15.0
======

* api-change:``s3``: Update s3 command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``fms``: Update fms command to latest version
* feature:s3: Add support for S3 Select. Amazon S3 Select is an Amazon S3 feature that makes it easy to retrieve specific data from the contents of an object using simple SQL expressions without having to retrieve the entire object. With this release of the Amazon S3 SDK, S3 Select API (SelectObjectContent) is now generally available in all public regions. This release supports retrieval of a subset of data using SQL clauses, like SELECT and WHERE, from delimited text files and JSON objects in Amazon S3 through the SelectObjectContent API available in AWS S3 SDK.
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version


1.14.70
=======

* api-change:``translate``: Update translate command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version


1.14.69
=======

* api-change:``es``: Update es command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


1.14.68
=======

* api-change:``connect``: Update connect command to latest version
* api-change:``acm``: Update acm command to latest version


1.14.67
=======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``greengrass``: Update greengrass command to latest version


1.14.66
=======

* api-change:``sts``: Update sts command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``mturk``: Update mturk command to latest version


1.14.65
=======

* api-change:``acm``: Update acm command to latest version


1.14.64
=======

* api-change:``dynamodb``: Update dynamodb command to latest version


1.14.63
=======

* api-change:``rds``: Update rds command to latest version


1.14.62
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.14.60
=======

* api-change:``serverlessrepo``: Update serverlessrepo command to latest version


1.14.59
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``ce``: Update ce command to latest version


1.14.58
=======

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


1.14.57
=======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.14.56
=======

* api-change:``lightsail``: Update lightsail command to latest version


1.14.55
=======

* api-change:``servicediscovery``: Update servicediscovery command to latest version


1.14.54
=======

* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``iot``: Update iot command to latest version


1.14.53
=======

* api-change:``rds``: Update rds command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``mgh``: Update mgh command to latest version


1.14.52
=======

* api-change:``medialive``: Update medialive command to latest version


1.14.51
=======

* api-change:``ecs``: Update ecs command to latest version


1.14.50
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.14.49
=======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.14.48
=======

* api-change:``ecr``: Update ecr command to latest version


1.14.47
=======

* api-change:``route53``: Update route53 command to latest version
* api-change:``sts``: Update sts command to latest version


1.14.46
=======

* api-change:``appstream``: Update appstream command to latest version


1.14.45
=======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ce``: Update ce command to latest version


1.14.44
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``codecommit``: Update codecommit command to latest version


1.14.43
=======

* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


1.14.42
=======

* api-change:``config``: Update config command to latest version
* enhancement:``s3``: Expose ``--request-payer`` to ``cp``, ``sync``, ``mv`, and ``rm`` commands.


1.14.41
=======

* api-change:``rds``: Update rds command to latest version


1.14.40
=======

* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


1.14.39
=======

* api-change:``appsync``: Update appsync command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.14.38
=======

* api-change:``route53``: Update route53 command to latest version
* api-change:``glacier``: Update glacier command to latest version


1.14.37
=======

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``kms``: Update kms command to latest version


1.14.36
=======

* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.14.35
=======

* api-change:``budgets``: Update budgets command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``dms``: Update dms command to latest version


1.14.34
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.14.33
=======

* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``opsworks``: Update opsworks command to latest version


1.14.32
=======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``mturk``: Update mturk command to latest version


1.14.31
=======

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.14.30
=======

* api-change:``budgets``: Update budgets command to latest version


1.14.29
=======

* api-change:``glue``: Update glue command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


1.14.28
=======

* api-change:``sagemaker``: Update sagemaker command to latest version


1.14.27
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version


1.14.26
=======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version


1.14.25
=======

* api-change:``lambda``: Update lambda command to latest version


1.14.24
=======

* api-change:``glue``: Update glue command to latest version


1.14.23
=======

* api-change:``elb``: Update elb command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``rds``: Update rds command to latest version


1.14.22
=======

* api-change:``kms``: Update kms command to latest version


1.14.21
=======

* api-change:``ds``: Update ds command to latest version


1.14.20
=======

* api-change:``discovery``: Update discovery command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``route53``: Update route53 command to latest version


1.14.19
=======

* api-change:``snowball``: Update snowball command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.14.18
=======

* api-change:``rds``: Update rds command to latest version


1.14.17
=======

* api-change:``workspaces``: Update workspaces command to latest version


1.14.16
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.14.15
=======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.14.14
=======

* api-change:``config``: Update config command to latest version
* api-change:``iot``: Update iot command to latest version


1.14.13
=======

* api-change:``mediastore-data``: Update mediastore-data command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``apigateway``: Update apigateway command to latest version


1.14.12
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.14.11
=======

* api-change:``appstream``: Update appstream command to latest version


1.14.10
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ses``: Update ses command to latest version
* bugfix:s3: Fixes a bug where calling the CLI from a context that has no stdin resulted in every command failing instead of only commands that required stdin.


1.14.9
======

* api-change:``codedeploy``: Update codedeploy command to latest version
* bugfix:sagemaker-runtime: Renamed the runtime.sagemaker service to sagemaker-runtime to be more consistent with existing services. The old service name is now aliased to sagemaker-runtime to maintain backwards compatibility.
* api-change:``workmail``: Update workmail command to latest version


1.14.8
======

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version


1.14.7
======

* bugfix:S3: S3 commands that encountered both an error and warning will now return the RC for error instead of warning.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.14.6
======

* api-change:``es``: Update es command to latest version
* api-change:``ses``: Update ses command to latest version


1.14.5
======

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.14.4
======

* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.14.3
======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``budgets``: Update budgets command to latest version


1.14.2
======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version


1.14.1
======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version


1.14.0
======

* api-change:``iot``: Update iot command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``translate``: Update translate command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``runtime.sagemaker``: Update runtime.sagemaker command to latest version
* api-change:``iot-jobs-data``: Update iot-jobs-data command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``glacier``: Update glacier command to latest version
* feature:``max_bandwidth``: Add the ability to set maximum bandwidth consumption for ``s3`` commands. (`issue 1090 <https://github.com/aws/aws-cli/issues/1090>`__)
* api-change:``kinesis-video-media``: Update kinesis-video-media command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.13.0
======

* feature:``cli_history``: Setting the value of ``cli_history`` to ``enabled`` in the shared config file enables the CLI to keep history of all commands ran.
* api-change:``appsync``: Update appsync command to latest version
* feature:``history list``: Lists all of the commands that have been run via the stored history of the CLI.
* api-change:``lambda``: Update lambda command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``batch``: Update batch command to latest version
* feature:``history show``: Shows the important events related to running a command that was recorded in the CLI history.
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* bugfix:Configure: Fix a bug where the configure command would write to the incorrect profile, fixes `#2970 <https://github.com/aws/aws-cli/issues/2970>`__.
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.12.2
======

* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``mediastore-data``: Update mediastore-data command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


1.12.1
======

* bugfix:Credentials: Fixes a bug causing cached credentials to break in the CLI on Windows. Fixes aws/aws-cli`#2978 <https://github.com/boto/botocore/issues/2978>`__
* api-change:``acm``: Update acm command to latest version


1.12.0
======

* enhancement:documentation: Deprecated operations will no longer appear in help documentation or be suggested in autocompletion results.
* feature:Credentials: When creating an assume role profile, you can now specify a credential source outside of the config file using the `credential_source` key.
* feature:Credentials: Adds support for the process credential provider, allowing users to specify a process to call to get credentials.
* feature:Credentials: When creating an assume role profile, you can now specify another assume role profile as the source. This allows for chaining assume role calls.
* api-change:``emr``: Update emr command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* enhancement:Arguments: Idempotency tokens are no longer marked as a required argument.
* api-change:``cloudformation``: Update cloudformation command to latest version


1.11.190
========

* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``workdocs``: Update workdocs command to latest version


1.11.189
========

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``s3``: Update s3 command to latest version


1.11.188
========

* api-change:``route53``: Update route53 command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``glue``: Update glue command to latest version


1.11.187
========

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``ses``: Update ses command to latest version


1.11.186
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``lightsail``: Update lightsail command to latest version


1.11.185
========

* api-change:``ec2``: Update ec2 command to latest version


1.11.184
========

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.11.183
========

* api-change:``rds``: Update rds command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``s3``: Update s3 command to latest version


1.11.182
========

* api-change:``kms``: Update kms command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``pricing``: Update pricing command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``organizations``: Update organizations command to latest version


1.11.181
========

* api-change:``ecs``: Update ecs command to latest version


1.11.180
========

* api-change:``apigateway``: Update apigateway command to latest version
* bugfix:datapipeline: Fixed a bug in datapipeline where list-runs could only handle 100 runs.


1.11.179
========

* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``directconnect``: Update directconnect command to latest version


1.11.178
========

* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.177
========

* api-change:``glue``: Update glue command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``elasticache``: Update elasticache command to latest version


1.11.176
========

* api-change:``organizations``: Update organizations command to latest version


1.11.175
========

* bugfix:sqs: Fixed an issue where the queue-url for an sqs operation was being fetched rather than used transparently.
* api-change:``ec2``: Update ec2 command to latest version


1.11.174
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``sqs``: Update sqs command to latest version


1.11.173
========

* api-change:``lightsail``: Update lightsail command to latest version


1.11.172
========

* api-change:``es``: Update es command to latest version


1.11.171
========

* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``cloudhsm``: Update cloudhsm command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``waf``: Update waf command to latest version
* enhancement:s3: Add a no-progress flag to s3 transfer commands. Resolves `#519 <https://github.com/aws/aws-cli/issues/519>`__.
* enchancement:cloudwatch: Extract ``--storage-resolution`` in put-metric-data as a top level argument.


1.11.170
========

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``dms``: Update dms command to latest version


1.11.169
========

* api-change:``ses``: Update ses command to latest version
* api-change:``ecr``: Update ecr command to latest version


1.11.168
========

* enhancement:``aws cloudformation``: Add support for forcing files to be zipped when uploaded
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.11.167
========

* api-change:``sqs``: Update sqs command to latest version


1.11.166
========

* api-change:``redshift``: Update redshift command to latest version


1.11.165
========

* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version
* api-change:``route53domains``: Update route53domains command to latest version


1.11.164
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.163
========

* api-change:``cloudhsm``: Update cloudhsm command to latest version


1.11.162
========

* api-change:``route53``: Update route53 command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``mturk``: Update mturk command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.11.161
========

* api-change:``pinpoint``: Update pinpoint command to latest version
* bugfix:Config: Properly handle spaces in profile names when being written out via the configure command, fixes `#2806 <https://github.com/aws/aws-cli/issues/2806>`__


1.11.160
========

* api-change:``cloudformation``: Update cloudformation command to latest version


1.11.159
========

* api-change:``rds``: Update rds command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``ecs``: Update ecs command to latest version


1.11.158
========

* api-change:``budgets``: Update budgets command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.157
========

* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version


1.11.156
========

* api-change:``ec2``: Update ec2 command to latest version


1.11.155
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``ses``: Update ses command to latest version


1.11.154
========

* api-change:``apigateway``: Update apigateway command to latest version


1.11.153
========

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.11.152
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``events``: Update events command to latest version
* bugfix:CloudFormation: CloudFormation will no longer fail for deploys that take longer than 10 minutes. Fixes `#2754 <https://github.com/aws/aws-cli/issues/2754>`__
* api-change:``batch``: Update batch command to latest version


1.11.151
========

* api-change:``ec2``: Update ec2 command to latest version


1.11.150
========

* api-change:``devicefarm``: Update devicefarm command to latest version


1.11.149
========

* api-change:``logs``: Update logs command to latest version


1.11.148
========

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version


1.11.147
========

* api-change:``budgets``: Update budgets command to latest version


1.11.146
========

* api-change:``codestar``: Update codestar command to latest version


1.11.145
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``mobile``: Update mobile command to latest version
* api-change:``gamelift``: Update gamelift command to latest version


1.11.144
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.11.143
========

* api-change:``organizations``: Update organizations command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


1.11.142
========

* api-change:``config``: Update config command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.141
========

* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``gamelift``: Update gamelift command to latest version


1.11.140
========

* api-change:``rekognition``: Update rekognition command to latest version


1.11.139
========

* api-change:``appstream``: Update appstream command to latest version


1.11.138
========

* api-change:``ssm``: Update ssm command to latest version


1.11.137
========

* api-change:``route53``: Update route53 command to latest version
* enhancement:Cloudformation: Add `--role-arn` and `--notification-arns` parameters to cloudformation deploy.
* api-change:``firehose``: Update firehose command to latest version


1.11.136
========

* api-change:``gamelift``: Update gamelift command to latest version


1.11.135
========

* api-change:``ec2``: Update ec2 command to latest version


1.11.134
========

* api-change:``batch``: Update batch command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``mgh``: Update mgh command to latest version
* api-change:``glue``: Update glue command to latest version


1.11.133
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version


1.11.132
========

* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.11.131
========

* api-change:``rds``: Update rds command to latest version


1.11.130
========

* bugfix:s3: Fixed bug causing progress to not display if unicode characters appeared in the path. Fixes `#2738 <https://github.com/aws/aws-cli/issues/2738>`__.
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


1.11.129
========

* api-change:``config``: Update config command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``ses``: Update ses command to latest version


1.11.128
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``inspector``: Update inspector command to latest version


1.11.127
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version


1.11.126
========

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


1.11.125
========

* api-change:``clouddirectory``: Update clouddirectory command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version


1.11.124
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.11.123
========

* api-change:``emr``: Update emr command to latest version


1.11.122
========

* api-change:``budgets``: Update budgets command to latest version


1.11.121
========

* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``lambda``: Update lambda command to latest version


1.11.120
========

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``discovery``: Update discovery command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* bugfix:Cloudformation: Fix a bug causing json templates containing tabs to fail to parse. Fixes `#2663 <https://github.com/aws/aws-cli/issues/2663>`__.


1.11.119
========

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.11.118
========

* bugfix:Aliases: Properly quote alias parameters that have spaces in them. Fixes `#2653 <https://github.com/aws/aws-cli/issues/2653>`__.
* api-change:``swf``: Update swf command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* enhancement:Cloudformation: Reduce polling delay for `cloudformation deploy`.


1.11.117
========

* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ds``: Update ds command to latest version


1.11.116
========

* api-change:``route53``: Update route53 command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.11.115
========

* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``s3``: Update s3 command to latest version


1.11.114
========

* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``ssm``: Update ssm command to latest version


1.11.113
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version


1.11.112
========

* api-change:``lambda``: Update lambda command to latest version


1.11.111
========

* api-change:``route53``: Update route53 command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``dms``: Update dms command to latest version


1.11.110
========

* api-change:``ssm``: Update ssm command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``dax``: Update dax command to latest version


1.11.109
========

* api-change:``workdocs``: Update workdocs command to latest version


1.11.108
========

* bugfix:``s3 rm``: Remove unnecessary HeadObject call for non-recursive ``s3 rm``. This caused errors when a remote S3 object was encrypted with SSE-C as HeadObject call requires the SSE-C key but DeleteObject does not (`#2494 <https://github.com/aws/aws-cli/issues/2494>`__)
* api-change:``organizations``: Update organizations command to latest version


1.11.107
========

* api-change:``xray``: Update xray command to latest version


1.11.106
========

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.105
========

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.11.104
========

* api-change:``config``: Update config command to latest version


1.11.103
========

* api-change:``rds``: Update rds command to latest version


1.11.102
========

* api-change:``opsworks``: Update opsworks command to latest version


1.11.101
========

* api-change:``rekognition``: Update rekognition command to latest version
* enhancement:cloudformation: Added support for S3 HTTPS urls.
* api-change:``iot``: Update iot command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


1.11.100
========

* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


1.11.99
=======

* api-change:``iot``: Update iot command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


1.11.98
=======

* api-change:``appstream``: Update appstream command to latest version
* api-change:``iot``: Update iot command to latest version


1.11.97
=======

* api-change:``kinesisanalytics``: Update kinesisanalytics command to latest version
* api-change:``workdocs``: Update workdocs command to latest version


1.11.96
=======

* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version


1.11.95
=======

* api-change:``rds``: Update rds command to latest version


1.11.94
=======

* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.11.93
=======

* api-change:``appstream``: Update appstream command to latest version
* api-change:``rekognition``: Update rekognition command to latest version


1.11.92
=======

* api-change:``iam``: Update iam command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version


1.11.91
=======

* api-change:``dms``: Update dms command to latest version
* enhancement:``ecr``: Add ``--include-email/--no-include-email`` to the ``get-login`` command.


1.11.90
=======

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version


1.11.89
=======

* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``athena``: Update athena command to latest version


1.11.88
=======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``logs``: Update logs command to latest version


1.11.87
=======

* api-change:``kms``: Update kms command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``inspector``: Update inspector command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version


1.11.86
=======

* api-change:``ssm``: Update ssm command to latest version


1.11.85
=======

* api-change:``organizations``: Update organizations command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``elb``: Update elb command to latest version
* api-change:``lex-models``: Update lex-models command to latest version


1.11.84
=======

* api-change:``codestar``: Update codestar command to latest version
* api-change:``workspaces``: Update workspaces command to latest version


1.11.83
=======

* api-change:``ecs``: Update ecs command to latest version
* api-change:``marketplace-entitlement``: Update marketplace-entitlement command to latest version
* bugfix:``s3``: Fixed possible security issue where files could be downloaded to a directory outside the destination directory if the key contained relative paths when downloading files recursively.
* api-change:``lambda``: Update lambda command to latest version


1.11.82
=======

* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``snowball``: Update snowball command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version


1.11.81
=======

* api-change:``rds``: Update rds command to latest version
* enhancement:rds: Add command to generate IAM database auth tokens.


1.11.80
=======

* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``appstream``: Update appstream command to latest version


1.11.79
=======

* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version
* api-change:``route53domains``: Update route53domains command to latest version


1.11.78
=======

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``codestar``: Update codestar command to latest version


1.11.77
=======

* api-change:``lambda``: Update lambda command to latest version
* bugfix:configure: Properly use the default profile in ``configure get``


1.11.76
=======

* api-change:``opsworks``: Update opsworks command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``gamelift``: Update gamelift command to latest version


1.11.75
=======

* api-change:``redshift``: Update redshift command to latest version


1.11.74
=======

* api-change:``elbv2``: Update elbv2 command to latest version


1.11.73
=======

* api-change:``elasticache``: Update elasticache command to latest version


1.11.72
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version


1.11.71
=======

* api-change:``lex-runtime``: Update lex-runtime command to latest version


1.11.70
=======

* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.11.69
=======

* api-change:``config``: Update config command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


1.11.68
=======

* bugfix:ec2: Fixed a bug causing some ec2 commands to fail with an invalid parameter combination error when arguments were supplied via --cli-input-json. Resolves `#2452 <https://github.com/aws/aws-cli/issues/2452>`__
* api-change:``batch``: Update batch command to latest version
* api-change:``ec2``: Update ec2 command to latest version


1.11.67
=======

* api-change:``ssm``: Update ssm command to latest version


1.11.66
=======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version


1.11.65
=======

* api-change:``discovery``: Update discovery command to latest version
* api-change:``lambda``: Update lambda command to latest version


1.11.64
=======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version


1.11.63
=======

* api-change:``events``: Update events command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version


1.11.62
=======

* api-change:``events``: Update events command to latest version
* api-change:``devicefarm``: Update devicefarm command to latest version


1.11.61
=======

* api-change:``emr``: Update emr command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version


1.11.60
=======

* api-change:``clouddirectory``: Update clouddirectory command to latest version
* api-change:``apigateway``: Update apigateway command to latest version


1.11.59
=======

* api-change:``organizations``: Update organizations command to latest version
* api-change:``workdocs``: Update workdocs command to latest version


1.11.58
=======

* api-change:``rds``: Update rds command to latest version


1.11.57
=======

* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version


1.11.56
=======

* api-change:``mturk``: Update mturk command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``iam``: Update iam command to latest version


1.11.55
=======

* api-change:``es``: Update es command to latest version


1.11.54
=======

* bugfix:cloudformation: Fixes awslabs/serverless-application-model`#93 <https://github.com/aws/aws-cli/issues/93>`__
* api-change:``ec2``: Update ec2 command to latest version


1.11.53
=======

* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``clouddirectory``: Update clouddirectory command to latest version


1.11.52
=======

* api-change:``ec2``: Update ec2 command to latest version


1.11.51
=======

* api-change:``directconnect``: Update directconnect command to latest version


1.11.50
=======

* api-change:``config``: Update config command to latest version
* api-change:``cognito-identity``: Update cognito-identity command to latest version


1.11.49
=======

* feature:``kms``: Update kms command to latest version


1.11.48
=======

* feature:``ec2``: Update ec2 command to latest version


1.11.47
=======

* feature:``clouddirectory``: Update clouddirectory command to latest version
* feature:``lex-runtime``: Update lex-runtime command to latest version
* feature:``storagegateway``: Update storagegateway command to latest version


1.11.46
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``rekognition``: Update rekognition command to latest version


1.11.45
=======

* feature:``lex-runtime``: Update lex-runtime command to latest version


1.11.44
=======

* feature:``clouddirectory``: Update clouddirectory command to latest version
* feature:Configuration: Adds a new option to the configuration file 'cli_timestamp_format' to change the timestamp output format displayed by the CLI.
* feature:``ec2``: Update ec2 command to latest version
* feature:``codedeploy``: Update codedeploy command to latest version
* feature:``rds``: Update rds command to latest version


1.11.43
=======

* feature:``elbv2``: Update elbv2 command to latest version
* feature:``rds``: Update rds command to latest version


1.11.42
=======

* feature:``codecommit``: Update codecommit command to latest version
* feature:``ecs``: Update ecs command to latest version
* feature:``codebuild``: Update codebuild command to latest version


1.11.41
=======

* feature:``acm``: Update acm command to latest version
* feature:``health``: Update health command to latest version


1.11.40
=======

* feature:``ec2``: Update ec2 command to latest version


1.11.39
=======

* feature:``rds``: Update rds command to latest version


1.11.38
=======

* feature:``dynamodb``: Update dynamodb command to latest version
* feature:``polly``: Update polly command to latest version
* feature:``glacier``: Update glacier command to latest version
* feature:``route53``: Update route53 command to latest version
* feature:``rekognition``: Update rekognition command to latest version


1.11.37
=======

* feature:``cur``: Update cur command to latest version
* bugfix:``cloudformation deploy``: ``deploy`` command must not override parameters with default values
* feature:``dynamodb``: Update dynamodb command to latest version
* bug:``cloudformation package``: Only generate S3BodyLocation when needed `#2320 <https://github.com/aws/aws-cli/issues/2320>`__
* feature:``elasticache``: Update elasticache command to latest version
* feature:``config``: Update config command to latest version
* bugfix:``cloudformation``: Fix yaml parsing error for ``!GetAtt`` `#2332 <https://github.com/aws/aws-cli/issues/2332>`__
* bugfix:``cloudformation package``: ``package`` command must use Path-style S3 URL when packaging AWS


1.11.36
=======

* feature:``config``: Update config command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``efs``: Update efs command to latest version
* feature:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* feature:``lambda``: Update lambda command to latest version
* feature:``dynamodbstreams``: Update dynamodbstreams command to latest version
* feature:``rekognition``: Update rekognition command to latest version
* feature:``iam``: Update iam command to latest version


1.11.35
=======

* feature:``codedeploy``: Update codedeploy command to latest version
* bugfix:s3: Catch and warn on overflow errors when getting a file stat.
* feature:``ecs``: Update ecs command to latest version


1.11.34
=======

* feature:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* feature:``ds``: Update ds command to latest version
* feature:``iam``: Update iam command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``apigateway``: Update apigateway command to latest version


1.11.33
=======

* feature:``rds``: Update rds command to latest version
* feature:``ecr``: Update ecr command to latest version


1.11.32
=======

* feature:``storagegateway``: Update storagegateway command to latest version
* feature:``firehose``: Update firehose command to latest version
* feature:``route53``: Update route53 command to latest version


1.11.31
=======

* feature:``cognito-identity``: Update cognito-identity command to latest version
* feature:``inspector``: Update inspector command to latest version
* feature:``cloudformation``: Update cloudformation command to latest version
* feature:``sqs``: Update sqs command to latest version
* feature:``discovery``: Update discovery command to latest version


1.11.30
=======

* feature:``ssm``: Update ssm command to latest version
* feature:``cognito-idp``: Update cognito-idp command to latest version


1.11.29
=======

* feature:``batch``: Update batch command to latest version
* feature:``logs``: Update logs command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``dms``: Update dms command to latest version
* feature:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* feature:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* feature:``sts``: Update sts command to latest version


1.11.28
=======

* feature:cloudfront: Add lambda function associations to cache behaviors.
* feature:rds: Add cluster create data to DBCluster APIs.
* bugfix:opsworks: This fixes an issue with opsworks register --local and python3 on some versions of linux.
* feature:waf-regional: With this new feature, customers can use AWS WAF directly on Application Load Balancers in a VPC within available regions to protect their websites and web services from malicious attacks such as SQL injection, Cross Site Scripting, bad bots, etc.


1.11.27
=======

* feature:``config``: Update config command to latest version
* feature:``sqs``: Update sqs command to latest version
* feature:``s3``: Update s3 command to latest version


1.11.26
=======

* feature:``sts``: Update sts command to latest version
* feature:``config``: Update config command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:``pinpoint``: Update pinpoint command to latest version


1.11.25
=======

* bugfix:opsworks-cm: Rename opsworkscm to opsworks-cm, keeping support for opsworkscm.


1.11.24
=======

* feature:``pinpoint``: Update pinpoint command to latest version
* feature:``lambda``: Update lambda command to latest version
* feature:``directconnect``: Update directconnect command to latest version
* feature:alias: Add ability to alias commands in the CLI
* feature:``xray``: Update xray command to latest version
* feature:``s3``: Display transfer speed for s3 commands
* feature:``ssm``: Update ssm command to latest version
* feature:``apigateway``: Update apigateway command to latest version
* feature:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* feature:``codebuild``: Update codebuild command to latest version
* feature:``opsworkscm``: Update opsworkscm command to latest version
* feature:``shield``: Update shield command to latest version
* feature:``stepfunctions``: Update stepfunctions command to latest version
* feature:``appstream``: Update appstream command to latest version
* feature:``health``: Update health command to latest version
* feature:``ec2``: Update ec2 command to latest version


1.11.23
=======

* feature:``polly``: Update polly command to latest version
* feature:``snowball``: Update snowball command to latest version
* feature:``rekognition``: Update rekognition command to latest version
* feature:``lightsail``: Update lightsail command to latest version
* feature:``--generate-cli-skeleton output``: Add support for generating sample output for command


1.11.22
=======

* feature:``s3``: Update s3 command to latest version


1.11.21
=======

* feature:``s3``: Update s3 command to latest version
* feature:``glacier``: Update glacier command to latest version
* feature:``cloudformation``: Update cloudformation command to latest version
* feature:``route53``: Update route53 command to latest version


1.11.20
=======

* feature:``ecs``: Update ecs command to latest version
* feature:``cloudtrail``: Update cloudtrail command to latest version


1.11.19
=======

* feature:``cloudformation deploy``: Add command to simplify deployments of cloudformation stack changes.
* feature:``emr``: Update emr command to latest version
* feature:``lambda``: Update lambda command to latest version
* feature:``elastictranscoder``: Update elastictranscoder command to latest version
* feature:``cloudformation package``: Add command to package source code for cloudfromation template.
* feature:``gamelift``: Update gamelift command to latest version
* feature:``application-autoscaling``: Update application-autoscaling command to latest version


1.11.18
=======

* bugfix:Powershell: Properly set return code on Powershell.
* feature:``cloudwatch``: Update cloudwatch command to latest version
* feature:``sqs``: Update sqs command to latest version
* feature:``apigateway``: Update apigateway command to latest version
* feature:``meteringmarketplace``: Update meteringmarketplace command to latest version


1.11.17
=======

* feature:``route53``: Update route53 command to latest version
* feature:``servicecatalog``: Update servicecatalog command to latest version


1.11.16
=======

* feature:``kinesis``: Update kinesis command to latest version
* feature:``ds``: Update ds command to latest version
* feature:``elasticache``: Update elasticache command to latest version


1.11.15
=======

* feature:``cognito-idp``: Update cognito-idp command to latest version


1.11.14
=======

* feature:``cloudformation``: Update cloudformation command to latest version
* feature:``logs``: Update logs command to latest version


1.11.13
=======

* feature:``directconnect``: Update directconnect command to latest version


1.11.12
=======

* feature:``ses``: Update ses command to latest version


1.11.11
=======

* bugfix:``cloudtrail``: Use STS instead of IAM in CreateSubscription
* feature:``cloudformation``: Update cloudformation command to latest version


1.11.10
=======

* feature:``autoscaling``: Update autoscaling command to latest version
* feature:``elbv2``: Update elbv2 command to latest version


1.11.9
======

* feature:``ecs``: Update ecs command to latest version
* feature:``sms``: Update sms command to latest version


1.11.8
======

* feature:``waf``: Update waf command to latest version
* feature:s3: Port mv to s3transfer.
* feature:``budgets``: Update budgets command to latest version


1.11.7
======

* feature:``cloudfront``: Update cloudfront command to latest version
* feature:``iot``: Update iot command to latest version
* feature:``config``: Update config command to latest version
* feature:``kinesisanalytics``: Update kinesisanalytics command to latest version
* feature:``rds``: Update rds command to latest version


1.11.6
======

* feature:``route53``: Update route53 command to latest version
* feature:``--region``: Add support for us-east-2


1.11.5
======

* bugfix:``s3 sync --delete``: Fix regression where ``--delete`` would not delete local files


1.11.4
======

* feature:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* feature:``gamelift``: Update gamelift command to latest version
* feature:``s3``: Integrate sync command with s3transfer
* feature:``acm``: Update acm command to latest version
* feature:``s3``: Output progress even when discovering new files to transfer


1.11.3
======

* bugfix:Pagination: Fix validation error when providing ``--no-paginate`` with normalized paging argument.
* feature:``apigateway``: Update apigateway command to latest version
* feature:``cloudfront``: Update cloudfront command to latest version
* feature:``gamelift``: Update gamelift command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``codedeploy``: Update codedeploy command to latest version
* feature:``sns``: Update sns command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``elasticache``: Update elasticache command to latest version
* feature:``ecr``: Update ecr command to latest version


1.11.2
======

* feature:``s3``: Update s3 command to latest version
* feature:``waf``: Update waf command to latest version
* feature:``devicefarm``: Update devicefarm command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``opsworks``: Update opsworks command to latest version
* bugfix:s3: Refactor rb into its own command. In addition, validate that no key is supplied regardless of whether or not the force argument is supplied.
* bugfix:route53domains: Rename `--end` to `--end-time` to fix a bug relating to argparse prefix expansion. Alias `--start` to `--start-time` to maintain a consistent interface while keeping the old parameter.
* feature:``cognito-idp``: Update cognito-idp command to latest version


1.11.1
======

* bugfix:``s3``: Fix regression when downloading empty files.


1.11.0
======

* feature:``snowball``: Update snowball command to latest version
* feature:``s3``: Update s3 command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:s3: Port cp and rm to s3transfer. Improve progress for those commands, showing byte progress.


1.10.67
=======

* feature:``codepipeline``: Update codepipeline command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``efs``: Update efs command to latest version
* feature:``cloudformation``: Update cloudformation command to latest version


1.10.66
=======

* feature:``codedeploy``: Update codedeploy command to latest version
* feature:``emr``: Update emr command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``redshift``: Update redshift command to latest version


1.10.65
=======

* feature:``iot``: Update iot command to latest version
* feature:``rds``: Update rds command to latest version


1.10.64
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``servicecatalog``: Update servicecatalog command to latest version


1.10.63
=======

* feature:``sns``: Update sns command to latest version
* feature:``support``: Update support command to latest version
* feature:``cloudfront``: Update cloudfront command to latest version


1.10.62
=======

* feature:``ecr``: Update ecr command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:``codepipeline``: Update codepipeline command to latest version
* feature:``sns``: Update sns command to latest version


1.10.61
=======

* feature:``cognito-idp``: Update cognito-idp command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``application-autoscaling``: Update application-autoscaling command to latest version
* feature:``gamelift``: Update gamelift command to latest version
* feature:``config``: Update config command to latest version
* bugfix:``s3``: Fix issue where setting ``addressing_style`` and ``use_accelerate_endpoint`` in your config file would cause ``aws s3`` commands using S3 streams to fail (`#2146 <https://github.com/aws/aws-cli/issues/2146>`__)


1.10.60
=======

* feature:``route53``: Update route53 command to latest version
* feature:``codepipeline``: Update codepipeline command to latest version
* feature:``autoscaling``: Update autoscaling command to latest version
* feature:``ssm``: Update ssm command to latest version
* bugfix:ec2: Set MaxResults to 1000 by default for DescribeSnapshots and DescribeVolumes.
* feature:``cloudfront``: Update cloudfront command to latest version


1.10.59
=======

* feature:``opsworks``: Update opsworks command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``s3``: Add a new ``aws s3 presign`` command, closes `#462 <https://github.com/aws/aws-cli/issues/462>`__


1.10.58
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``workspaces``: Update workspaces command to latest version
* feature:``iam``: Update iam command to latest version


1.10.57
=======

* feature:``ecs``: Update ecs command to latest version
* feature:``apigateway``: Update apigateway command to latest version
* feature:``acm``: Update acm command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``elbv2``: Update elbv2 command to latest version


1.10.55
=======

* feature:``s3``: Add support for dualstack configuration
* feature:``ecs``: Update ecs command to latest version
* feature:``autoscaling``: Update autoscaling command to latest version
* feature:``elbv2``: Update elbv2 command to latest version
* feature:``kms``: Update kms command to latest version
* feature:``kinesisanalytics``: Update kinesisanalytics command to latest version
* feature:``snowball``: Update snowball command to latest version
* feature:``elb``: Update elb command to latest version


1.10.54
=======

* feature:``ecr``: Update ecr command to latest version
* feature:``cloudfront``: Update cloudfront command to latest version
* feature:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version


1.10.53
=======

* feature:``lambda``: Update lambda command to latest version
* feature:``gamelift``: Update gamelift command to latest version
* feature:``rds``: Update rds command to latest version


1.10.52
=======

* feature:``rds``: Update rds command to latest version
* feature:``route53domains``: Update route53domains command to latest version
* feature:``cloudwatch``: Update cloudwatch command to latest version
* feature:``machinelearning``: Update machinelearning command to latest version
* feature:``meteringmarketplace``: Update meteringmarketplace command to latest version
* feature:``iot``: Update iot command to latest version
* feature:``application-autoscaling``: Update application-autoscaling command to latest version
* feature:``emr``: Update emr command to latest version
* feature:``ds``: Update ds command to latest version
* feature:``logs``: Update logs command to latest version


1.10.51
=======

* feature:``sts``: Update sts command to latest version
* feature:``ds``: Update ds command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:``es``: Update es command to latest version
* feature:``apigateway``: Update apigateway command to latest version
* feature:``cognito-idp``: Update cognito-idp command to latest version
* feature:``ses``: Update ses command to latest version


1.10.50
=======

* feature:``iot``: Update iot command to latest version
* feature:``s3``: Update s3 command to latest version


1.10.49
=======

* feature:``cloudformation``: Update cloudformation command to latest version
* feature:``elastictranscoder``: Update elastictranscoder command to latest version
* feature:``config``: Update config command to latest version
* feature:``application-autoscaling``: Update application-autoscaling command to latest version
* feature:``acm``: Update acm command to latest version


1.10.48
=======

* feature:``devicefarm``: Update devicefarm command to latest version
* feature:``ssm``: Update ssm command to latest version
* bugfix:emr: Fixes a bug in exception handling which was causing create-default-roles to break.


1.10.47
=======

* feature:Credential Provider: Add support for ECS metadata credential provider.
* feature:``dms``: Update dms command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``efs``: Remove preview status from ``aws efs`` command
* feature:``ecs``: Update ecs command to latest version


1.10.46
=======

* feature:``config``: Update config command to latest version
* feature:``ds``: Update ds command to latest version
* feature:``opsworks``: Update opsworks command to latest version
* feature:``servicecatalog``: Update servicecatalog command to latest version


1.10.45
=======

* feature:``iam``: Update iam command to latest version
* feature:``codepipeline``: Update codepipeline command to latest version
* feature:``efs``: Update efs command to latest version


1.10.44
=======

* feature:``ssm``: Update ssm command to latest version
* feature:``dms``: Update dms command to latest version


1.10.43
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``gamelift``: Update gamelift command to latest version
* feature:``efs``: Update efs command to latest version
* feature:``iot``: Update iot command to latest version
* feature:``route53``: Update route53 command to latest version
* feature:``sns``: Update sns command to latest version


1.10.42
=======

* feature:``s3``: Update s3 command to latest version


1.10.41
=======

* feature:``iam``: Update iam command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``cognito-identity``: Update cognito-identity command to latest version
* feature:``directconnect``: Update directconnect command to latest version


1.10.40
=======

* bugfix:AssumeRole: Fix regression in assume role where cached credentials were not valid JSON (`botocore #962 <https://github.com/boto/botocore/pull/962>`__)


1.10.39
=======

* feature:``codepipeline``: Update codepipeline command to latest version
* feature:opsworks: Instead of always creating an IAM user for instance registration, allow using credentials from the instance profile
* feature:``opsworks``: Update opsworks command to latest version


1.10.38
=======

* feature:``acm``: Update acm command to latest version
* feature:``ses``: Update ses command to latest version
* feature:``rds``: Update rds command to latest version
* feature:``cloudtrail``: Update cloudtrail command to latest version


1.10.37
=======

* feature:``s3``: Update s3 command to latest version


1.10.36
=======

* feature:``dynamodbstreams``: Update dynamodbstreams command to latest version
* feature:``machinelearning``: Update machinelearning command to latest version
* feature:``iot``: Update iot command to latest version
* bugfix:Pagination: Fix regression with --no-paginate introduced in `#1958 <https://github.com/aws/aws-cli/issues/1958>`__ (fixes `#1993 <https://github.com/aws/aws-cli/issues/1993>`__)


1.10.35
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``application-autoscaling``: Update application-autoscaling command to latest version


1.10.34
=======

* feature:``elasticache``: Update elasticache command to latest version


1.10.33
=======

* feature:``rds``: Update rds command to latest version
* feature:``ec2``: Update ec2 command to latest version
* bugfix:help: Write help content to stdout if less is not installed. Fixes `#1957 <https://github.com/aws/aws-cli/issues/1957>`__


1.10.32
=======

* feature:``firehose``: Update firehose command to latest version
* bugfix:Table: Fix rendering of tables with double-width characters.
* feature:``ec2``: Update ec2 command to latest version
* feature:``ecs``: Update ecs command to latest version


1.10.31
=======

* feature:``application-autoscaling``: Adds support for Application Auto Scaling. Application Auto Scaling is a general purpose Auto Scaling service for supported elastic AWS resources. With Application Auto Scaling, you can automatically scale your AWS resources, with an experience similar to that of Auto Scaling.


1.10.29
=======

* feature:``dynamodb``: Update dynamodb command to latest version
* bugfix:Shorthand: Remove back-compat shorthand features from new services.
* bugfix:Paginator: Print a better error when pagination params are supplied along with no-paginate.
* bugfix:ec2: Sets MaxResults to default value of 1000.
* feature:``workspaces``: Update workspaces command to latest version
* feature:``discovery``: Update discovery command to latest version


1.10.28
=======

* feature:``ec2``: Update ec2 command to latest version
* feature:``ssm``: Update ssm command to latest version
* feature:``discovery``: Update discovery command to latest version
* feature:``cloudformation``: Update cloudformation command to latest version


1.10.27
=======

* feature:``storagegateway``: Update storagegateway command to latest version
* feature:``directconnect``: Update directconnect command to latest version
* feature:``emr``: Update emr command to latest version
* feature:``sqs``: Update sqs command to latest version
* feature:``iam``: Update iam command to latest version


1.10.26
=======

* feature:``kms``: Update kms command to latest version
* feature:``sts``: Update sts command to latest version
* feature:``apigateway``: Update apigateway command to latest version
* feature:``ecs``: Update ecs command to latest version
* feature:``s3``: Update s3 command to latest version
* feature:``cloudtrail``: Update cloudtrail command to latest version


1.10.25
=======

* feature:``inspector``: Update inspector command to latest version
* feature:``codepipeline``: Update codepipeline command to latest version
* bugfix:Configure: Fix issue causing prompts not to display on mintty. Fixes `#1925 <https://github.com/aws/aws-cli/issues/1925>`__
* feature:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


1.10.24
=======

* feature:``route53domains``: Update route53domains command to latest version
* feature:``opsworks``: Update opsworks command to latest version


1.10.23
=======

* feature:``ecr``: Update ecr command to latest version
* feature:``acm``: Update acm command to latest version
* feature:``ec2``: Update ec2 command to latest version
* feature:``sts``: Update sts command to latest version
* feature:``cognito-idp``: Update cognito-idp command to latest version


1.10.22
=======

* feature:emr: Add support for smart targeted resize feature
* feature:iot: Add SQL RulesEngine version support
* feature:acm: Add tagging support for ACM


1.10.21
=======

* feature:``aws ec2``: Add support for two new EBS volume types
* feature:``aws cognito-idp``: Add support for new service, ``aws cognito-idp``
* feature:``aws kinesis``: Update ``aws kinesis`` command to latest version
* feature:``aws elasticbeanstalk``: Add support for automatic platform version upgrades with managed updates
* feature:``aws devicefarm``: Update ``aws devicefarm`` command to latest version
* feature:``aws s3``: Add support for Amazon S3 Transfer Acceleration
* feature:``aws firehose``: Update ``firehose`` command to latest version


1.10.20
=======

* feature:``iot``: Add commands for managing CA certificates.
* bugfix:``ec2 wait``: Fix issues with waiting on incorrect error code.
* bugfix:``s3``: Fix issue where multipart uploads were not being properly aborted after Cntrl-C. (`issue 1905 <https://github.com/aws/aws-cli/pull/1905>`__)


1.10.19
=======

* feature:``lambda``: Added support for setting the function runtime as nodejs4.3, as well as updating function configuration to set the runtime.
* feature:``ds``: Added support for Directory Service Conditional Forwarder APIs.
* feature:``elasticbeanstalk``: Adds support for three additional elements in AWS Elasticbeanstalk's DescribeInstancesHealthResponse: Deployment, AvailabilityZone, and InstanceType. Additionally adds support for increased EnvironmentName length from 23 to 40.
* bugfix:Paginator: Allow non-specified input tokens in old starting token format.


1.10.18
=======

* feature:``apigateway``: Added support for API Import
* feature:``route53``: Added support for metric-based health checks and regional health checks.
* feature:``sts``: Added support for GetCallerIdentity, which returns details about the credentials used to make the API call. The details include name and account, as well as the type of entity making the call, such as an IAM user vs. federated user.
* feature:``s3api``: Added support for VersionId in PutObjectAcl (`issue 856 <https://github.com/boto/botocore/pull/856>`__)
* bugfix:``s3api``: Add validation to enforce S3 metadata only contains ASCII. (`issue 861 <https://github.com/boto/botocore/pull/861>`__)
* bugfix:Exceptions: Consistently parse errors with no body (`issue 859 <https://github.com/boto/botocore/pull/859>`__)
* bugfix:Config: Handle case where S3 config key is not a dict (`issue 858 <https://github.com/boto/botocore/pull/858>`__)


1.10.17
=======

* feature:``acm``: Update command to latest version
* feature:``cloudformation``: Update command to latest version
* feature:``codedeploy``: Update command to latest version
* feature:``dms``: Update command to latest version
* feature:``elasticache``: Update command to latest version
* feature:``elasticbeanstalk``: Update command to latest version
* feature:``redshift``: Update command to latest version
* feature:``waf``: Update command to latest version
* bugfix:Pagintor: Fix regression when providing a starting token for a paginated command (`botocore issue 849 <https://github.com/boto/botocore/pull/849>`__)
* bugfix:Response Parsing: Handle case when generic HTML error response is received (`botocore issue 850 <https://github.com/boto/botocore/pull/850>`__)
* bugfix:Request serialization: Handle case when non str values are provided for header values when using signature version 4 (`botocore issue 852 <https://github.com/boto/botocore/pull/852>`__)
* bugfix:Retry: Retry HTTP responses with status code 502 (`botocore issue 853 <https://github.com/boto/botocore/pull/853>`__)
* bugfix:``ec2 run-instances``: Fix issue when providing ``--secondary-private-ip-address-count`` argument (`issue 1874 <https://github.com/aws/aws-cli/pull/1874>`__)


1.10.16
=======

* feature:``elasticache``: Update command to latest version
* feature:``rds``: Update command to latest version
* feature:``storagegateway``: Update command to latest version


1.10.15
=======

* feature:``aws devicefarm``: Add support to pay a flat monthly fee for unlimited testing of your Android and iOS apps with AWS Device Farm device slots
* feature:``aws rds``: Add support for customizing the order in which Aurora Replicas are promoted to primary instance during a failover


1.10.14
=======

* feature:``meteringmarketplace``: The AWS Marketplace Metering Service enables sellers to price their products along new pricing dimensions. After a integrating their product with the AWS Marketplace Metering Service, that product will emit an hourly record capturing the usage of any single pricing dimension. Buyers can easily subscribe to software priced by this new dimension on the AWS Marketplace website and only pay for what they use.
* feature:``s3api``: Added support for delete marker and abort multipart upload lifecycle configuration.
* feature:``iot``: Added support for Amazon Elasticsearch Service and Amazon Cloudwatch actions for the AWS IoT rules engine.
* feature:``cloudhsm``: Added support for tagging resources.


1.10.13
=======

* feature:``DMS``: Added support for AWS Database Migration Service
* feature:``SES``: Added support for white-labeling
* feature:``CodeDeploy``: Added support for BatchGetDeploymentGroups
* feature:``endpoints``: Updated endpoints to latest version
* bugfix:``groff``: Fix groff command which was causing issues on some systems
* bugfix:``shorthand``: Allow ``#`` in keys in the shorthand parser


1.10.12
=======

* feature:``gamelift``: Update command to latest version
* feature:``iam``: Update command to latest version
* feature:``redshift``: Update command to latest version


1.10.11
=======

* feature:``acm``: Update ``acm`` command to latest version
* feature:``codecommit``: Update ``codecommit`` model to latest version
* feature:``config``: Update ``config`` command to latest version
* feature:``devicefarm``: Update ``devicefarm`` command to latest version
* feature:``directconnect``: Update ``directconnect`` command to latest version
* feature:``events``: Update ``events`` command to latest version
* bugfix:``aws s3 cp``: Add error checking when attempting recursive copies or syncs with streaming output (`issue 1771 <https://github.com/aws/aws-cli/issues/1771>`__)


1.10.10
=======

* feature:``aws ds``: Add support for SNS event notifications.
* bugfix:``aws s3 rb``: Fix issue where bucket is still attempted to be removed when the preceding delete requests failed. (`issue 1827 <https://github.com/aws/aws-cli/pull/1827>`__)
* bugfix:``aws storagegateway``: Fix issue in aliasing required args. (`issue 1790 <https://github.com/aws/aws-cli/issues/1790>`__)


1.10.9
======

* feature:``aws dynamodb``: Add support for describing limits.
* feature:``aws apigateway``: Add support for testing invoke authorizers and flushing stage authorizers cache.
* feature:``aws cloudsearchdomain``: Add support for new stat fields.


1.10.8
======

* bugfix:``aws s3``: Disable use of MD5 when SHA256 checksum is already calculated for the body (`botocore issue 804 <https://github.com/boto/botocore/pull/804>`__)
* bugfix:FIPS: Handle case where MD5 cipher is not available on FIPS compliant systems (`botocore issue 807 <https://github.com/boto/botocore/pull/807>`__)
* feature:``aws cloudformation``: Update AWS CloudFormation command to the latest version
* feature:``aws logs``: Update Amazon CloudWatch Logs command to the latest version
* feature:``aws ses``: Update Amazon SES to the latest version
* feature:``aws autoscaling``: Update Auto Scaling to the latest version


1.10.7
======

* bug:``aws configure set``: Fix issue when adding entries to an empty profile section (`issue 1806 <https://github.com/aws/aws-cli/pull/1806>`__)
* feature:``aws route53``: Add suport for SNI health checks


1.10.6
======

* feature:``aws codedeploy``: Added support for setting up triggers for a deployment group.
* bugfix:``aws emr``: Fix missing dns name issue with private clusters. (`issue 1749 <https://github.com/aws/aws-cli/pull/1749>`__)
* bugfix:``aws emr``: Fix issue where impala args were not joined with commas. (`issue 1802 <https://github.com/aws/aws-cli/pull/1802>`__)


1.10.5
======

* feature:``aws rds``: Added support for Cross-account Encrypted (KMS) snapshot sharing.
* feature:``aws emr``: Added support for adding EBS storage to EMR instances.
* bugfix:pagination: Fixed a bug that was causing non-string service tokens to fail on serialization


1.10.4
======

* feature:``aws apigateway``: Add support for custom request authorizers.


1.10.3
======

* feature:``aws marketplacecommerceanalytics generate-data-set``:  Add support for --customer-defined-values parameter


1.10.2
======

* feature:``aws gamelift``: Add support for AWS GameLift
* bugfix:Assume Role: Fix issue where temporary credentials from assuming a role were not being properly cached (`issue 1684 <https://github.com/aws/aws-cli/issues/1684>`__)


1.10.1
======

* feature:``aws waf``: Add support for blocking, allowing, or monitoring (count) requests based on the content in HTTP request bodies.
* bugfix:``aws ssm``: Remove constraint on Amazon EC2 instance id's. (`issue 1729 <https://github.com/aws/aws-cli/issues/1729>`__)


1.10.0
======

* feature:``aws acm``: adds support for AWS Certificate Manager
* feature:``aws cloudfront``: adds support for AWS Certificate Manager certificates
* feature:``aws cloudfront create-distribution``: Adds support for --origin-domain-name and --default-root-object
* feature:``aws cloudfront update-distribution``: Adds support for --default-root-object
* feature:``aws iot``: adds support for topic rules
* feature:``aws cloudformation``: adds suport for ContinueUpdateRollback


1.9.21
======

* feature:``aws sts``: now returns RegionDisabledException instead of AccessDenied when a user sends an API request to an STS regional endpoint that is not activated for that AWS account. This enables customers to more easily decide how to respond, such as by trying to call a different region instead of simply failing the call.
* feature:``aws opsworks``: adds support for new enums.
* feature:``aws devicefarm``: adds support running Appium tests written in Python against your native, hybrid and browser-based apps on AWS Device Farm.


1.9.20
======

* bugfix:``aws cloudfront``: Fix regression in waiters.


1.9.19
======

* feature:``aws events``: Initial support for Amazon CloudWatch Events. CloudWatch Events allows you to track changes to your AWS resources with less overhead and greater efficiency.
* feature:``aws ec2``: Adds support for purchasing reserved capacity for specific blocks of time on a one-time of recurring basis.
* feature:``aws cloudfront``: Adds support for HTTPS-only connections, and control of edge-to-origin request headers.
* bugfix:``aws s3``: Gracefully handle encoding errors when printing S3 keys (`issue 1719 <https://github.com/boto/botocore/pull/1719>`__)


1.9.18
======

* feature:``aws ec2``: Add support for the new 63-bit EC2 Instance and Reservation IDs.


1.9.16
======

* feature:``aws datapipeline list-runs``: Add support for output format


1.9.15
======

* feature:``aws ecr``: Add ``aws ecr`` commands
* feature:``aws emr``: Update ``aws emr create-cluster`` to accept Amazon EC2 security group
* feature:``aws ecs``: Update ``ecs`` command to include a new deployment option


1.9.14
======

* feature:``aws configservice``: Support for IAM resource types
* feature:``aws cloudtrail``: Adds ``isMultiRegion`` to some of the commands
* feature:``aws cloudfront``: Adds support for gzip
* feature:``aws ec2``: Adds new commands for VPC Managed NAT


1.9.13
======

* bugfix:``aws``: Fix regression when using AWS_DATA_PATH environment variable (`issue 736 <https://github.com/boto/botocore/pull/736>`__)


1.9.12
======

* feature:``aws cloudfront create-invalidation``: Add a new --paths option. (`issue 1662 <https://github.com/aws/aws-cli/pull/1662>`__)
* feature:``aws cloudfront sign``: Add a new command to create a signed url. (`issue 1668 <https://github.com/aws/aws-cli/pull/1668>`__)
* feature:``aws autoscaling``: Added support for protecting instances from scale-in events.
* feature:``aws rds``: Added support for Aurora encryption at rest.


1.9.11
======

* feature:``aws rds``: Added support for specifying port number.
* feature:``aws ds``: Added support for Microsoft ActiveDirctory.
* feature:``aws route53``: Added support for TrafficFlow, a new management and modeling layer for Route53.
* feature:Timeouts: Added additonal options for configuring socket timeouts.


1.9.10
======

* feature:``aws config``: Added support for dedicated hosts.
* feature:``aws s3``: Added support for custom metadata in cp, mv, and sync.


1.9.9
=====

* feature:``aws s3api``: Added support for the aws-exec-read canned ACL on objects.
* feature:``aws elasticbeanstalk``: Added support for composable web applications.
* feature:``aws ec2``: Added support for EC2 dedicated hosts.
* feature:``aws ecs``: Added support for task stopped reasons and task start and stop times.


1.9.8
=====

* bugfix:``aws s3``: Fix regression when downloading a restored Glacier object (`issue 1650 <https://github.com/aws/aws-cli/pull/1650>__`)
* bugfix:``aws s3``: Fix issue when encountering "out of disk space" errors as well as permissions errors when downloading large files (`issue 1645 <https://github.com/aws/aws-cli/issues/1645>`__, `issue 1442 <https://github.com/aws/aws-cli/issues/1442>`__)
* bugfix:``aws opsworks register``: Support ``--no-verify-ssl`` argument for the ``aws opsworks register`` command (`issue 1632 <https://github.com/aws/aws-cli/pull/1632>`__)
* feature:``s3``: Add support for Server-Side Encryption with KMS and Server-Side Encryption with Customer-Provided Keys. (`issue 1623 <https://github.com/aws/aws-cli/pull/1623>`__)


1.9.7
=====

* bugfix:``memory management``: Resolve a potential memory leak when creating lots of clients on Python 2.6 and Linux 2.6
* bugfix:``presign url``: Now generate_presigned_url() works correctly with different expiry time


1.9.6
=====

* feature:``aws apigateway``: Support for stage variables to configure the different deployment stages


1.9.5
=====

* bugfix:``aws datapipeline create-default-roles``: Fix issue with error handling. (`issue 1618 <https://github.com/aws/aws-cli/pull/1618>`__)
* bugfix:``aws s3``: Skip glacier objects when downloading from S3. (`issue 1581 <https://github.com/aws/aws-cli/pull/1581>`__)
* feature:``aws s3api``: Auto-populate ``--copy-source-sse-customer-key-md5`` (`botocore issue 709 <https://github.com/boto/botocore/pull/709>`__)


1.9.4
=====

* feature:``aws devicefarm``: Add commands for updating and deleting projects, device pools, uploads, and runs.


1.9.2
=====

* bugfix:``aws s3``: Fix some local path validation issues (`issue 1575 <https://github.com/aws/aws-cli/pull/1575>`__)
* bugfix:``aws storagegateway``: Fix ``--tape-ar-ns``, ``--volume-ar-ns``, and ``--vtl-device-ar-ns`` to ``--tape-arns``, ``--volume-arns``, and ``--vtl-device-arns``, respectively.  The old arguments are still supported for backwards compatibility, but are no longer documented. (`issue 1599 <https://github.com/aws/aws-cli/pull/1599>`__)
* bugfix:``aws configservice subscribe``: Fix an issue when creating a new S3 bucket (`issue 1593 <https://github.com/aws/aws-cli/pull/1593>`__)
* bugfix:``aws apigateway put-integration``: Fix issue with ``--uri`` and ``--integration-http-method`` parameters (`issue 1605 <https://github.com/aws/aws-cli/issues/1605>`_)


1.9.1
=====

* feature:``aws apigateway``: Add support for Amazon API Gateway


1.9.0
=====

* feature:``aws iam``: Add policy simulator support
* feature:``aws autoscaling``: Add support for launch configurations that include encrypted Amazon Elastic Block Store (EBS) volumes
* feature:configure: Add support for ``ca_bundle`` config variable
* feature:Assume Role: Add ``role_session_name`` config variable to control the ``RoleSessionName`` when assuming roles (`issue 1389 <https://github.com/aws/aws-cli/pull/1389>`__)
* bug:Argument Parsing: Handle case when empty list parameter was specified with no value (`issue 838 <https://github.com/aws/aws-cli/issues/838>`__)


1.8.13
======

* feature:``aws deploy``: Compress zip files when using ``aws deploy push`` (`issue 1534 <https://github.com/aws/aws-cli/pull/1534>`--)
* bugfix:Shorthand Parser: Fix issue when display error message for multiline shorthand syntax values (`issue 1543 <https://github.com/aws/aws-cli/pull/1543>`__)
* bugfix:``aws route53``: Automatically retry Throttling and PriorRequestNotComplete errors (`botocore issue 682 <https://github.com/boto/botocore/pull/682>`__)
* feature:``aws s3/s3api``: Add support for changing the bucket addressing style (`botocore issue 673 <https://github.com/boto/botocore/pull/673>`__)
* bugfix:``aws s3api``: Add missing ``--server-side-encryption`` option to ``upload-part`` command
* feature:``aws kms``: Add ability to delete customer master keys (CMKs)


1.8.12
======

* feature:``aws iot-data``: Add support for AWS IoT Data Plane
* feature:``aws lambda``: Add support for aliasing and function versioning
* feature:``aws ecs``: Update commands


1.8.11
======

* feature:``aws firehose``: Add support for Amazon Kinesis Firehose
* feature:``aws inspector``: Add support for Amazon Inspector
* feature:``aws kinesis``: Add support for updating stream retention periods
* feature:``aws configservice``: Add support for config rules


1.8.10
======

* feature:``aws ec2``: Add support for spot blocks
* feature:``aws cloudfront``: Add support for adding Web ACLs to CloudFront distributions


1.8.9
=====

* feature:``aws cloudtrail``: Adds support for log file integrity validation, log encryption with AWS KMS-Managed Keys (SSE-KMS), and trail tagging.
* feature:``aws rds create-db-instance``: --db-instance-class has a new value as db.t2.large
* feature:``aws workspaces``: Adds support for volume encryption in Amazon WorkSpaces.


1.8.8
=====

* feature:``aws cloudformation describe-account-limits``: This is a new API.
* feature:``aws ec2 modify-spot-fleet-request``: This is a new API.
* bugfix:``aws elasticbeanstalk``: Documentation update.


1.8.7
=====

* feature:``aws cognito-sync``: Update API to latest version
* feature:``aws cognito-identity``: Update API to latest version
* bugfix:Assume Role Provider: Fix issue where profile does not exist errors were not being propogated back to the user (`issue 1515 <https://github.com/aws/aws-cli/pull/1515>`__)


1.8.6
=====

* bugfix:Shorthand Syntax: Fix parser regression when a key name has an underscore character (`issue 1510 <https://github.com/aws/aws-cli/pull/1510>`__)
* feature:``aws s3``: Add support for ``STANDARD_IA`` storage class to the ``aws s3`` commands (`issue 1511 <https://github.com/aws/aws-cli/pull/1511>`__)
* feature:``aws logs``: Add support for ``create-export-task``, ``cancel-export-task``, and ``describe-export-tasks``.


1.8.5
=====

* bugfix:Output: Only omit printing response to stdout if the response is an empty dictionary (`issue 1496 <https://github.com/aws/aws-cli/pull/1496>`__)
* feature:``aws s3/s3api``: Update Amazon S3 commands to the latest version


1.8.4
=====

* feature:``aws ec2 describe-snapshots``: Add new dataEncryptionKeyId and StateMessage parameters
* feature:``aws efs describe-mount-targets``: Add new optional MountTargetId parameter
* feature:``aws route53``: Add calculated health checks and latency health checks
* bugfix:StreamingBody: File-like object for HTTP response can now be properly closed


1.8.3
=====

* feature:``aws importexport``: Documentation update
* bugfix:``aws machinelearning``: Remove a constraint
* feature:``aws kinesis get-records``: Add a timestamp field to all Records
* bugfix:``aws cloudfront``: Add paginators and waiters


1.8.2
=====

* feature:``aws storagegateway``: Add support for resource tagging.


1.8.1
=====

* feature:``aws ec2 request-spot-fleet``: Add support for new request config parameters
* bugfix:Shorthand Parser: Fix regression where '-' character was not accepted as a key name in a shorthand value (`issue 1470 <https://github.com/aws/aws-cli/issues/1470>`__)
* bugfix:Shorthand Parser: Fix regression where spaces in unquoted values were not being accepted (`issue 1471 <https://github.com/aws/aws-cli/issues/1471>`__)


1.8.0
=====

* feature:``aws configservice``: Add support for listing discovered resources
* bugfix:``aws emr create-default-roles``: Fix the issue where the command would fail to honor an existing AWS_CA_BUNDLE environment setting and end up with "SSLError: object has no attribute" (`issue 1468 <https://github.com/aws/aws-cli/pull/1468>`__)
* feature:Shorthand Syntax: Add support for nested hashes when using shorthand syntax (`issue 1444 <https://github.com/aws/aws-cli/pull/1444>`__)


1.7.47
======

* feature:``aws codepipeline``: Add support for specification of an encryption key to use with the artifact bucket, when creating and updating a pipeline


1.7.46
======

* feature:``aws s3``: Add support for event notification filters
* bugfix:``aws iam create-virtual-mfa-device``: Fix issue when an error response is received from the ``create-virtual-mfa-device`` command (`issue 1447 <https://github.com/aws/aws-cli/pull/1447/>`__)


1.7.45
======

* feature:``aws elasticbeanstalk``: Add support for enhanced health reporting in ``aws elasticbeanstalk`` commands
* feature:Shared Credentials File: Add support for changing the shared credentials file from the default location of ``~/.aws/credentials`` by setting the ``AWS_SHARED_CREDENTIALS_FILE`` environment variable (`botocore issue 623 <https://github.com/boto/botocore/pull/623>`__)
* feature:Waiters: Add ``aws iam wait instance-profile-exists`` and ``aws iam wait user-exists`` commands (`botocore issue <https://github.com/boto/botocore/pull/624>`__)


1.7.44
======

* feature:``aws swf``: Add support for Added support for invoking AWS Lambda tasks from an Amazon SWF workflow.


1.7.43
======

* feature:``aws devicefarm``: Add support for testing iOS applications with AWS Device Farm.


1.7.42
======

* feature:``aws opsworks``: Add support for managing Amazon EC2 Container Service clusters.
* feature:``aws rds``: Add support for Amazon Aurora.


1.7.41
======

* feature:``aws s3api``: Add support for more types of event notifications.
* feature:``aws s3api``: Add support for GET/HEAD storage class response headers.
* feature:``aws logs``: Add destination API support.


1.7.40
======

* feature:``aws glacier``: Add support for Vault Lock.
* feature:``aws emr``: Add support for release-based clusters.


1.7.39
======

* feature:``aws devicefarm``: Add support for AWS Device Farm
* feature:``aws dynamodbstreams``: Add support for Amazon DynamoDB Streams
* feature:``aws dynamodb``: Add support for consistent reads with the Scan API


1.7.38
======

* feature:``aws codepipeline``: Add support for AWS CodePipeline
* feature:``aws codecommit``: Add support for AWS CodeCommit
* feature:``aws ses``: Add support for cross-account sending
* feature:``aws iam``: Add support for managing SSH Public Keys
* feature:``aws ecs``: Update API


1.7.37
======

* feature:``aws ec2``: Add support for EBS Snapshot Copy Support for Customer Managed Encryption Keys
* feature:``aws autoscaling``: Add support for Step Policies


1.7.36
======

* feature:``aws cloudfront``: Update the ``aws cloudfront`` command to the latest version.
* feature:``aws redshift``: Update the ``aws redshift`` command to latest version.
* feature:``aws glacier``: Add support for tagging.
* feature:``aws opsworks``: Update the ``aws opsworks`` command to latest version.
* feature:``aws config``: Add support for users to specify which types of supported resources AWS Config records for tracking configuration changes.
* feature:``aws deploy``: Adds support for deployments to Red Hat Enterprise Linux (RHEL) instances.
* feature:``aws machinelearning wait``: Add ``data-source-available``, ``ml-model-available``, ``evaluation-available``, and ``batch-prediction-available`` waiter commands. (`botocore issue 544 <https://github.com/boto/botocore/pull/544>`__)
* feature:``aws route53 wait``: Add ``resource-record-sets-changed`` waiter command. (`botocore issue 543 <https://github.com/boto/botocore/pull/543>`__)


1.7.35
======

* feature:``aws ecs``: Add support for DeregisterTaskDefintion and environment variable overrides.
* bugfix:msi: Fix issue with msi's being installed on Windows 2008 and below.


1.7.34
======

* bugfix:Installation: Fix bundled installer when running python 2.6 (`issue 1381 https://github.com/aws/aws-cli/pull/1381`)
* bugfix:Installation: Fix minimum required version of pip to install the AWS CLI using python2.6 (`issue 1383 https://github.com/aws/aws-cli/pull/1382`)


1.7.33
======

* feature:``aws autoscaling``: Add support for attachinga and describing load balancers.
* feature:``aws ec2``: Add support for VPC flow logs and M4 instances.
* feature:``aws emr``: Add Spark support and managed policy support.
* feature:``aws ecs``: Add support for updating container agent.


1.7.32
======

* feature:``aws logs``: Add support for ``put-subscription-filter``, ``describe-subscription-filters``, and ``delete-subscription-filters``
* feature:``aws storagegateway``: Add support for ``list-volume-initiators``
* feature:``aws cognito-identity``: Add support for ``delete-identities`` and hiding disabled identities with the ``list-identities`` API operation


1.7.31
======

* feature:``aws lambda create-function``: Add support for uploading code using Amazon S3.
* feature:Preview Services: Preview services are now documented and will also show up in the list of available services (`issue 1345 <https://github.com/aws/aws-cli/pull/1345>`__)


1.7.30
======

* feature:``aws efs``: Add support for ``aws efs``
* feature:``aws ecs``: Add paginators and waiters for ``aws ecs``


1.7.29
======

* feature:``aws kinesis``: The ``get-records`` command now returns a new value MillisBehindLatest: the number of milliseconds the ``get-records`` response is from the end of the stream, indicating how far behind real time a consumer is.
* feature:``aws kms``: Add update-alias command
* feature:``aws elastictranscoder``: Update the aws elastictranscoder command to include support for additional formats, including MXF, FLAC, and OGA, and additional flexibility for your output audio.


1.7.28
======

* feature:``aws ec2``: Add support for Spot Fleet.
* feature:``aws opsworks``: Add support for custom AutoScaling.
* feature:``aws elasticbeanstalk``: Update model to latest version.


1.7.27
======

* feature:``aws ds``: Add support for AWS Directory Service.
* feature:``aws ec2``: Add support for VPC endpoints for Amazon S3.
* feature:``aws ec2``: Add support for EIP Migration.
* feature:``aws logs``: Add support for filtering log events.


1.7.26
======

* feature:``aws glacier``: Add support for vault policies.
* bugfix:``aws iam create-open-id-connect-provider``: Fix issue where the ``--url`` parameter would try to retrieve the contents from the url instead of use the url as its value. (`issue 1317 <https://github.com/aws/aws-cli/pull/1317>`__)
* bugfix:``aws workspaces``: Fix issue where throttling errors were not being retried (`botocore issue 529 <https://github.com/boto/botocore/pull/529>`__)


1.7.25
======

* feature:``aws dynamodb query``: Add support for KeyConditonExpression.


1.7.24
======

* feature:``aws help topics``: Add support for listing available help topics.
* feature:``aws help config-vars``: Add help topic for configuration variables.
* feature:``aws help return-codes``: Add help topic for return codes.
* feature:``aws help s3-config``: Add help topic for configuration of s3 commands.
* bugfix:``aws lambda create-function/update-function-code``: Improve error message when invalid ``--zip-file`` values are provided (`issue 1296 <https://github.com/aws/aws-cli/pull/1296>`__)
* feature:``aws ec2``: Add support for new VM Import APIs, including ``import-image``.  The new APIs provide support for importing multi-volume VMs to Amazon EC2 and other enhancements.
* feature:``aws iam``: Update AWS IAM command to latest version


1.7.23
======

* feature:``aws cognito-sync``: Add support for Amazon Cognito Events.
* bugfix:Parsing: Treat empty XML nodes in a response as an empty string instead of ``None`` if the underlying structure member is a string. This fixes the broken ``password-data-available`` Amazon EC2 waiter. **Note**: this changes the output of the CLI and may affect filtering with the ``--query`` parameter. (`issue 1252 <https://github.com/aws/aws-cli/issues/1252>`__, `botocore issue 506 <https://github.com/boto/botocore/pull/506>`__)


1.7.22
======

* bugfix:``aws ecs``: Minor documentation fixes.


1.7.21
======

* feature:``aws workspaces``: Add support for Amazon WorkSpaces.
* feature:``aws machinelearning``: Add support for Amazon Machine Learning.
* feature:``aws s3api``: Add support for specifying Lambda bucket notifications without needing to specify an invocation role.
* feature:``aws lambda``: Update to latest api.
* feature:``aws ecs``: Add support for Amazon ECS Service scheduler.


1.7.20
======

* feature:``aws datapipeline``: Add support for deactivating pipelines.
* feature:``aws elasticbeanstalk``: Add support for cancelling in-progress environment updates or application version deployment.


1.7.19
======

* feature:``aws codedeploy``: Add ``register``, ``deregister``, ``install``, and ``uninstall`` commands and update to the latest AWS CodeDeploy API.
* feature:``aws rds``: Add support for ``describe-certificates``.
* feature:``aws elastictranscoder``: Add support for PlayReady DRM.
* feature:``aws ec2``: Add support for D2 instances.


1.7.18
======

* bugfix:Pagination: Fix issue where disabling pagination did not work when shadowing arguments.  Affects commands such as ``aws route53 list-resource-record-sets``.
* feature:``aws elastictranscoder``: Add support for job timing and input/output metadata
* feature:``aws iam``: Add NamedPolicy to GetAccountAuthorization details
* feature:``aws opsworks``: Allow for BlockDeviceMapping on EC2 instances launched through OpsWorks


1.7.17
======

* feature:``aws emr``: Adds support for Amazon S3 client-side encryption in Amazon EMR and setting configuration values for several variables in the ``create-cluster`` and ``ssh`` commands. Also, the ``create-default-roles`` command will now auto-populate the Service Role and Instance Profile variables in the configuration file with the default roles after they are created.


1.7.16
======

* feature:``aws ec2 wait image-available``: Add support for polling until an EC2 image is available (`issue 1105 <https://github.com/aws/aws-cli/issues/1105>`__)
* feature:``aws ec2 wait``: Add support for additional EC2 waiters including ``instance-status-ok``, ``password-data-available``, ``spot-instance-request-fulfilled``, and ``system-status-ok``
* feature:``aws s3api``: Add support for Amazon S3 cross region replication
* feature:``aws s3api``: Add support for Amazon S3 requester pays (`issue 797 <https://github.com/aws/aws-cli/issues/797>`__)
* bugfix:Tab Completion: Fix issue where tab completion could not handle an ``LC_CTYPE`` of ``UTF-8`` (`issue 1233 <https://github.com/aws/aws-cli/pull/1233>`__)
* bugfix:``aws s3api put-bucket-notification``: Fix issue where an empty notification configuration could not be specified (`botocore issue 495 <https://github.com/boto/botocore/pull/495>`__)
* bugfix:``aws cloudfront``: Fix issue when calling cloudfront commands (`issue 1234 <https://github.com/aws/aws-cli/issues/1234>`__)
* bugfix:``aws ec2 copy-snapshot``: Fix issue with the ``aws ec2 copy-snapshot`` command not correctly generating the presigned url argument (`botocore issue 498 <https://github.com/boto/botocore/pull/498>`__)


1.7.15
======

* feature:``aws elastictranscoder``: Add support for Applied Color SpaceConversion.
* bugfix:``aws --profile``: Fix issue where explicitly specifying profile did not override credential environment variables. (`botocore issue 486 <https://github.com/boto/botocore/pull/486>`__)
* bugfix:``aws datapipeline list-runs``: Fix issue with ``--schedule-interval`` parameter. (`issue 1225 <https://github.com/aws/aws-cli/pull/1225>`__)
* bugfix:``aws configservice subscribe``: Fix issue where users could not subscribe to a s3 bucket that they had no HeadBucket permissions to. (`issue 1223 <https://github.com/aws/aws-cli/pull/1223>`__)
* bugfix:``aws cloudtrail create-subscription``: Fix issue where command would try to fetch the contents at a url using the contents of the custom policy as the url. (`issue 1216 <https://github.com/aws/aws-cli/pull/1216/files>`__)


1.7.14
======

* feature:``aws logs``: Update ``aws logs`` command to the latest model.
* feature:``aws ec2``: Add paginators for the ``describe-snapshots`` sub-command.
* feature:``aws cloudtrail``: Add support for the new ``lookup-events`` sub-command.
* bugfix:``aws configure set``: Fix issue when setting nested configuration values
* feature:``aws s3``: Add support for ``--metadata-directive`` that allows metadata to be copied or replaced for single part copies. (`issue 1188 <https://github.com/aws/aws-cli/pull/1188>`__)


1.7.13
======

* feature:``aws cloudsearch``: Update ``aws cloudsearch`` command to the latest model
* feature:``aws cognito-sync``: Update ``aws cognito-sync`` command to allow customers to receive near-realtime updates as their data changes as well as exporting historical data. Customers configure an Amazon Kinesis stream to receive the data which can then be processed and exported to other data stores such as Amazon Redshift.
* bugfix:``aws opsworks``: Fix issue with platform detection on linux systems with python3.3 and higher (`issue 1199 <https://github.com/aws/aws-cli/pull/1199>`__)
* feature:Help Paging: Support paging through ``more`` when running help commands on windows (`issue 1195 <https://github.com/aws/aws-cli/pull/1195>`__)
* bugfix:``aws s3``: Fix issue where read timeouts were not retried. (`issue 1191 <https://github.com/aws/aws-cli/pull/1191>`__)
* feature:``aws cloudtrail``: Add support for regionalized policy templates for the ``create-subscription`` and ``update-subscription`` commands. (`issue 1167 <https://github.com/aws/aws-cli/pull/1167>`__)
* bugfix:parsing: Fix issue where if there is a square bracket inside one of the values of a list, the end character would get removed. (`issue 1183 <https://github.com/aws/aws-cli/pull/1183>`__)


1.7.12
======

* feature:``aws datapipeline``: Add support for tagging.
* feature:``aws route53``: Add support for listing hosted zones by name and getting the hosted zone count.
* bugfix:``aws s3 sync``: Remove ``--recursive`` parameter. The ``sync`` command is always a recursive operation meaning the inclusion or exclusion of ``--recursive`` had no effect on the ``sync`` command. (`issue 1171 <https://github.com/aws/aws-cli/pull/1171>`__)
* bugfix:``aws s3``: Fix issue where ``--endpoint-url`` was being ignored (`issue 1142 <https://github.com/aws/aws-cli/pull/1142>`__)


1.7.11
======

* bugfix:``aws sts``: Allow calling ``assume-role-with-saml`` without credentials.
* bugfix:``aws sts``: Allow users to make regionalized STS calls by specifying the STS endpoint with ``--endpoint-url`` and the region with ``--region``. (`botocore issue 464 <https://github.com/boto/botocore/pull/464>`__)


1.7.10
======

* bugfix:``aws sts``: Fix regression where if a region was not activated for STS it would raise an error if call was made to that region.


1.7.9
=====

* feature:``aws cloudfront``: Update to latest API
* feature:``aws sts``: Add support for STS regionalized calls
* feature:``aws ssm``: Add support for Amazon Simple Systems Management Service (SSM)


1.7.8
=====

* bugfix:``aws s3``: Fix auth errors when uploading large files to the ``eu-central-1`` and ``cn-north-1`` regions (`botocore issue 462 <https://github.com/boto/botocore/pull/462>`__)


1.7.7
=====

* bugfix:``aws ec2 revoke-security-group-ingress``: Fix parsing of a ``--port`` value of ICMP echo request (`issue 1075 <https://github.com/aws/aws-cli/issues/1075>`__)
* feature:``aws iam``: Add support for managed policies
* feature:``aws elasticache``: Add support for tagging
* feature:``aws route53domains``: Add support for tagging of domains


1.7.6
=====

* feature:``aws dynamodb``: Add support for index scan
* bugfix:``aws s3``: Fix issue where literal value for ``--website-redirect`` was not being used. (`issue 1137 <https://github.com/aws/aws-cli/pull/1137>`__)
* bugfix:``aws sqs purge-queue``: Fix issue with the processing of the ``--queue-url`` parameter (`issue 1126 <https://github.com/aws/aws-cli/issues/1126>`__)
* feature:``aws s3``: Add support for config variable for changing S3 runtime values (`issue 1122 <https://github.com/aws/aws-cli/pull/1122>`__)
* bugfix:Proxies: Fix issue with SSL certificate validation when using proxies and python 2.7.9 (`botocore issue 451 <https://github.com/boto/botocore/pull/451>`__)


1.7.5
=====

* bugfix:``aws datapipeline list-runs``: Fix issue where ``--status`` values where not being serialized correctly (`issue 1110 <https://github.com/aws/aws-cli/pull/1110>`__)
* bugfix:Output Formatting: Handle broken pipe errors when piping the output to another program (`issue 1113 <https://github.com/aws/aws-cli/pull/1113>`__)
* bugfix:HTTP Proxy: Fix issue where ``aws s3/s3api`` commands would hang when using an HTTP proxy (`issue 1116 <https://github.com/aws/aws-cli/issues/1116>`__)
* feature:``aws elasticache wait``: Add waiters for the ``aws elasticache wait`` (`botocore issue 443 <https://github.com/boto/botocore/pull/443>`__)
* bugfix:Locale Settings: Fix issue when Mac OS X has an ``LC_CTYPE`` value of ``UTF-8`` (`issue 945 <https://github.com/aws/aws-cli/issues/945>`__)


1.7.4
=====

* feature:``aws dynamodb``: Add support for online indexing.
* feature:``aws importexport get-shipping-label``: Add support for ``get-shipping-label``.
* feature:``aws s3 ls``: Add ``--human-readable`` and ``--summarize`` options (`issue 1103 <https://github.com/aws/aws-cli/pull/1103>`__)
* bugfix:``aws kinesis put-records``: Fix issue with base64 encoding for blob types (`botocore issue 413 <https://github.com/boto/botocore/pull/413>`__)


1.7.3
=====

* feature:``aws emr``: Add support for security groups.
* feature:``aws cognitio-identity``: Enhance authentication flow by being able to save associations of IAM roles with identity pools.


1.7.2
=====

* feature:``aws autoscaling``: Add ClassicLink support.
* bugfix:``aws s3``: Fix issue where mtime was set before file was finished downloading. (`issue 1102 <https://github.com/aws/aws-cli/pull/1102>`__)


1.7.1
=====

* bugfix:``aws s3 cp``: Fix issue with parts of a file being downloaded more than once when streaming to stdout (`issue 1087 <https://github.com/aws/aws-cli/pull/1087>`__)
* bugfix:``--no-sign-request``: Fix issue where requests were still trying to be signed even though user used the ``--no-sign-request`` flag. (`botocore issue 433 <https://github.com/boto/botocore/pull/433>`__)
* bugfix:``aws cloudsearchdomain search``: Fix invalid signatures when using the ``aws cloudsearchdomain search`` command (`issue 976 <https://github.com/aws/aws-cli/issues/976>`__)


1.7.0
=====

* feature:``aws cloudhsm``: Add support for AWS CloudHSM.
* feature:``aws ecs``: Add support for ``aws ecs``, the Amazon EC2 Container Service (ECS)
* feature:``aws rds``: Add Encryption at Rest and CloudHSM Support.
* feature:``aws ec2``: Add Classic Link support
* feature:``aws cloudsearch``: Update ``aws cloudsearch`` command to latest version
* bugfix:``aws cloudfront wait``: Fix issue where wait commands did not stop waiting when a success state was reached. (`botocore issue 426 <https://github.com/boto/botocore/pull/426>`_)
* bugfix:``aws ec2 run-instances``: Allow binary files to be passed to ``--user-data`` (`botocore issue 416 <https://github.com/boto/botocore/pull/416>`_)
* bugfix:``aws cloudsearchdomain suggest``: Add ``--suggest-query`` option to fix the argument being shadowed by the top level ``--query`` option. (`issue 1068 <https://github.com/aws/aws-cli/pull/1068>`__)
* bugfix:``aws emr``: Fix issue with endpoints for ``eu-central-1`` and ``cn-north-1`` (`botocore issue 423 <https://github.com/boto/botocore/pull/423>`__)
* bugfix:``aws s3``: Fix issue where empty XML nodes are now parsed as an empty string ``""`` instead of ``null``, which allows for round tripping ``aws s3 get/put-bucket-lifecycle`` (`issue 1076 <https://github.com/aws/aws-cli/issues/1076>`__)


1.6.10
======

* bugfix:AssumeRole: Fix issue with cache filenames when assuming a role on Windows (`issue 1063 <https://github.com/aws/aws-cli/issues/1063>`__)
* bugfix:``aws s3 ls``: Fix issue when listing Amazon S3 objects containing non-ascii characters in eu-central-1 (`issue 1046 <https://github.com/aws/aws-cli/issues/1046>`__)
* feature:``aws storagegateway``: Update the ``aws storagegateway`` command to the latest version
* feature:``aws emr``: Update the ``aws emr`` command to the latest version
* bugfix:``aws emr create-cluster``: Fix script runnner jar to the current region location when ``--enable-debugging`` is specified in the ``aws emr create-cluster`` command


1.6.9
=====

* bugfix:``aws datapipeline get-pipeline-definition``: Rename operation parameter ``--version`` to ``--pipeline-version`` to avoid shadowing a built in parameter (`issue 1058 <https://github.com/aws/aws-cli/pull/1058>`__)
* bugfix:pip installation: Fix issue where pip installations would cause an error due to the system's python configuration (`issue 1051 <https://github.com/aws/aws-cli/issues/1051>`__)
* feature:``aws elastictranscoder``: Update the ``aws elastictranscoder`` command to the latest version


1.6.8
=====

* bugfix:Non-ascii chars: Fix issue where escape sequences were being printed instead of the non-ascii chars (`issue 1048 <https://github.com/aws/aws-cli/issues/1048>`__)
* bugfix:``aws iam create-virtual-mfa-device``: Fix issue with ``--outfile`` not supporting relative paths (`issue 1002 <https://github.com/aws/aws-cli/pull/1002>`__)


1.6.7
=====

* feature:``aws sqs``: Add support for Amazon Simple Queue Service purge queue which allows users to delete the messages in their queue.
* feature:``aws opsworks``: Add AWS OpsWorks support for registering and assigning existing Amazon EC2 instances and on-premises servers.
* feature:``aws opsworks register``: Registers an EC2 instance or machine with AWS OpsWorks. Registering a machine using this command will install the AWS OpsWorks agent on the target machine and register it with an existing OpsWorks stack.
* bugfix:``aws s3``: Fix issue with expired signatures when retrying failed requests (`botocore issue 399 <https://github.com/boto/botocore/pull/399>`__)
* bugfix:``aws cloudformation get-template``: Fix error message when template does not exist (`issue 1044 <https://github.com/aws/aws-cli/issues/1044>`__)


1.6.6
=====

* feature:``aws kinesis put-records``: Add support for PutRecord operation. It writes multiple data records from a producer into an Amazon Kinesis stream in a single call
* feature:``aws iam get-account-authorization-details``: Add support for GetAccountAuthorizationDetails operation. It retrieves information about all IAM users, groups, and roles in your account, including their relationships to one another and their attached policies.
* feature:``aws route53 update-hosted-zone-comment``: Add support for updating the comment of a hosted zone.
* bugfix:Timestamp Arguments: Fix issue where certain timestamps were not being accepted as valid input (`botocore issue 389 <https://github.com/boto/botocore/pull/389>`__)
* bugfix:``aws s3``: Skip files whose names cannot be properly decoded (`issue 1038 <https://github.com/aws/aws-cli/pull/1038>`__)
* bugfix:``aws kinesis put-record``: Fix issue where ``--data`` argument was not being base64 encoded (`issue 1033 <https://github.com/aws/aws-cli/issues/1033>`__)
* bugfix:``aws cloudwatch put-metric-data``: Fix issue where the values for ``--statistic-values`` were not being parsed properly (`issue 1036 <https://github.com/aws/aws-cli/issues/1036>`__)


1.6.5
=====

* feature:``aws datapipeline``: Add support for using AWS Data Pipeline templates to create pipelines and bind values to parameters in the pipeline
* feature:``aws elastictranscoder``: Add support for encryption of files in Amazon S3
* bugfix:``aws s3``: Fix issue where requests were not being resigned correctly when using Signature Version 4 (`botocore issue 388 <https://github.com/boto/botocore/pull/388>`__)
* bugfix:``aws s3``: Fix issue where KMS encrypted objects could not be downloaded (`issue 1026 <https://github.com/aws/aws-cli/pull/1026>`__)


1.6.4
=====

* bugfix:``aws s3``: Fix issue where datetime's were not being parsed properly when a profile was specified (`issue 1020 <https://github.com/aws/aws-cli/issues/1020>`__)
* bugfix:Assume Role Credential Provider: Fix issue with parsing expiry time from assume role credential provider (`botocore issue 387 <https://github.com/boto/botocore/pull/387>`__)


1.6.3
=====

* feature:``aws redshift``: Add support for integration with KMS
* bugfix:``aws cloudtrail create-subscription``: Set a bucket config location constraint on buckets created outside of us-east-1. (`issue 1013 <https://github.com/aws/aws-cli/pull/1013>`__)
* bugfix:``aws deploy push``: Fix s3 multipart uploads
* bugfix:``aws s3 ls``: Fix return codes for non existing objects (`issue 1008 <https://github.com/aws/aws-cli/pull/1008>`__)
* bugfix:Retrying Signed Requests: Fix issue where requests using Signature Version 4 signed with temporary credentials were not being retried properly, resulting in auth errors (`botocore issue 379 <https://github.com/boto/botocore/pull/379>`__)
* bugfix:``aws s3api get-bucket-location``: Fix issue where getting the bucket location for a bucket in eu-central-1 required specifying ``--region eu-central-1`` (`botocore issue 380 <https://github.com/boto/botocore/pull/380>`__)
* bugfix:Timestamp Input: Fix regression where timestamps without any timezone information were not being handled properly (`issue 982 <https://github.com/aws/aws-cli/issues/982>`__)
* bugfix:Signature Version 4: You can enable Signature Version 4 for Amazon S3 commands by running ``aws configure set default.s3.signature_version s3v4`` (`issue 1006 <https://github.com/aws/aws-cli/issues/1006>`__, `botocore issue 382 <https://github.com/boto/botocore/pull/382>`__)
* bugfix:``aws emr``: Fix issue where ``--ssh``, ``--get``, ``--put`` would not work when the cluster was in a waiting state (`issue 1007 <https://github.com/aws/aws-cli/issues/1007>`__)
* feature:Binary File Input: Add support for reading file contents as binary by prepending the filename with ``fileb://`` (`issue 1010 <https://github.com/aws/aws-cli/pull/1010>`__)
* bugfix:Streaming Output File: Fix issue when streaming a response to a file and an error response is returned (`issue 1012 <https://github.com/aws/aws-cli/pull/1012>`__)
* bugfix:Binary Output: Fix regression where binary output was no longer being base64 encoded (`issue 1001 <https://github.com/aws/aws-cli/pull/1001>`__, `issue 970 <https://github.com/aws/aws-cli/pull/970>`__)


1.6.2
=====

* feature:``aws s3``: Add support for S3 notifications
* bugfix:``aws configservice get-status``: Fix connecting to endpoint without using ssl. (`issue 998 <https://github.com/aws/aws-cli/pull/998>`__)
* bugfix:``aws deploy push``: Fix some python compatibility issues (`issue 1000 <https://github.com/aws/aws-cli/pull/1000>`__)


1.6.1
=====

* feature:``aws configservice``: Adds support for AWS Config
* feature:``aws kms``: Adds support AWS Key Management Service
* feature:``aws s3api``: Adds support for S3 server-side encryption using KMS
* feature:``aws ec2``: Adds support for EBS encryption using KMS
* feature:``aws cloudtrail``: Adds support for CloudWatch Logs delivery
* feature:``aws cloudformation``: Adds support for template summary.


1.6.0
=====

* feature:AssumeRole Credential Provider: Add support for assuming a role by configuring a ``role_arn`` and a ``source_profile`` in the AWS config file (`issue 991 <https://github.com/aws/aws-cli/pull/991>`__, `issue 990 <https://github.com/aws/aws-cli/pull/990>`__)
* feature:Waiters: Add a ``wait`` subcommand that allows for a command to block until an AWS resource reaches a given state (`issue 992 <https://github.com/aws/aws-cli/pull/992>`__, `issue 985 <https://github.com/aws/aws-cli/pull/985>`__)
* bugfix:``aws s3``: Fix issue where request was not properly signed on retried requests for ``aws s3`` (`issue 986 <https://github.com/aws/aws-cli/issues/986>`__, `botocore issue 375 <https://github.com/boto/botocore/pull/375>`__)
* bugfix:``aws s3``: Fix issue where ``--exclude`` and ``--include`` were not being properly applied when a s3 prefix was provided. (`issue 993 <https://github.com/aws/aws-cli/pull/993>`__)


1.5.6
=====

* feature:``aws cloudfront``: Adds support for wildcard cookie names and options caching.
* feature:``aws route53``: Add further support for private dns and sigv4.
* feature:``aws cognito-sync``: Add support for push sync.


1.5.5
=====

* bugfix:Pagination: Only display ``--page-size`` when an operation can be paginated (`issue 956 <https://github.com/aws/aws-cli/pull/956>`__)
* feature:``--generate-cli-skeleton``: Generates a JSON skeleton to fill out and be used as input to ``--cli-input-json``. (`issue 963 <https://github.com/aws/aws-cli/pull/963>`_)
* feature:``--cli-input-json``: Runs an operation using a global JSON file that supplies all of the operation's arguments. This JSON file can be generated by ``--generate-cli-skeleton``. (`issue 963 <https://github.com/aws/aws-cli/pull/963>`_)


1.5.4
=====

* feature:``aws s3/s3api``: Show hint about using the correct region when the corresponding error occurs (`issue 968 <https://github.com/aws/aws-cli/pull/968>`__)


1.5.3
=====

* feature:``aws ec2 describe-volumes``: Add support for optional pagination.
* feature:``aws route53domains``: Add support for auto-renew domains.
* feature:``aws cognito-identity``: Add for Open-ID Connect.
* feature:``aws sts``: Add support for Open-ID Connect
* feature:``aws iam``: Add support for Open-ID Connect
* bugfix:``aws s3 sync``: Fix issue when uploading with ``--exact-timestamps`` (`issue 964 <https://github.com/aws/aws-cli/pull/964>`__)
* bugfix:Retry: Fix issue where certain error codes were not being retried (`botocore issue 361 <https://github.com/boto/botocore/pull/361>`__)
* bugfix:``aws emr ssh``: Fix issue when using waiter interface to wait on the cluster state (`issue 954 <https://github.com/aws/aws-cli/pull/954>`__)


1.5.2
=====

* feature:``aws cloudsearch``: Add support for advance Japanese language processing.
* feature:``aws rds``: Add support for gp2 which provides faster access than disk-based storage.
* bugfix:``aws s3 mv``: Delete multi-part objects when transferring objects across regions using ``--source-region`` (`issue 938 <https://github.com/aws/aws-cli/pull/938>`__)
* bugfix:``aws emr ssh``: Fix issue with waiter configuration not being found (`issue 937 <https://github.com/aws/aws-cli/issues/937>`__)


1.5.1
=====

* feature:``aws dynamodb``: Update ``aws dynamodb`` command to support storing and retrieving documents with full support for document models.  New data types are fully compatible with the JSON standard and allow you to nest document elements within one another.
* bugfix:``aws configure``: Fix bug where ``aws configure`` was not properly writing out to the shared credentials file
* bugfix:S3 Response Parsing: Fix regression for parsing S3 responses containing a status code of 200 with an error response body (`botocore issue 342 <https://github.com/boto/botocore/pull/342>`__)
* bugfix:Shorthand Error Message: Ensure the error message for shorthand parsing always contains the CLI argument name (`issue 935 <https://github.com/aws/aws-cli/pull/935>`__)


1.5.0
=====

* bugfix:Response Parsing: Fix response parsing so that leading and trailing spaces are preserved
* feature:Shared Credentials File: The ``aws configure`` and ``aws configure set`` command now write out all credential variables to the shared credentials file ``~/.aws/credentials`` (`issue 847 <https://github.com/aws/aws-cli/issues/847>`__)
* bugfix:``aws s3``: Write warnings and errors to standard error as opposed to standard output. (`issue 919 <https://github.com/aws/aws-cli/pull/919>`__)
* feature:``aws s3``: Add ``--only-show-errors`` option that displays errors and warnings but suppresses all other output.
* feature:``aws s3 cp``: Added ability to upload local file streams from standard input to s3 and download s3 objects as local file streams to standard output. (`issue 903 <https://github.com/aws/aws-cli/pull/903>`__)


1.4.4
=====

* feature:``aws emr create-cluster``: Add support for ``--emrfs``.


1.4.3
=====

* feature:``aws iam``: Update ``aws iam`` command to latest version.
* feature:``aws cognito-sync``: Update ``aws cognito-sync`` command to latest version.
* feature:``aws opsworks``: Update ``aws opsworks`` command to latest version.
* feature:``aws elasticbeanstalk``: Add support for bundling logs.
* feature:``aws kinesis``: Add suport for tagging.
* feature:Page Size: Add a ``--page-size`` option, that controls page size when perfoming an operation that uses pagination. (`issue 889 <https://github.com/aws/aws-cli/pull/889>`__)
* bugfix:``aws s3``: Added support for ignoring and warning about files that do not exist, user does not have read permissions, or are special files (i.e. sockets, FIFOs, character special devices, and block special devices) (`issue 881 <https://github.com/aws/aws-cli/pull/881>`__)
* feature:Parameter Shorthand: Added support for ``structure(list-scalar, scalar)`` parameter shorthand. (`issue 882 <https://github.com/aws/aws-cli/pull/882>`__)
* bugfix:``aws s3``: Fix bug when unknown options were passed to ``aws s3`` commands (`issue 886 <https://github.com/aws/aws-cli/pull/886>`__)
* bugfix:Endpoint URL: Provide a better error message when an invalid ``--endpoint-url`` is provided (`issue 899 <https://github.com/aws/aws-cli/issues/899>`__)
* bugfix:``aws s3``: Fix issue when keys do not get properly url decoded when syncing from a bucket that requires pagination to a bucket that requires less pagination (`issue 909 <https://github.com/aws/aws-cli/pull/909>`__)


1.4.2
=====

* feature:``aws cloudsearchdomain``: Added sigv4 support.
* bugfix:Credentials: Raise an error if an incomplete profile is found (`issue 690 <https://github.com/aws/aws-cli/issues/690>`__)
* feature:Signing Requests: Add a ``--no-sign-request`` option that, when specified, will not sign any requests.
* bugfix:``aws s3``: Added ``-source-region`` argument to allow transfer between non DNS compatible buckets that were located in different regions. (`issue 872 <https://github.com/aws/aws-cli/pull/872>`__)


1.4.1
=====

* feature:``aws elb``: Add support for AWS Elastic Load Balancing tagging


1.4.0
=====

* feature:``aws emr``: Move emr out of preview mode.
* bugfix:``aws s3api``: Fix serialization of several s3 api commands. (`issue botocore 193 <https://github.com/boto/botocore/pull/196>`__)
* bugfix:``aws s3 sync``: Fix issue for unnecessarily resyncing files on windows machines. (`issue 843 <https://github.com/aws/aws-cli/issues/843>`__)
* bugfix:``aws s3 sync``: Fix issue where keys were being decoded twice when syncing between buckets. (`issue 862 <https://github.com/aws/aws-cli/pull/862>`__)


1.3.25
======

* bugfix:``aws ec2 describe-network-interface-attribute``: Fix issue where the model for the ``aws ec2 describe-network-interface-attribute`` was incorrect (`issue 558 <https://github.com/aws/aws-cli/issues/558>`__)
* bugfix:``aws s3``: Add option to not follow symlinks via ``--[no]-follow-symlinks``.  Note that the default behavior of following symlinks is left unchanged. (`issue 854 <https://github.com/aws/aws-cli/pull/854>`__, `issue 453 <https://github.com/aws/aws-cli/issues/453>`__, `issue 781 <https://github.com/aws/aws-cli/issues/781>`__)
* bugfix:``aws route53 change-tags-for-resource``: Fix serialization issue for ``aws route53 change-tags-for-resource`` (`botocore issue 328 <https://github.com/boto/botocore/pull/328>`__)
* bugfix:``aws ec2 describe-network-interface-attribute``: Update parameters to add the ``--attribute`` argument (`botocore issue 327 <https://github.com/boto/botocore/pull/327>`__)
* feature:``aws autoscaling``: Update command to the latest version
* feature:``aws elasticache``: Update command to the latest version
* feature:``aws route53``: Update command to the latest version
* feature:``aws route53domains``: Add support for Amazon Route53 Domains


1.3.24
======

* feature:``aws elasticloadbalancing``: Update to the latest service model.
* bugfix:``aws swf poll-for-decision-task``: Fix issue where the default paginated response is missing output response keys (`issue botocore 324 <https://github.com/boto/botocore/pull/324>`__)
* bugfix:Connections: Fix issue where connections were hanging when network issues occurred `issue botocore 325 <https://github.com/boto/botocore/pull/325>`__)
* bugfix:``aws s3/s3api``: Fix issue where Deprecations were being written to stderr in Python 3.4.1 `issue botocore 319 <https://github.com/boto/botocore/issues/319>`__)


1.3.23
======

* feature:``aws support``: Update ``aws support`` command to the latest version
* feature:``aws iam``: Update ``aws iam`` command to the latest version
* feature:``aws emr``: Add ``--hive-site`` option to ``aws emr create-cluster`` and ``aws emr install-application`` commands
* feature:``aws s3 sync``: Add an ``--exact-timestamps`` option to the ``aws s3 sync`` command (`issue 824 <https://github.com/aws/aws-cli/pull/824>`__)
* bugfix:``aws ec2 copy-snapshot``: Fix bug when spaces in the description caused the copy request to fail (`issue botocore 321 <https://github.com/boto/botocore/pull/321>`__)


1.3.22
======

* feature:``aws cwlogs``: Add support for Amazon CloudWatch Logs
* feature:``aws cognito-sync``: Add support for Amazon Cognito Service
* feature:``aws cognito-identity``: Add support for Amazon Cognito Identity Service
* feature:``aws route53``: Update ``aws route53`` command to the latest version
* feature:``aws ec2``: Update ``aws ec2`` command to the latest version
* bugfix:``aws s3/s3api``: Fix issue where ``--endpoint-url`` wasn't being used for ``aws s3/s3api`` commands (`issue 549 <https://github.com/aws/aws-cli/issues/549>`__)
* bugfix:``aws s3 mv``: Fix bug where using the ``aws s3 mv`` command to move a large file onto itself results in the file being deleted (`issue 831 <https://github.com/aws/aws-cli/issues/831>`__)
* bugfix:``aws s3``: Fix issue where parts in a multipart upload are stil being uploaded when a part has failed (`issue 834 <https://github.com/aws/aws-cli/issues/834>`__)
* bugfix:Windows: Fix issue where ``python.exe`` is on a path that contains spaces (`issue 825 <https://github.com/aws/aws-cli/pull/825>`__)


1.3.21
======

* feature:``aws opsworks``: Update the ``aws opsworks`` command to the latest version
* bugfix:Shorthand JSON: Fix bug where shorthand lists with a single item (e.g. ``--arg Param=[item]``) were not parsed correctly. (`issue 830 <https://github.com/aws/aws-cli/pull/830>`__)
* bugfix:Text output: Fix bug when rendering only scalars that are numbers in text output (`issue 829 <https://github.com/aws/aws-cli/pull/829>`__)
* bugfix:``aws cloudsearchdomain``: Fix bug where ``--endpoint-url`` is required even for ``help`` subcommands (`issue 828 <https://github.com/aws/aws-cli/pull/828>`__)


1.3.20
======

* feature:``aws cloudsearchdomain``: Add support for the Amazon CloudSearch Domain command.
* feature:``aws cloudfront``: Update the Amazon CloudFront command to the latest version


1.3.19
======

* feature:``aws ses``: Add support for delivery notifications
* bugfix:Region Config: Fix issue for ``cn-north-1`` region (`issue botocore 314 <https://github.com/boto/botocore/pull/314>`__)
* bugfix:Amazon EC2 Credential File: Fix regression for parsing EC2 credential file (`issue botocore 315 <https://github.com/boto/botocore/pull/315>`__)
* bugfix:Signature Version 2: Fix timestamp format when calculating signature version 2 signatures (`issue botocore 308 <https://github.com/boto/botocore/pull/308>`__)


1.3.18
======

* feature:``aws configure``: Add support for setting nested attributes (`issue 817 <https://github.com/aws/aws-cli/pull/817>`__)
* bugfix:``aws s3``: Fix issue when uploading large files to newly created buckets in a non-standard region (`issue 634 <https://github.com/aws/aws-cli/issues/634>`__)
* feature:``aws dynamodb``: Add support for a ``local`` region for dynamodb (``aws dynamodb --region local ...``) (`issue 608 <https://github.com/aws/aws-cli/issues/608>`__)
* feature:``aws elasticbeanstalk``: Update ``aws elasticbeanstalk`` model to the latest version
* feature:Documentation Examples: Add more documentatoin examples for many AWS CLI commands
* feature:``aws emr``: Update model to the latest version
* feature:``aws elastictranscoder: `` Update model to the latest version


1.3.17
======

* feature:``aws s3api``: Add support for server-side encryption with a customer-supplied encryption key.
* feature:``aws sns``: Support for message attributes.
* feature:``aws redshift``: Support for renaming clusters.


1.3.16
======

* bugfix:``aws s3``: Fix bug related to retrying requests when 500 status codes are received (`issue botocore 302 <https://github.com/boto/botocore/pull/302>`__)
* bugfix:``aws s3``: Fix when when using S3 in the ``cn-north-1`` region (`issue botocore 301 <https://github.com/boto/botocore/pull/301>`__)
* bugfix:``aws kinesis``: Fix pagination bug when using the ``get-records`` operation (`issue botocore 304 <https://github.com/boto/botocore/pull/304>`__)


1.3.15
======

* bugfix:Python 3.4.1: Add support for python 3.4.1 (`issue 800 <https://github.com/aws/aws-cli/issues/800>`__)
* feature:``aws emr``: Update preview commands for Amazon Elastic MapReduce


1.3.14
======

* bugfix:``aws s3``: Add filename to error message when we're unable to stat local filename (`issue 795 <https://github.com/aws/aws-cli/pull/795>`__)
* bugfix:``aws s3api get-bucket-policy``: Fix response parsing for the ``aws s3api get-bucket-policy`` command (`issue 678 <https://github.com/aws/aws-cli/issues/678>`__)
* bugfix:Shared Credentials: Fix bug when specifying profiles that don't exist in the CLI config file (`issue botocore 294 <https://github.com/boto/botocore/pull/294>`__)
* bugfix:``aws s3``: Handle Amazon S3 error responses that have a 200 OK status code (`issue botocore 298 <https://github.com/boto/botocore/pull/298>`__)
* feature:``aws sts``: Update the ``aws sts`` command to the latest version
* feature:``aws cloudsearch``: Update the ``aws cloudsearch`` command to the latest version


1.3.13
======

* feature:Shorthand: Add support for surrounding list parameters with ``[]`` chars in shorthand syntax (`issue 788 <https://github.com/aws/aws-cli/pull/788>`__)
* feature:Shared credential file: Add support for the ``~/.aws/credentials`` file
* feature:``aws ec2``: Add support for Amazon EBS encryption


1.3.12
======

* bugfix:``aws s3``: Fix issue when ``--delete`` and ``--exclude`` filters are used together (`issue 778 <https://github.com/aws/aws-cli/issues/778>`__)
* feature:``aws route53``: Update ``aws route53`` to the latest model
* bugfix:``aws emr``: Fix issue with ``aws emr`` retry logic not being applied correctly (`botocore issue 285 <https://github.com/boto/botocore/pull/285>`__)


1.3.11
======

* feature:``aws cloudtrail``: Add support for eu-west-1, ap-southeast-2, and eu-west-1 regions
* bugfix:``aws ec2``: Fix issue when specifying user data from a file containing non-ascii characters (`issue 765 <https://github.com/aws/aws-cli/issues/765>`__)
* bugfix:``aws cloudtrail``: Fix a bug with python3 when creating a subscription (`issue 773 <https://github.com/aws/aws-cli/pull/773>`__)
* bugfix:Shorthand: Fix issue where certain shorthand parameters were not parsing to the correct types (`issue 776 <https://github.com/aws/aws-cli/pull/776>`__)
* bugfix:``aws cloudformation``: Fix issue with parameter casing for the ``NotificationARNs`` parameter (`botocore issue 283 <https://github.com/boto/botocore/pull/283>`__)


1.3.10
======

* feature:``aws cloudformation``: Add support for updated API


1.3.9
=====

* feature:``aws sqs``: Add support for message attributes
* bugfix:``aws s3api``: Fix issue when setting metadata on an S3 object (`issue 356 <https://github.com/aws/aws-cli/issues/356>`__)


1.3.8
=====

* feature:``aws autoscaling``: Add support for launching Dedicated Instances in Amazon Virtual Private Cloud
* feature:``aws elasticache``: Add support to backup and restore for Redis clusters
* feature:``aws dynamodb``: Update ``aws dynamodb`` command to the latest API


1.3.7
=====

* bugfix:Output Format: Fix issue with encoding errors when using text and table output and redirecting to a pipe or file (`issue 742 <https://github.com/aws/aws-cli/issues/742>`__)
* bugfix:``aws s3``: Fix issue with sync re-uploading certain files (`issue 749 <https://github.com/aws/aws-cli/issues/749>`__)
* bugfix:Text Output: Fix issue with inconsistent text output based on order (`issue 751 <https://github.com/aws/aws-cli/issues/751>`__)
* bugfix:``aws datapipeline``: Fix issue for aggregating keys into a list when calling ``aws datapipeline get-pipeline-definition`` (`issue 750 <https://github.com/aws/aws-cli/pull/750>`__)
* bugfix:``aws s3``: Fix issue when running out of disk space during ``aws s3`` transfers (`issue 739 <https://github.com/aws/aws-cli/issues/739>`__)
* feature:``aws s3 sync``: Add ``--size-only`` param to the ``aws s3 sync`` command (`issue 472 <https://github.com/aws/aws-cli/issues/473>`__, `issue 719 <https://github.com/aws/aws-cli/pull/719>`__)


1.3.6
=====

* bugfix:``aws cloudtrail``: Fix issue when using ``create-subscription`` command (`issue botocore 268 <https://github.com/boto/botocore/pull/268>`__)
* feature:``aws cloudsearch``: Amazon CloudSearch has moved out of preview (`issue 730 <https://github.com/aws/aws-cli/pull/730>`__)
* bugfix:``aws s3 website``: Fix issue where ``--error-document`` was being ignored in certain cases (`issue 714 <https://github.com/aws/aws-cli/pull/714>`__)


1.3.5
=====

* feature:``aws opsworks``: Update ``aws opsworks`` model to the latest version
* bugfix:Pagination: Fix issue with ``--max-items`` with ``aws route53``, ``aws iam``, and ``aws ses`` (`issue 729 <https://github.com/aws/aws-cli/pull/729>`__)
* bugfix:``aws s3``: Fix issue with fips-us-gov-west-1 endpoint (`issue botocore 265 <https://github.com/boto/botocore/pull/265>`__)
* bugfix:Table Output: Fix issue when displaying unicode characters in table output (`issue 721 <https://github.com/aws/aws-cli/pull/721>`__)
* bugfix:``aws s3``: Fix regression when syncing files with whitespace (`issue 706 <https://github.com/aws/aws-cli/issues/706>`__, `issue 718 <https://github.com/aws/aws-cli/issues/718>`__)


1.3.4
=====

* bugfix:``aws ec2``: Fix issue with EC2 model resulting in responses not being parsed.


1.3.3
=====

* feature:``aws ec2``: Add support for Amazon VPC peering
* feature:``aws redshift``: Add support for the latest Amazon Redshift API
* feature:``aws cloudsearch``: Add support for the latest Amazon CloudSearch API
* bugfix:``aws cloudformation``: Documentation updates
* bugfix:Argument Parsing: Fix issue when list arguments were not being decoded to unicode properly (`issue 711 <https://github.com/aws/aws-cli/issues/711>`__)
* bugfix:Output: Fix issue when invalid output type was provided in a config file or environment variable (`issue 600 <https://github.com/aws/aws-cli/issues/600>`__)


1.3.2
=====

* bugfix:``aws datapipeline``: Fix issue when serializing pipeline definitions containing list elements (`issue 705 <https://github.com/aws/aws-cli/issues/705>`__)
* bugfix:``aws s3``: Fix issue when recursively removing keys containing control characters (`issue 675 <https://github.com/aws/aws-cli/issues/675>`__)
* bugfix:``aws s3``: Honor ``--no-verify-ssl`` in high level ``aws s3`` commands (`issue 696 <https://github.com/aws/aws-cli/issues/696>`__)


1.3.1
=====

* bugfix:Parameters: Fix issue parsing with CLI parameters of type ``long`` (`issue 693 <https://github.com/aws/aws-cli/pull/693/files>`__)
* bugfix:Pagination: Fix issue where ``--max-items`` in pagination was always assumed to be an integer (`issue 689 <https://github.com/aws/aws-cli/pull/689>`__)
* feature:``aws elb``: Add support for AccessLog
* bugfix:Bundled Installer: Allow creation of bundled installer with ``pip 1.5`` (`issue 691 <https://github.com/aws/aws-cli/issues/691>`__)
* bugfix:``aws s3``: Fix issue when copying objects using ``aws s3 cp`` with key names containing ``+`` characters (`issue #614 <https://github.com/aws/aws-cli/issues/614>`__)
* bugfix:``ec2 create-snapshot``: Remove ``Tags`` key from output response (`issue 247 <https://github.com/boto/botocore/pull/247>`__)
* bugfix:``aws s3``: ``aws s3`` commands should not be requiring regions (`issue 681 <https://github.com/aws/aws-cli/issues/681>`__)
* bugfix:``CLI Arguments``: Fix issue where unicode command line arguments were not being handled correctly (`issue 679 <https://github.com/aws/aws-cli/pull/679>`__)


1.3.0
=====

* bugfix:``aws s3``: Fix issue where S3 downloads would hang in certain cases and could not be interrupted (`issue 650 <https://github.com/aws/aws-cli/issues/650>`__, `issue 657 <https://github.com/aws/aws-cli/issues/657>`__)
* bugfix:``aws s3``: Support missing canned ACLs when using the ``--acl`` parameter (`issue 663 <https://github.com/aws/aws-cli/issues/663>`__)
* bugfix:``aws rds describe-engine-default-parameters``: Fix pagination issue when calling ``aws rds describe-engine-default-parameters`` (`issue 607 <https://github.com/aws/aws-cli/issues/607>`__)
* bugfix:``aws cloudtrail``: Merge existing SNS topic policy with the existing AWS CloudTrail policy instead of overwriting the default topic policy
* bugfix:``aws s3``: Fix issue where streams were not being rewound when encountering 307 redirects with multipart uploads (`issue 544 <https://github.com/aws/aws-cli/issues/544>`__)
* bugfix:``aws elb``: Fix issue with documentation errors in ``aws elb help`` (`issue 622 <https://github.com/aws/aws-cli/issues/622>`__)
* bugfix:JSON Parameters: Add a more clear error message when parsing invalid JSON parameters (`issue 639 <https://github.com/aws/aws-cli/pull/639>`__)
* bugfix:``aws s3api``: Properly handle null inputs (`issue 637 <https://github.com/aws/aws-cli/issues/637>`__)
* bugfix:Argument Parsing: Handle files containing JSON with leading and trailing spaces (`issue 640 <https://github.com/aws/aws-cli/pull/640>`__)


1.2.13
======

* feature:``aws route53``: Update ``aws route53`` command to support string-match health checks and the UPSERT action for the ``aws route53 change-resource-record-sets`` command
* bugfix:Command Completion: Don't show tracebacks on SIGINT (`issue 628 <https://github.com/aws/aws-cli/issues/628>`__)
* bugfix:Docs: Don't duplicate enum values in reference docs (`issue 632 <https://github.com/aws/aws-cli/pull/632>`__)
* bugfix:``aws s3``: Don't require ``s3 (`issue 626 <https://github.com/aws/aws-cli/pull/626>`__)


1.2.12
======

* feature:``aws configure``: Add support for ``configure get`` and ``configure set`` command which allow you to set and get configuration values from the AWS config file (`issue 602 <https://github.com/aws/aws-cli/issues/602`__)
* bugfix:``aws s3``: Fix issue with Amazon S3 downloads on certain OSes (`issue 619 <https://github.com/aws/aws-cli/issues/619`__)


1.2.11
======

* feature:``aws s3``: Add support for the ``--recursive`` option in the ``aws s3 ls`` command (`issue 465 <https://github.com/aws/aws-cli/issues/465`)
* feature:Config: Add support for the ``AWS_CA_BUNDLE`` environment variable so that users can specify an alternate path to a cert bundle (`issue 586 <https://github.com/aws/aws-cli/pull/586>`__)
* feature:Configuration: Add ``metadata_service_timeout`` and ``metadata_service_num_attempts`` config parameters to control behavior when retrieving credentials using an IAM role (`issue 597 <https://github.com/aws/aws-cli/pull/597>`__)
* bugfix:``aws s3``: Retry intermittent ``aws s3`` download failures including socket timeouts and content length mismatches (`issue 594 <https://github.com/aws/aws-cli/pull/594>`__)
* bugfix:``aws s3api``: Fix response parsing of ``aws s3api get-bucket-location`` (`issue 345 <https://github.com/aws/aws-cli/issues/345>`__)
* bugfix:``aws elastictranscoder``: Fix response parsing of the ``aws elastictranscoder`` command (`issue 207 <https://github.com/boto/botocore/pull/207>`__)
* feature:``aws elasticache``: Update ``aws elasticache`` command to not require certain parameters


1.2.10
======

* feature:``aws autoscaling``: Add support for creating launch configuration or Auto Scaling groups using an Amazon EC2 instance, for attaching Amazon EC2 isntances to an existing Auto Scaling group, and for describing the limits on the Auto Scaling resources in the ``aws autoscaling`` command
* feature:Documentation: Update documentation in the ``aws support`` command
* bugfix:``aws ec2``: Allow the ``--protocol`` customization for ``CreateNetworkAclEntry`` to also work for ``ReplaceNetworkAclEntry`` (`issue 559 <https://github.com/aws/aws-cli/issues/559>`__)
* bugfix:``aws s3``: Remove one second delay when tasks are finished running for several ``aws s3`` subcommands (`issue 551 <https://github.com/aws/aws-cli/pull/551>`__)
* bugfix:Documentation: Fix bug in shorthand documentation generation that prevented certain nested structure parameters from being fully documented (`issue 579 <https://github.com/aws/aws-cli/pull/579>`__)
* bugfix:Config: Update default timeout from .1 second to 1 second (`botocore issue 202 <https
* bugfix:``aws rds``: Removed filter parameter in RDS operations (`issue 515 <https
* bugfix:Endpoints: Fixed region endpoint for the ``aws kinesis`` command (`botocore issue 194 <https


1.2.9
=====

* bugfix:``aws s3``: Fix issue 548 where ``--include/--exclude`` arguments for various ``aws s3`` commands were prepending the CWD instead of the source directory for filter patterns
* bugfix:``aws s3``: Fix issue 552 where a remote location without a trailing slash would show a malformed XML error when using various  ``aws s3`` commands
* feature:``aws emr``: Add support for tagging in ``aws emr`` command
* feature:``aws cloudfront``: Add support for georestrictions in ``aws cloudfront`` command
* feature:``aws elastictranscoder``: Add support for new audio compression codecs in the ``aws elastictranscoder`` command
* feature:``aws cloudtrail``: Update the ``aws cloudtrail`` command to the latest API
* feature:Endpoints: Add support for the new China (Beijing) Region. Note now includes support for the newly announced China (Beijing) Region, the service endpoints will not be accessible until the Region’s limited preview is launched in early 2014. To find out more about the new Region and request a limited preview account, please visit http://www.amazonaws.cn/.


1.2.8
=====

* feature:``aws s3``: Add support for parallel multipart uploads when copying objects between Amazon S3 locations when using the ``aws s3`` command (issue 538)
* bugfix:``aws cloudformation``: Fix issue 542 where the ``---stack-policy-url`` will parameter will not interpret its value as a URL when using the ``aws cloudformation create-stack`` command
* feature:``aws dynamodb``: Add support for global secondary indexes in the ``aws dynamodb`` command
* feature:``aws kinesis``: Add support for the ``aws kinesis`` command
* feature:``aws elasticbeanstalk``: Add support for worker roles in the ``aws elasticbeanstalk`` command
* feature:``aws emr``: Add support for resource tagging and other new operations in the ``aws emr`` command
* feature:``aws opsworks``: Add support for resource-based permissions in the ``aws opsworks`` command
* feature:``aws elasticache``: Update the ``aws elasticache`` command to signature version 4


1.2.7
=====

* bugfix:``aws ec2``: Allow tcp, udp, icmp, all for ``--protocol`` param of the ``ec2 create-network-acl-entry`` command (`issue 508 <https://github.com/aws/aws-cli/issues/508>`__)
* bugfix:``aws s3``: Fix bug when filtering ``s3 ``--include/--exclude`` params (`issue 531 <https://github.com/aws/aws-cli/pull/531>`__)
* bugfix:``aws sns``: Fix an issue with map type parameters raising uncaught exceptions in commands such as `sns create-platform-application` (`issue 407 <https://github.com/aws/aws-cli/issues/407>`__)
* bugfix:``aws ec2``: Fix an issue when both ``--private-ip-address`` and ``--associate-public-ip-address`` are specified in the ``ec2 run-instances`` command (`issue 520 <https://github.com/aws/aws-cli/issues/520>`__)
* bugfix:Output: Fix an issue where ``--output text`` was not providing a starting identifier for certain rows (`issue 516 <https://github.com/aws/aws-cli/pull/516>`__)
* feature:``aws support``: Update the ``support`` command to the latest version
* feature:Output: Update the ``--query`` syntax to support flattening sublists (`boto/jmespath#20 <https://github.com/boto/jmespath/pull/20>`__)


1.2.6
=====

* bugfix:Endpoints: Allow ``--endpoint-url`` to work with the ``aws s3`` command (`issue 469 <https://github.com/aws/aws-cli/pull/469>`__)
* bugfix:``aws cloudtrail``: Fix issue with ``aws cloudtrail [create|update]-subscription`` not honoring the ``--profile`` argument (`issue 494 <https://github.com/aws/aws-cli/issues/494>`__)
* bugfix:``aws ec2``: Fix issue with ``--associate-public-ip-address`` when a ``--subnet-id`` is provided (`issue 501 <https://github.com/aws/aws-cli/issues/501>`__)
* bugfix:Argument Parsing: Don't require key names for structures of single scalar values (`issue 484 <https://github.com/aws/aws-cli/issues/484>`__)
* bugfix:``aws s3``: Fix issue with symlinks silently failing during ``s3 sync/cp`` (`issue 425 <https://github.com/aws/aws-cli/issues/425>`__ and `issue 487 <https://github.com/aws/aws-cli/issues/487>`__)
* feature:Configuration: Add a ``aws configure list`` command to show where the configuration values are sourced from (`issue 513 <https://github.com/aws/aws-cli/pull/513>`__)
* feature:``aws cloudwatch``: Update ``cloudwatch`` command to use Signature Version 4
* feature:``aws ec2``: Update ``ec2`` command to support enhanced network capabilities and pagination controls for ``describe-instances`` and ``describe-tags``
* feature:``aws rds``: Add support in ``rds`` command for copying DB snapshots from one AWS region to another


1.2.5
=====

* feature:``aws cloudtrail``: Add support for AWS Cloudtrail
* feature:``aws iam``: Add support for identity federation using SAML 2.0 in the ``aws iam`` command
* feature:``aws redshift``: Update the ``aws redshift`` command to include several new features related to event notifications, encryption, audit logging, data load from external hosts, WLM configuration, and database distribution styles and functions
* feature:``aws ec2``: Add a ``--associate-public-ip-address`` option to the ``ec2 run-instances`` command (`issue 479 <https://github.com/aws/aws-cli/issues/479>`__)
* bugfix:``aws s3``: Add an ``s3 website`` command for configuring website configuration for an S3 bucket (`issue 482 <https://github.com/aws/aws-cli/pull/482>`__)


1.2.4
=====

* bugfix:``aws s3``: Fix an issue with the ``s3`` command when using GovCloud regions (boto/botocore#170)
* bugfix:``aws s3``: Fix an issue with the ``s3 ls`` command making an extra query at the root level (issue 439)
* bugfix:``aws s3``: Add detailed error message when unable to decode local filenames during an ``s3 sync`` (issue 378)
* bugfix:``aws ec2``: Support ``-1`` and ``all`` as valid values to the ``--protocol`` argument to ``ec2 authorize-security-group-ingress`` and ``ec2 authorize-security-group-egress`` (issue 460)
* feature:``aws s3``: Log the reason why a file is synced when using the ``s3 sync`` command
* bugfix:``aws s3``: Fix an issue when uploading large files on low bandwidth networks (issue 454)
* bugfix:Argument Parsing: Fix an issue with parsing shorthand boolean argument values (issue 477)
* bugfix:CloudSearch: Fix an issue with the ``cloudsearch`` command missing a required attribute (boto/botocore#175)
* bugfix:Response Parsing: Fix an issue with parsing XML response for ``ec2 describe-instance-attribute`` (boto/botocore#174)
* feature:``aws cloudformation``: Update ``cloudformation`` command to support new features for stacks and templates
* feature:``aws storagegateway``: Update ``storagegateway`` command to support a new gateway configuration, Gateway-Virtual Tape Library (Gateway-VTL)
* feature:``aws elb``: Update ``elb`` command to support cross-zone load balancing, which changes the way that Elastic Load Balancing (ELB) routes incoming requests


1.2.3
=====

* feature:Configuration: Add a new ``configure`` command that allows users to interactively specify configuration values (pull request 455)
* feature:``aws emr``: Add support for new EMR APIs, termination of specific cluster instances, and unlimited EMR steps
* feature:``aws cloudfront``: Update Amazon CloudFront command to the 2013-09-27 API version
* bugfix:``aws ec2``: Fix issue where Expires timestamp in bundle-instance policy is incorrect (issue 456)
* bugfix:HTTP: The requests library is now vendored in botocore (at version 2.0.1)
* bugfix:Auth: Fix an issue where timestamps used for Signature Version 4 weren't being refreshed (boto/botocore#162)


1.2.2
=====

* bugfix:``aws s3``: Fix an issue causing ``s3 sync`` with the ``--delete`` incorrectly deleting files (issue 440)
* bugfix:Output: Fix an issue with ``--output text`` combined with paginated results (boto/botocore#165)
* bugfix:Output: Fix a bug in text output when an empty list is encountered (issue 446)


1.2.1
=====

* feature:``aws directconnect``: Update the AWS Direct Connect command to support the latest features
* bugfix:Arguments: Fix text output with single scalar value (issue 428)
* bugfix:Input: Fix shell quoting for ``PAGER``/``MANPAGER`` environment variable (issue 429)
* bugfix:Endpoints: --endpoint-url is explicitly used for URL of remote service (boto/botocore#163)
* bugfix:``aws ec2``: Fix an validation error when using ``--ip-permissions`` and ``--group-id`` together (issue 435)


1.2.0
=====

* feature:``aws elastictranscoder``: Update Amazon Elastic Transcoder command with audio transcoding features
* feature:Output: Improve text output (``--output text``) to have a consistent output structure
* feature:Output: Add ``--query`` argument that allows you to specify output data using a JMESPath expression
* feature:HTTP: Upgrade requests library to 2.0.0
* feature:``aws redshift``: Update Amazon Redshift region configuration to include ``ap-southeast-1``  and ``ap-southeast-2``
* feature:``aws s3``: Update Amazon S3 region configuration to include ``fips-us-gov-west-1``
* feature:Install: Add a bundled installer for the CLI which bundles all necessary dependencies (does not require pip)
* bugfix:Tab Completion: Fix an issue with ZSH tab completion (issue 411)
* bugfix:``aws s3``: Fix an issue with S3 requests timing out (issue 401)
* bugfix:``aws s3api``: Fix an issue with ``s3api delete-objects`` not providing the ``Content-MD5`` header (issue 400)


1.1.2
=====

* feature:``aws ec2``: Update the Amazon EC2 command to support Reserved Instance instance type modifications
* feature:``aws opsworks``: Update the AWS OpsWorks command to support new resource management features
* bugfix:``aws s3``: Fix an issue when transferring files on different drives on Windows
* bugfix:Help: Fix an issue that caused interactive help to emit control characters on certain Linux distributions


1.1.1
=====

* feature:``aws cloudfront``: Update the Amazon CloudFront command to support the latest API version 2013-08-26
* feature:``aws autoscaling``: Update the Auto Scaling client to support public IP address association of instances
* feature:``aws swf``: Update Amazon SWF to support signature version 4
* feature:``aws rds``: Update Amazon RDS with a new subcommand, ``add-source-identifier-to-subscription``


1.1.0
=====

* feature:``aws s3``: Update the ``s3`` commands to support the setting for how objects are stored in Amazon S3
* feature:``aws ec2``: Update the Amazon EC2 command to support the latest API version (2013-08-15)
* bugfix:``aws s3``: Fix an issue causing excessive CPU utilization in some scenarios where many files were being uploaded
* bugfix:``aws s3``: Fix a memory growth issue with ``s3`` copying and syncing of files
* bugfix:Install: Fix an issue caused by a conflict with a dependency and Python 3.x that caused installation to fail

