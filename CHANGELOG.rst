=========
CHANGELOG
=========

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

