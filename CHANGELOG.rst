=========
CHANGELOG
=========

2.24.12
=======

* api-change:``iot``: AWS IoT - AWS IoT Device Defender adds support for a new Device Defender Audit Check that monitors device certificate age and custom threshold configurations for both the new device certificate age check and existing device certificate expiry check.
* api-change:``codebuild``: Adding "reportArns" field in output of BatchGetBuildBatches API. "reportArns" is an array that contains the ARNs of reports created by merging reports from builds associated with the batch build.
* api-change:``devicefarm``: Add an optional configuration to the ScheduleRun and CreateRemoteAccessSession API to set a device level http/s proxy.
* enhancement:openssl: Update bundled OpenSSL version to 1.1.1zb for Linux installers
* api-change:``taxsettings``: PutTaxRegistration API changes for Egypt, Greece, Vietnam countries
* api-change:``ec2``: Adds support for time-based EBS-backed AMI copy operations. Time-based copy ensures that EBS-backed AMIs are copied within and across Regions in a specified timeframe.


2.24.11
=======

* api-change:``elasticache``: Documentation update, adding clarity and rephrasing.
* api-change:``bedrock-runtime``: This release adds Reasoning Content support to Converse and ConverseStream APIs
* api-change:``bedrock-agent``: This release improves support for newer models in Amazon Bedrock Flows.
* api-change:``bedrock-agent-runtime``: Adding support for ReasoningContent fields in Pre-Processing, Post-Processing and Orchestration Trace outputs.
* api-change:``elastic-inference``: The elastic-inference client has been removed following the deprecation of the service.


2.24.10
=======

* api-change:``bedrock-agent``: Introduce a new parameter which represents the user-agent header value used by the Bedrock Knowledge Base Web Connector.
* enhancement:Python: Update bundled Python interpreter version to 3.12.9
* api-change:``appstream``: Added support for Certificate-Based Authentication on AppStream 2.0 multi-session fleets.


2.24.9
======

* api-change:``rds``: CloudWatch Database Insights now supports Amazon RDS.
* api-change:``workspaces-web``: Add support for toolbar configuration under user settings.
* api-change:``codebuild``: Add webhook status and status message to AWS CodeBuild webhooks
* api-change:``sagemaker``: Added new capability in the UpdateCluster operation to remove instance groups from your SageMaker HyperPod cluster.
* api-change:``license-manager-user-subscriptions``: Updates entity to include Microsoft RDS SAL as a valid type of user subscription.
* api-change:``guardduty``: Reduce the minimum number of required attack sequence signals from 2 to 1


2.24.8
======

* api-change:``location``: Adds support for larger property maps for tracking and geofence positions changes. It increases the maximum number of items from 3 to 4, and the maximum value length from 40 to 150.
* api-change:``network-firewall``: This release introduces Network Firewall's Automated Domain List feature. New APIs include UpdateFirewallAnalysisSettings, StartAnalysisReport, GetAnalysisReportResults, and ListAnalysisReports. These allow customers to enable analysis on firewalls to identify and report frequently accessed domain.
* api-change:``sesv2``: This release adds the ability for outbound email sent with SES to preserve emails to a Mail Manager archive.
* api-change:``ecs``: This is a documentation only release for Amazon ECS that supports the CPU task limit increase.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``sagemaker``: Adds r8g instance type support to SageMaker Realtime Endpoints
* api-change:``mailmanager``: This release adds additional metadata fields in Mail Manager archive searches to show email source and details about emails that were archived when being sent with SES.
* api-change:``codepipeline``: Add environment variables to codepipeline action declaration.


2.24.7
======

* enhancement:protocols: Added support for multiple protocols within a service based on performance priority.
* api-change:``batch``: This documentation-only update corrects some typos.
* api-change:``medialive``: Adds support for creating CloudWatchAlarmTemplates for AWS Elemental MediaTailor Playback Configuration resources.
* api-change:``emr-containers``: EMR on EKS StartJobRun Api will be supporting the configuration of log storage in AWS by using "managedLogs" under "MonitoringConfiguration".
* enhancement:protocol: The CLI no longer validates payload size for event streams. This is to facilitate varying payload requirements across AWS services.


2.24.6
======

* api-change:``dms``: Support replicationConfigArn in DMS DescribeApplicableIndividualAssessments API.
* api-change:``timestream-influxdb``: This release introduces APIs to manage DbClusters and adds support for read replicas
* api-change:``amplify``: Add ComputeRoleArn to CreateApp, UpdateApp, CreateBranch, and UpdateBranch, allowing caller to specify a role to be assumed by Amplify Hosting for server-side rendered applications.


2.24.5
======

* api-change:``codebuild``: Added test suite names to test case metadata
* api-change:``connect``: Release Notes: 1) Analytics API enhancements: Added new ListAnalyticsDataLakeDataSets API. 2)  Onboarding API Idempotency: Adds ClientToken to instance creation and management APIs to support idempotency.
* api-change:``workspaces-thin-client``: Update Environment and Device name field definitions
* api-change:``rds-data``: Add support for Stop DB feature.
* api-change:``dms``: Introduces premigration assessment feature to DMS Serverless API for start-replication and describe-replications
* api-change:``s3``: Added support for Content-Range header in HeadObject response.
* api-change:``wafv2``: The WAFv2 API now supports configuring data protection in webACLs.


2.24.4
======

* api-change:``acm-pca``: Private Certificate Authority (PCA) documentation updates
* api-change:``ecs``: This is a documentation only release to support migrating Amazon ECS service ARNs to the long ARN format.
* api-change:``sagemaker``: Adds additional values to the InferenceAmiVersion parameter in the ProductionVariant data type.
* api-change:``fis``: Adds auto-pagination for the following operations: ListActions, ListExperimentTemplates, ListTargetAccountConfigurations, ListExperiments, ListExperimentResolvedTargets, ListTargetResourceTypes. Reduces length constraints of prefixes for logConfiguration and experimentReportConfiguration.
* api-change:``accessanalyzer``: This release introduces the getFindingsStatistics API, enabling users to retrieve aggregated finding statistics for IAM Access Analyzer's external access and unused access analysis features. Updated service API and documentation.
* api-change:``storagegateway``: This release adds support for generating cache reports on S3 File Gateways for files that fail to upload.


2.24.3
======

* api-change:``fsx``: Support for in-place Lustre version upgrades
* api-change:``b2bi``: Allow spaces in the following fields in the Partnership resource: ISA 06 - Sender ID, ISA 08 - Receiver ID, GS 02 - Application Sender Code, GS 03 - Application Receiver Code
* api-change:``polly``: Added support for the new voice - Jasmine (en-SG). Jasmine is available as a Neural voice only.
* api-change:``bedrock-agent-runtime``: This releases adds the additionalModelRequestFields field to the InvokeInlineAgent operation. Use additionalModelRequestFields to specify  additional inference parameters for a model beyond the base inference parameters.
* api-change:``bedrock-agent``: This releases adds the additionalModelRequestFields field to the CreateAgent and UpdateAgent operations. Use additionalModelRequestFields to specify  additional inference parameters for a model beyond the base inference parameters.
* api-change:``opensearchserverless``: Custom OpenSearchServerless Entity ID for SAML Config.
* api-change:``codebuild``: Add note for the RUNNER_BUILDKITE_BUILD buildType.
* api-change:``medialive``: Adds a RequestId parameter to all MediaLive Workflow Monitor create operations.  The RequestId parameter allows idempotent operations.


2.24.2
======

* api-change:``pi``: Documentation only update for RDS Performance Insights dimensions for execution plans and locking analysis.
* api-change:``acm-pca``: Private Certificate Authority service now supports Partitioned CRL as a revocation configuration option.
* api-change:``appsync``: Add support for operation level caching
* api-change:``ec2``: Adding support for the new fullSnapshotSizeInBytes field in the response of the EC2 EBS DescribeSnapshots API. This field represents the size of all the blocks that were written to the source volume at the time the snapshot was created.


2.24.1
======

* api-change:``connect``: Updated the CreateContact API documentation to indicate that it only applies to EMAIL contacts.
* api-change:``apigatewayv2``: Documentation updates for Amazon API Gateway
* api-change:``cloudfront``: Doc-only update that adds defaults for CloudFront VpcOriginEndpointConfig values.
* api-change:``dms``: New vendors for DMS Data Providers: DB2 LUW and DB2 for z/OS


2.24.0
======

* api-change:``ecr``: Adds support to handle the new basic scanning daily quota.
* api-change:``pi``: Adds documentation for dimension groups and dimensions to analyze locks for Database Insights.
* api-change:``eks``: Introduce versionStatus field to take place of status field in EKS DescribeClusterVersions API
* api-change:``transcribe``: This release adds support for the Clinical Note Template Customization feature for the AWS HealthScribe APIs within Amazon Transcribe.
* feature:``emr-containers``: Add custom ``create-role-associations`` and ``delete-role-associations`` commands to create/delete role associations for EMR service accounts and provided IAM role.
* api-change:``mediaconvert``: This release adds support for Animated GIF output, forced chroma sample positioning metadata, and Extensible Wave Container format


2.23.15
=======

* api-change:``cost-optimization-hub``: This release enables AWS Cost Optimization Hub to show cost optimization recommendations for Amazon Auto Scaling Groups, including those with single and mixed instance types.
* api-change:``s3``: Updated list of the valid AWS Region values for the LocationConstraint parameter for general purpose buckets.
* api-change:``connectcases``: This release adds the ability to conditionally require fields on a template. Check public documentation for more information.
* api-change:``cloudformation``: We added 5 new stack refactoring APIs: CreateStackRefactor, ExecuteStackRefactor, ListStackRefactors, DescribeStackRefactor, ListStackRefactorActions.


2.23.14
=======

* api-change:``rds``: Documentation updates to clarify the description for the parameter AllocatedStorage for the DB cluster data type, the description for the parameter DeleteAutomatedBackups for the DeleteDBCluster API operation, and removing an outdated note for the CreateDBParameterGroup API operation.


2.23.13
=======

* api-change:``neptune-graph``: Added argument to `list-export` to filter by graph ID
* api-change:``iam``: This release adds support for accepting encrypted SAML assertions. Customers can now configure their identity provider to encrypt the SAML assertions it sends to IAM.
* api-change:``qbusiness``: Adds functionality to enable/disable a new Q Business Chat orchestration feature. If enabled, Q Business can orchestrate over datasources and plugins without the need for customers to select specific chat modes.
* api-change:``sagemaker``: IPv6 support for Hyperpod clusters
* api-change:``dms``: Introduces TargetDataSettings with the TablePreparationMode option available for data migrations.
* api-change:``datasync``: Doc-only update to provide more information on using Kerberos authentication with SMB locations.


2.23.12
=======

* api-change:``mediatailor``: Add support for CloudWatch Vended Logs which allows for delivery of customer logs to CloudWatch Logs, S3, or Firehose.


2.23.11
=======

* api-change:``codebuild``: Added support for CodeBuild self-hosted Buildkite runner builds
* api-change:``rds``: Updates to Aurora MySQL and Aurora PostgreSQL API pages with instance log type in the create and modify DB Cluster.
* api-change:``bedrock-agent-runtime``: This change is to deprecate the existing citation field under RetrieveAndGenerateStream API response in lieu of GeneratedResponsePart and RetrievedReferences
* api-change:``amp``: Add support for sending metrics to cross account and CMCK AMP workspaces through RoleConfiguration on Create/Update Scraper.
* api-change:``geo-routes``: The OptimizeWaypoints API now supports 50 waypoints per request (20 with constraints like AccessHours or AppointmentTime). It adds waypoint clustering via Clustering and ClusteringIndex for better optimization. Also, total distance validation is removed for greater flexibility.
* api-change:``sagemaker``: This release introduces a new valid value in InstanceType parameter: p5en.48xlarge, in ProductionVariant.


2.23.10
=======

* enhancement:awscrt: Update awscrt version requirement to 0.23.8
* api-change:``ecr-public``: Temporarily updating dualstack endpoint support
* api-change:``s3tables``: You can now use the CreateTable API operation to create tables with schemas by adding an optional metadata argument.
* api-change:``ecr``: Temporarily updating dualstack endpoint support
* api-change:``mediatailor``: Adds options for configuring how MediaTailor conditions ads before inserting them into the content stream. Based on the new settings, MediaTailor will either transcode ads to match the content stream as it has in the past, or it will insert ads without first transcoding them.
* api-change:``bedrock-agent-runtime``: Add a 'reason' field to InternalServerException
* api-change:``qbusiness``: Added APIs to manage QBusiness user subscriptions
* api-change:``appstream``: Add support for managing admin consent requirement on selected domains for OneDrive Storage Connectors in AppStream2.0.
* api-change:``verifiedpermissions``: Adds Cedar JSON format support for entities and context data in authorization requests


2.23.9
======

* api-change:``ecr``: Add support for Dualstack and Dualstack-with-FIPS Endpoints
* api-change:``bcm-pricing-calculator``: Added ConflictException error type in DeleteBillScenario, BatchDeleteBillScenarioCommitmentModification, BatchDeleteBillScenarioUsageModification, BatchUpdateBillScenarioUsageModification, and BatchUpdateBillScenarioCommitmentModification API operations.
* api-change:``ecr-public``: Add support for Dualstack Endpoints
* api-change:``s3``: Change the type of MpuObjectSize in CompleteMultipartUploadRequest from int to long.
* api-change:``mailmanager``: This release includes a new feature for Amazon SES Mail Manager which allows customers to specify known addresses and domains and make use of those in traffic policies and rules actions to distinguish between known and unknown entries.


2.23.8
======

* api-change:``firehose``: For AppendOnly streams, Firehose will automatically scale to match your throughput.
* api-change:``deadline``: feature: Deadline: Add support for limiting the concurrent usage of external resources, like floating licenses, using limits and the ability to constrain the maximum number of workers that work on a job
* api-change:``appsync``: Add stash and outErrors to EvaluateCode/EvaluateMappingTemplate response
* api-change:``ec2``: This release changes the CreateFleet CLI and SDK's such that if you do not specify a client token, a randomly generated token is used for the request to ensure idempotency.
* api-change:``timestream-influxdb``: Adds 'allocatedStorage' parameter to UpdateDbInstance API that allows increasing the database instance storage size and 'dbStorageType' parameter to UpdateDbInstance API that allows changing the storage type of the database instance
* api-change:``datasync``: AWS DataSync now supports the Kerberos authentication protocol for SMB locations.


2.23.7
======

* api-change:``iot``: Raised the documentParameters size limit to 30 KB for AWS IoT Device Management - Jobs.
* api-change:``mediaconvert``: This release adds support for dynamic audio configuration and the ability to disable the deblocking filter for h265 encodes.
* bugfix:Signing: No longer sign transfer-encoding header for SigV4
* api-change:``bedrock-agent``: Add support for the prompt caching feature for Bedrock Prompt Management
* api-change:``s3control``: Minor fix to ARN validation for Lambda functions passed to S3 Batch Operations


2.23.6
======

* api-change:``sso-oidc``: Fixed typos in the descriptions.
* api-change:``healthlake``: Added new authorization strategy value 'SMART_ON_FHIR' for CreateFHIRDatastore API to support Smart App 2.0
* api-change:``cloudtrail``: This release introduces the SearchSampleQueries API that allows users to search for CloudTrail Lake sample queries.
* api-change:``eks``: Adds support for UpdateStrategies in EKS Managed Node Groups.
* api-change:``ssm``: Systems Manager doc-only update for January, 2025.
* api-change:``transfer``: Added CustomDirectories as a new directory option for storing inbound AS2 messages, MDN files and Status files.


2.23.5
======

* api-change:``ec2``: Added "future" allocation type for future dated capacity reservation


2.23.4
======

* api-change:``workspaces-thin-client``: Rename WorkSpaces Web to WorkSpaces Secure Browser
* api-change:``bedrock-agent-runtime``: Adds multi-turn input support for an Agent node in an Amazon Bedrock Flow
* api-change:``medialive``: AWS Elemental MediaLive adds a new feature, ID3 segment tagging, in CMAF Ingest output groups. It allows customers to insert ID3 tags into every output segment, controlled by a newly added channel schedule action Id3SegmentTagging.
* api-change:``glue``: Docs Update for timeout changes


2.23.3
======

* api-change:``quicksight``: Added `DigitGroupingStyle` in ThousandsSeparator to allow grouping by `LAKH`( Indian Grouping system ) currency. Support LAKH and `CRORE` currency types in Column Formatting.
* api-change:``connect``: Added DeleteContactFlowVersion API and the CAMPAIGN flow type
* api-change:``batch``: Documentation-only update: clarified the description of the shareDecaySeconds parameter of the FairsharePolicy data type, clarified the description of the priority parameter of the JobQueueDetail data type.
* api-change:``cognito-idp``: corrects the dual-stack endpoint configuration for cognitoidp
* api-change:``iotsitewise``: AWS IoT SiteWise now supports ingestion and querying of Null (all data types) and NaN (double type) values of bad or uncertain data quality. New partial error handling prevents data loss during ingestion. Enabled by default for new customers; existing customers can opt-in.
* api-change:``logs``: Documentation-only update to address doc errors
* api-change:``sns``: This release adds support for the topic attribute FifoThroughputScope for SNS FIFO topics. For details, see the documentation history in the Amazon Simple Notification Service Developer Guide.
* api-change:``emr-serverless``: Increasing entryPoint in SparkSubmit to accept longer script paths. New limit is 4kb.


2.23.2
======

* api-change:``bedrock-runtime``: Allow hyphens in tool name for Converse and ConverseStream APIs
* api-change:``sagemaker``: Correction of docs for  "Added support for ml.trn1.32xlarge instance type in Reserved Capacity Offering"
* api-change:``notifications``: Added support for Managed Notifications, integration with AWS Organization and added aggregation summaries for Aggregate Notifications
* api-change:``detective``: Doc only update for Detective documentation.
* api-change:``ec2``: Release u7i-6tb.112xlarge, u7i-8tb.112xlarge, u7inh-32tb.480xlarge, p5e.48xlarge, p5en.48xlarge, f2.12xlarge, f2.48xlarge, trn2.48xlarge instance types.


2.23.1
======

* api-change:``ecs``: The release addresses Amazon ECS documentation tickets.
* api-change:``sagemaker``: Added support for ml.trn1.32xlarge instance type in Reserved Capacity Offering


2.23.0
======

* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``workspaces-thin-client``: Mark type in MaintenanceWindow as required.
* api-change:``workspaces``: Added GeneralPurpose.4xlarge & GeneralPurpose.8xlarge ComputeTypes.
* api-change:``security-ir``: Increase minimum length of Threat Actor IP 'userAgent' to 1.
* api-change:``cognito-identity``: corrects the dual-stack endpoint configuration
* feature:``s3``: The S3 client attempts to validate response checksums for all S3 API operations that support checksums. However, if the SDK has not implemented the specified checksum algorithm then this validation is skipped. Checksum validation behavior can be configured using the ``when_supported`` and ``when_required`` options - in the shared AWS config file using ``response_checksum_validation``, and as an env variable using ``AWS_RESPONSE_CHECKSUM_VALIDATION``.
* feature:``s3``: S3 client behavior is updated to always calculate CRC64NVME checksum by default for operations that support it, such as PutObject or UploadPart, or require it, such as DeleteObjects. Checksum behavior can be configured using the ``when_supported`` and ``when_required`` options - in the shared AWS config file using ``request_checksum_calculation`` and as an env variable using ``AWS_REQUEST_CHECKSUM_CALCULATION``. Note: AWS CLI will no longer automatically compute and populate the Content-MD5 header.
* api-change:``sesv2``: This release introduces a new recommendation in Virtual Deliverability Manager Advisor, which detects elevated complaint rates for customer sending identities.
* api-change:``s3``: This change enhances integrity protections for new SDK requests to S3. S3 SDKs now support the CRC64NVME checksum algorithm, full object checksums for multipart S3 objects, and new default integrity protections for S3 requests.
* feature:``s3``: Added support for the CRC64NVME checksum algorithm in the S3 CRT-based client.
* api-change:``bedrock-agent-runtime``: Now supports streaming for inline agents.
* api-change:``partnercentral-selling``: Add Tagging support for ResourceSnapshotJob resources


2.22.35
=======

* api-change:``route53``: Amazon Route 53 now supports the Mexico (Central) Region (mx-central-1) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region
* api-change:``gamelift``: Amazon GameLift releases a new game session placement feature: PriorityConfigurationOverride. You can now override how a game session queue prioritizes placement locations for a single StartGameSessionPlacement request.


2.22.34
=======

* api-change:``ec2``: Add support for DisconnectOnSessionTimeout flag in CreateClientVpnEndpoint and ModifyClientVpnEndpoint requests and DescribeClientVpnEndpoints responses
* api-change:``bedrock``: With this release, Bedrock Evaluation will now support latency-optimized inference for foundation models.
* api-change:``kafkaconnect``: Support updating connector configuration via UpdateConnector API. Release Operations API to monitor the status of the connector operation.
* api-change:``artifact``: Support resolving regional API calls to partition's leader region endpoint.
* api-change:``transcribe``: This update provides tagging support for Transcribe's Call Analytics Jobs and Call Analytics Categories.


2.22.33
=======

* api-change:``sts``: Fixed typos in the descriptions.
* api-change:``redshift``: Additions to the PubliclyAccessible and Encrypted parameters clarifying what the defaults are.
* api-change:``securitylake``: Doc only update for ServiceName that fixes several customer-reported issues


2.22.32
=======

* api-change:``codebuild``: AWS CodeBuild Now Supports BuildBatch in Reserved Capacity and Lambda
* api-change:``compute-optimizer``: This release expands AWS Compute Optimizer rightsizing recommendation support for Amazon EC2 Auto Scaling groups to include those with scaling policies and multiple instance types.
* api-change:``fms``: AWS Firewall Manager now lets you combine multiple resource tags using the logical AND operator or the logical OR operator.


2.22.31
=======

* api-change:``sagemaker``: Adds support for IPv6 for SageMaker HyperPod cluster nodes.
* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Thailand) Region (ap-southeast-7) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region
* api-change:``rds``: Updates Amazon RDS documentation to clarify the RestoreDBClusterToPointInTime description.


2.22.30
=======

* enhancement:``s3 ls``: Expose low-level ``ListBuckets` parameters ``Prefix`` and ``BucketRegion`` to high-level ``s3 ls`` command as ``--bucket-name-prefix`` and ``--bucket-region``.
* api-change:``dynamodb``: This release makes Amazon DynamoDB point-in-time-recovery (PITR) to be configurable. You can set PITR recovery period for each table individually to between 1 and 35 days.
* api-change:``imagebuilder``: This release adds support for importing images from ISO disk files. Added new ImportDiskImage API operation.
* api-change:``cloudhsmv2``: Adds support to ModifyCluster for modifying a Cluster's Hsm Type.


2.22.29
=======

* api-change:``supplychain``: Allow vanity DNS domain when creating a new ASC instance
* api-change:``iotsecuretunneling``: Adds dualstack endpoint support for IoT Secure Tunneling


2.22.28
=======

* api-change:``s3``: This change is only for updating the model regexp of CopySource which is not for validation but only for documentation and user guide change.
* api-change:``route53domains``: Doc only update for Route 53 Domains that fixes several customer-reported issues
* api-change:``ecs``: Adding SDK reference examples for Amazon ECS operations.


2.22.27
=======

* api-change:``appsync``: Modify UpdateGraphQLAPI operation and flag authenticationType as required.
* api-change:``organizations``: Added ALL_FEATURES_MIGRATION_ORGANIZATION_SIZE_LIMIT_EXCEEDED to ConstraintViolationException for the EnableAllFeatures operation.
* api-change:``sagemaker``: Adding ETag information with Model Artifacts for Model Registry
* api-change:``gamelift``: Amazon GameLift releases a new game session shutdown feature. Use the Amazon GameLift console or AWS CLI to terminate an in-progress game session that's entered a bad state or is no longer needed.
* api-change:``mediaconnect``: AWS Elemental MediaConnect now supports Content Quality Analysis for enhanced source stream monitoring. This enables you to track specific audio and video metrics in transport stream source flows, ensuring your content meets quality standards.
* api-change:``sqs``: In-flight message typo fix from 20k to 120k.
* api-change:``mediaconvert``: This release adds support for the AVC3 codec and fixes an alignment issue with Japanese vertical captions.


2.22.26
=======

* api-change:``ecr-public``: Restoring custom endpoint functionality for ECR Public
* api-change:``ecr``: Restoring custom endpoint functionality for ECR


2.22.25
=======

* api-change:``rds``: Updates Amazon RDS documentation to correct various descriptions.


2.22.24
=======

* api-change:``network-firewall``: Dual-stack endpoints are now supported.
* api-change:``bcm-pricing-calculator``: Added ConflictException to DeleteBillEstimate.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``ecr``: Add support for Dualstack Endpoints


2.22.23
=======

* api-change:``ecr-public``: Add support for Dualstack endpoints
* api-change:``ecr``: Documentation update for ECR GetAccountSetting and PutAccountSetting APIs.
* api-change:``glue``: Add IncludeRoot parameters to GetCatalogs API to return root catalog.
* api-change:``eks``: This release adds support for DescribeClusterVersions API that provides important information about Kubernetes versions along with end of support dates


2.22.22
=======

* api-change:``connect``: This release supports adding NotAttributeCondition and Range to the RoutingCriteria object.
* api-change:``billing``: Added new API's for defining and fetching Billing Views.
* api-change:``ce``: Support for retrieving cost, usage, and forecast for billing view.
* enhancement:endpoints: Add support for ``stringArray`` parameters and the ``operationContextParams`` trait when resolving service endpoints.
* api-change:``sagemaker``: This release adds support for c6i, m6i and r6i instance on SageMaker Hyperpod and trn1 instances in batch
* api-change:``eks``: This release expands the catalog of upgrade insight checks
* api-change:``outposts``: Add CS8365C as a supported power connector for Outpost sites.
* api-change:``bedrock-agent``: Support for custom user agent and max web pages crawled for web connector. Support app only credentials for SharePoint connector. Increase agents memory duration limit to 365 days. Support to specify max number of session summaries to include in agent invocation context.
* api-change:``docdb``: Support AWS Secret Manager managed password for AWS DocumentDB instance-based cluster.
* api-change:``bedrock-data-automation``: Documentation update for Amazon Bedrock Data Automation
* api-change:``bedrock-data-automation-runtime``: Documentation update for Amazon Bedrock Data Automation Runtime
* api-change:``bedrock-agent-runtime``: bedrock agents now supports long term memory and performance configs. Invokeflow supports performance configs. RetrieveAndGenerate performance configs
* api-change:``macie2``: This release adds support for identifying S3 general purpose buckets that exceed the Amazon Macie quota for preventative control monitoring.


2.22.21
=======

* api-change:``workspaces``: Added AWS Global Accelerator (AGA) support for WorkSpaces Personal.
* api-change:``qconnect``: Amazon Q in Connect enables agents to ask Q for assistance in multiple languages and Q will provide answers and recommended step-by-step guides in those languages. Qs default language is English (United States) and you can switch this by setting the locale configuration on the AI Agent.
* api-change:``appstream``: Added support for Rocky Linux 8 on Amazon AppStream 2.0
* api-change:``mediaconvert``: This release adds support for inserting timecode tracks into MP4 container outputs.
* api-change:``ssm-sap``: AWS Systems Manager for SAP added support for registration and discovery of distributed ABAP applications
* api-change:``medialive``: MediaLive is releasing ListVersions api


2.22.20
=======

* api-change:``resiliencehub``: AWS Resilience Hub now automatically detects already configured CloudWatch alarms and FIS experiments as part of the assessment process and returns the discovered resources in the corresponding list API responses. It also allows you to include or exclude test recommendations for an AppComponent.
* enhancement:``ec2``: Replace cryptographic functions from ``cryptography`` with ``awscrt`` for the ``get-password-data`` command.
* api-change:``quicksight``: Add support for PerformanceConfiguration attribute to Dataset entity. Allow PerformanceConfiguration specification in CreateDataset and UpdateDataset APIs.
* api-change:``transfer``: Added AS2 agreement configurations to control filename preservation and message signing enforcement. Added AS2 connector configuration to preserve content type from S3 objects.
* api-change:``budgets``: Releasing minor partition endpoint updates
* api-change:``connect``: This release adds support for the UpdateParticipantAuthentication API used for customer authentication within Amazon Connect chats.
* enhancement:``cloudfront``: Replace cryptographic functions from ``cryptography`` with ``awscrt`` for the ``sign`` command.
* api-change:``datasync``: AWS DataSync introduces the ability to update attributes for in-cloud locations.
* api-change:``iot``: Release connectivity status query API which is a dedicated high throughput(TPS) API to query a specific device's most recent connectivity state and metadata.
* api-change:``amplify``: Added WAF Configuration to Amplify Apps
* enhancement:``cloudtrail``: Replace cryptographic functions from ``cryptography`` with ``awscrt`` for the ``validate-logs`` and ``verify-query-results`` commands.
* api-change:``connectparticipant``: This release adds support for the GetAuthenticationUrl and CancelParticipantAuthentication APIs used for customer authentication within Amazon Connect chats. There are also minor updates to the GetAttachment API.
* api-change:``mwaa``: Added support for Apache Airflow version 2.10.3 to MWAA.


2.22.19
=======

* api-change:``m2``: This release adds support for AWS Mainframe Modernization(M2) Service to allow specifying network type(ipv4, dual) for the environment instances. For dual network type, m2 environment applications will serve both IPv4 and IPv6 requests, whereas for ipv4 it will serve only IPv4 requests.
* api-change:``cloudfront``: Adds support for OriginReadTimeout and OriginKeepaliveTimeout to create CloudFront Distributions with VPC Origins.
* api-change:``batch``: This feature allows AWS Batch on Amazon EKS to support configuration of Pod Annotations, overriding Namespace on which the Batch job's Pod runs on, and allows Subpath and Persistent Volume claim to be set for AWS Batch on Amazon EKS jobs.
* api-change:``synthetics``: Add support to toggle outbound IPv6 traffic on canaries connected to dualstack subnets.  This behavior can be controlled via the new Ipv6AllowedForDualStack parameter of the VpcConfig input object in CreateCanary and UpdateCanary APIs.
* api-change:``cleanroomsml``: Add support for SQL compute configuration for StartAudienceGenerationJob API.
* api-change:``ecs``: Added support for enableFaultInjection task definition parameter which can be used to enable Fault Injection feature on ECS tasks.
* api-change:``backup``: Add Support for Backup Indexing
* api-change:``account``: Update endpoint configuration.
* api-change:``codepipeline``: AWS CodePipeline V2 type pipelines now support Managed Compute Rule.
* api-change:``backupsearch``: Add support for searching backups


2.22.18
=======

* api-change:``ec2``: This release adds support for EBS local snapshots in AWS Dedicated Local Zones, which allows you to store snapshots of EBS volumes locally in Dedicated Local Zones.
* api-change:``dlm``: This release adds support for Local Zones in Amazon Data Lifecycle Manager EBS snapshot lifecycle policies.
* api-change:``greengrassv2``: Add support for runtime in GetCoreDevice and ListCoreDevices APIs.
* api-change:``medialive``: AWS Elemental MediaLive adds three new features: MediaPackage v2 endpoint support for live stream delivery, KLV metadata passthrough in CMAF Ingest output groups, and Metadata Name Modifier in CMAF Ingest output groups for customizing metadata track names in output streams.
* api-change:``cloud9``: Added information about Ubuntu 18.04 will be removed from the available imageIds for Cloud9 because Ubuntu 18.04 has ended standard support on May 31, 2023.
* api-change:``rds``: This release adds support for the "MYSQL_CACHING_SHA2_PASSWORD" enum value for RDS Proxy ClientPasswordAuthType.


2.22.17
=======

* api-change:``mediaconnect``: AWS Elemental MediaConnect Gateway now supports Source Specific Multicast (SSM) for ingress bridges. This enables you to specify a source IP address in addition to a multicast IP when creating or updating an ingress bridge source.
* api-change:``networkmanager``: There was a sentence fragment in UpdateDirectConnectGatewayAttachment that was causing customer confusion as to whether it's an incomplete sentence or if it was a typo. Removed the fragment.
* api-change:``eks``: Add NodeRepairConfig in CreateNodegroupRequest and UpdateNodegroupConfigRequest
* api-change:``logs``: Limit PutIntegration IntegrationName and ListIntegrations IntegrationNamePrefix parameters to 50 characters
* api-change:``servicediscovery``: AWS Cloud Map now supports service-level attributes, allowing you to associate custom metadata directly with services. These attributes can be retrieved, updated, and deleted using the new GetServiceAttributes, UpdateServiceAttributes, and DeleteServiceAttributes API calls.
* api-change:``ec2``: This release adds GroupId to the response for DeleteSecurityGroup.
* api-change:``cloudhsmv2``: Add support for Dual-Stack hsm2m.medium clusters. The customers will now be able to create hsm2m.medium clusters having both IPv4 and IPv6 connection capabilities by specifying a new param called NetworkType=DUALSTACK during cluster creation.


2.22.16
=======

* api-change:``connect``: Configure holidays and other overrides to hours of operation in advance. During contact handling, Amazon Connect automatically checks for overrides and provides customers with an appropriate flow path. After an override period passes call center automatically reverts to standard hours of operation.
* api-change:``glue``: To support customer-managed encryption in Data Quality to allow customers encrypt data with their own KMS key, we will add a DataQualityEncryption field to the SecurityConfiguration API where customers can provide their KMS keys.
* api-change:``route53domains``: This release includes the following API updates: added the enumeration type RESTORE_DOMAIN to the OperationType; constrained the Price attribute to non-negative values; updated the LangCode to allow 2 or 3 alphabetical characters.
* enhancement:awscrt: Update awscrt version requirement to 0.23.4
* api-change:``dms``: Add parameters to support for kerberos authentication. Add parameter for disabling the Unicode source filter with PostgreSQL settings. Add parameter to use large integer value with Kinesis/Kafka settings.
* api-change:``guardduty``: Improved descriptions for certain APIs.


2.22.15
=======

* api-change:``cloudtrail``: Doc-only updates for CloudTrail.
* api-change:``cognito-idp``: Updated descriptions for some API operations and parameters, corrected some errors in Cognito user pools
* api-change:``artifact``: Add support for listing active customer agreements for the calling AWS Account.
* api-change:``timestream-influxdb``: Adds networkType parameter to CreateDbInstance API which allows IPv6 support to the InfluxDB endpoint
* api-change:``emr-serverless``: This release adds support for accessing system profile logs in Lake Formation-enabled jobs.
* api-change:``sesv2``: Introduces support for multi-region endpoint.
* api-change:``mgh``: API and documentation updates for AWS MigrationHub related to adding support for listing migration task updates and associating, disassociating and listing source resources
* api-change:``controlcatalog``: Minor documentation updates to the content of ImplementationDetails object part of the Control Catalog GetControl API


2.22.14
=======

* api-change:``sesv2``: Introduces support for creating DEED (Deterministic Easy-DKIM) identities.
* api-change:``finspace``: Update KxCommandLineArgument value parameter regex to allow for spaces and semicolons
* api-change:``application-autoscaling``: Doc only update for AAS Predictive Scaling policy configuration API.
* api-change:``connect``: Add support for Push Notifications for Amazon Connect chat. With Push Notifications enabled an alert could be sent to customers about new messages even when they aren't actively using the mobile application.
* api-change:``bcm-pricing-calculator``: Updated condition key inference from Workload Estimate, Bill Scenario, and Bill Estimate resources. Updated documentation links.
* api-change:``ivs-realtime``: IVS Real-Time now offers customers the ability to customize thumbnails recording mode and interval for both Individual Participant Recording (IPR) and Server-Side Compositions (SSC).


2.22.13
=======

* api-change:``keyspaces``: Amazon Keyspaces: adding the list of IAM actions required by the UpdateKeyspace API.
* bugfix:``sso``: Support the ``--ca-bundle`` and ``--no-verify-ssl`` options on SSO commands.
* api-change:``appsync``: Provides description of new Amazon Bedrock runtime datasource.
* api-change:``ec2``: This release includes a new API for modifying instance network-performance-options after launch.
* api-change:``medialive``: H265 outputs now support disabling the deblocking filter.
* bugfix:``s3``: Follow ``IllegalLocationConstraintException`` redirects for ``s3``.
* api-change:``ecs``: This is a documentation only update to address various tickets for Amazon ECS.
* api-change:``cognito-idp``: Change `CustomDomainConfig` from a required to an optional parameter for the `UpdateUserPoolDomain` operation.
* api-change:``workspaces``: Added text to clarify case-sensitivity


2.22.12
=======

* api-change:``qbusiness``: This release removes the deprecated UserId and UserGroups fields from SearchRelevantContent api's request parameters.
* api-change:``partnercentral-selling``: Introducing the preview of new partner central selling APIs designed to transform how AWS partners collaborate and co-sell with multiple partners. This enables multiple partners to seamlessly engage and jointly pursue customer opportunities, fostering a new era of collaborative selling.


2.22.11
=======

* api-change:``bedrock``: Introduced two APIs ListPromptRouters and GetPromptRouter for Intelligent Prompt Router feature. Add support for Bedrock Guardrails image content filter. New Bedrock Marketplace feature enabling a wider range of bedrock compatible models with self-hosted capability.
* api-change:``kendra``: This release adds GenAI Index in Amazon Kendra for Retrieval Augmented Generation (RAG) and intelligent search. With the Kendra GenAI Index, customers get high retrieval accuracy powered by the latest information retrieval technologies and semantic models.
* api-change:``sagemaker``: Amazon SageMaker HyperPod launched task governance to help customers maximize accelerator utilization for model development and flexible training plans to meet training timelines and budget while reducing weeks of training time. AI apps from AWS partner is now available in SageMaker.
* api-change:``bedrock-data-automation``: Release Bedrock Data Automation SDK
* api-change:``bedrock-runtime``: Added support for Intelligent Prompt Router in Invoke, InvokeStream, Converse and ConverseStream. Add support for Bedrock Guardrails image content filter. New Bedrock Marketplace feature enabling a wider range of bedrock compatible models with self-hosted capability.
* api-change:``bedrock-data-automation-runtime``: Release Bedrock Data Automation Runtime SDK
* api-change:``bedrock-agent-runtime``: This release introduces the ability to generate SQL using natural language, through a new GenerateQuery API (with native integration into Knowledge Bases); ability to ingest and retrieve images through Bedrock Data Automation; and ability to create a Knowledge Base backed by Kendra GenAI Index.
* api-change:``bedrock-agent``: This release introduces the ability to generate SQL using natural language, through a new GenerateQuery API (with native integration into Knowledge Bases); ability to ingest and retrieve images through Bedrock Data Automation; and ability to create a Knowledge Base backed by Kendra GenAI Index.


2.22.10
=======

* api-change:``bedrock``: Tagging support for Async Invoke resources. Added support for Distillation in CreateModelCustomizationJob API. Support for videoDataDeliveryEnabled flag in invocation logging.
* api-change:``s3tables``: Amazon S3 Tables deliver the first cloud object store with built-in open table format support, and the easiest way to store tabular data at scale.
* api-change:``dynamodb``: This change adds support for global tables with multi-Region strong consistency (in preview). The UpdateTable API now supports a new attribute MultiRegionConsistency to set consistency when creating global tables. The DescribeTable output now optionally includes the MultiRegionConsistency attribute.
* api-change:``cloudwatch``: Support for configuring AiOps investigation as alarm action
* api-change:``redshift-serverless``: Adds support for the ListManagedWorkgroups API to get an overview of existing managed workgroups.
* api-change:``dsql``: Add new API operations for Amazon Aurora DSQL. Amazon Aurora DSQL is a serverless, distributed SQL database with virtually unlimited scale, highest availability, and zero infrastructure management.
* api-change:``qapps``: Add support for 11 new plugins as action cards to help automate repetitive tasks and improve productivity.
* api-change:``bedrock-runtime``: Added support for Async Invoke Operations Start, List and Get. Support for invocation logs with `requestMetadata` field in Converse, ConverseStream, Invoke and InvokeStream. Video content blocks in Converse/ConverseStream accept raw bytes or S3 URI.
* api-change:``glue``: This release includes(1)Zero-ETL integration to ingest data from 3P SaaS and DynamoDB to Redshift/Redlake (2)new properties on Connections to enable reuse; new connection APIs for retrieve/preview metadata (3)support of CRUD operations for Multi-catalog (4)support of automatic statistics collections
* api-change:``bedrock-agent``: Releasing SDK for Multi-Agent Collaboration.
* api-change:``quicksight``: This release includes API needed to support for Unstructured Data in Q in QuickSight Q&A (IDC).
* api-change:``s3``: Amazon S3 Metadata stores object metadata in read-only, fully managed Apache Iceberg metadata tables that you can query. You can create metadata table configurations for S3 general purpose buckets.
* api-change:``athena``: Add FEDERATED type to CreateDataCatalog. This creates Athena Data Catalog, AWS Lambda connector, and AWS Glue connection. Create/DeleteDataCatalog returns DataCatalog. Add Status, ConnectionType, and Error to DataCatalog and DataCatalogSummary. Add DeleteCatalogOnly to delete Athena Catalog only.
* api-change:``redshift``: Adds support for Amazon Redshift RegisterNamespace and DeregisterNamespace APIs to share data to AWS Glue Data Catalog.
* api-change:``datazone``: Adds support for Connections, ProjectProfiles, and JobRuns APIs. Supports the new Lineage feature at GA. Adjusts optionality of a parameter for DataSource and SubscriptionTarget APIs which may adjust types in some clients.
* api-change:``bedrock-agent-runtime``: Releasing SDK for multi agent collaboration
* api-change:``lakeformation``: This release added two new LakeFormation Permissions (CREATE_CATALOG, SUPER_USER) and added Id field for CatalogResource. It also added new conditon and expression field.
* api-change:``qbusiness``: Amazon Q Business now supports customization options for your web experience, 11 new Plugins, and QuickSight support. Amazon Q index allows software providers to enrich their native generative AI experiences with their customer's enterprise knowledge and user context spanning multiple applications.


2.22.9
======

* api-change:``s3control``: It allows customers to pass CRC64NVME as a header in S3 Batch Operations copy requests
* api-change:``socialmessaging``: Added support for passing role arn corresponding to the supported event destination
* api-change:``bedrock-runtime``: Add an API parameter that allows customers to set performance configuration for invoking a model.


2.22.8
======

* api-change:``qbusiness``: Amazon Q Business now supports capabilities to extract insights and answer questions from visual elements embedded within documents, a browser extension for Google Chrome, Mozilla Firefox, and Microsoft Edge, and attachments across conversations.
* api-change:``fsx``: FSx API changes to support the public launch of the Amazon FSx Intelligent Tiering for OpenZFS storage class.
* api-change:``eks``: Added support for Auto Mode Clusters, Hybrid Nodes, and specifying computeTypes in the DescribeAddonVersions API.
* api-change:``customer-profiles``: This release introduces Event Trigger APIs as part of Amazon Connect Customer Profiles service.
* api-change:``ec2``: Adds support for declarative policies that allow you to enforce desired configuration across an AWS organization through configuring account attributes. Adds support for Allowed AMIs that allows you to limit the use of AMIs in AWS accounts. Adds support for connectivity over non-HTTP protocols.
* api-change:``guardduty``: Add new Multi Domain Correlation findings.
* api-change:``events``: Call private APIs by configuring Connections with VPC connectivity through PrivateLink and VPC Lattice
* api-change:``security-ir``: AWS Security Incident Response is a purpose-built security incident solution designed to help customers prepare for, respond to, and recover from security incidents.
* api-change:``s3control``: Amazon S3 introduces support for AWS Dedicated Local Zones
* api-change:``securityhub``: Add new Multi Domain Correlation findings.
* api-change:``organizations``: Add support for policy operations on the DECLARATIVE_POLICY_EC2 policy type.
* api-change:``imagebuilder``: Added support for EC2 Image Builder's integration with AWS Marketplace for Marketplace components.
* api-change:``vpc-lattice``: Lattice APIs that allow sharing and access of VPC resources across accounts.
* api-change:``connectcampaignsv2``: Amazon Connect Outbound Campaigns V2 / Features : Adds support for Event-Triggered Campaigns.
* api-change:``bedrock-agent-runtime``: This release introduces a new Rerank API to leverage reranking models (with integration into Knowledge Bases); APIs to upload documents directly into Knowledge Base; RetrieveAndGenerateStream API for streaming response; Guardrails on Retrieve API; and ability to automatically generate filters
* api-change:``memorydb``: Amazon MemoryDB SDK now supports all APIs for Multi-Region. Please refer to the updated Amazon MemoryDB public documentation for detailed information on API usage.
* api-change:``opensearch``: This feature introduces support for CRUDL APIs, enabling the creation and management of Connected data sources.
* api-change:``connect``: Adds support for WhatsApp Business messaging, IVR call recording, enabling Contact Lens for existing on-premise contact centers and telephony platforms, and enabling telephony and IVR migration to Amazon Connect independent of their contact center agents.
* api-change:``qconnect``: This release adds following capabilities: Configuring safeguards via AIGuardrails for Q in Connect inferencing, and APIs to support Q&A self-service use cases
* api-change:``bedrock-agent``: This release introduces APIs to upload documents directly into a Knowledge Base
* api-change:``networkflowmonitor``: This release adds documentation for a new feature in Amazon CloudWatch called Network Flow Monitor. You can use Network Flow Monitor to get near real-time metrics, including retransmissions and data transferred, for your actual workloads.
* api-change:``s3``: Amazon S3 introduces support for AWS Dedicated Local Zones
* api-change:``cleanrooms``: This release allows customers and their partners to easily collaborate with data stored in Snowflake and Amazon Athena, without having to move or share their underlying data among collaborators.
* api-change:``ecs``: This release adds support for Container Insights with Enhanced Observability for Amazon ECS.
* api-change:``bedrock``: Add support for Knowledge Base Evaluations & LLM as a judge
* api-change:``invoicing``: AWS Invoice Configuration allows you to receive separate AWS invoices based on your organizational needs. You can use the AWS SDKs to manage Invoice Units and programmatically fetch the information of the invoice receiver.
* api-change:``chime-sdk-voice``: This release adds supports for enterprises to integrate Amazon Connect with other voice systems. It supports directly transferring voice calls and metadata without using the public telephone network. It also supports real-time and post-call analytics.
* api-change:``transfer``: AWS Transfer Family now offers Web apps that enables simple and secure access to data stored in Amazon S3.
* api-change:``logs``: Adds PutIntegration, GetIntegration, ListIntegrations and DeleteIntegration APIs. Adds QueryLanguage support to StartQuery, GetQueryResults, DescribeQueries, DescribeQueryDefinitions, and PutQueryDefinition APIs.
* api-change:``rds``: Amazon RDS supports CloudWatch Database Insights. You can use the SDK to create, modify, and describe the DatabaseInsightsMode for your DB instances and clusters.


2.22.7
======

* api-change:``config``: AWS Config adds support for service-linked recorders, a new type of Config recorder managed by AWS services to record specific subsets of resource configuration data and functioning independently from customer managed AWS Config recorders.
* api-change:``fsx``: This release adds EFA support to increase FSx for Lustre file systems' throughput performance to a single client instance. This can be done by specifying EfaEnabled=true at the time of creation of Persistent_2 file systems.
* api-change:``observabilityadmin``: Amazon CloudWatch Observability Admin adds the ability to audit telemetry configuration for AWS resources in customers AWS Accounts and Organizations. The release introduces new APIs to turn on/off the new experience, which supports discovering supported AWS resources and their state of telemetry.
* api-change:``bedrock-agent``: Add support for specifying embeddingDataType, either FLOAT32 or BINARY


2.22.6
======

* api-change:``ec2``: Adds support for Time-based Copy for EBS Snapshots and Cross Region PrivateLink. Time-based Copy ensures that EBS Snapshots are copied within and across AWS Regions in a specified timeframe. Cross Region PrivateLink enables customers to connect to VPC endpoint services hosted in other AWS Regions.
* api-change:``connect``: Enables access to ValueMap and ValueInteger types for SegmentAttributes and fixes deserialization bug for DescribeContactFlow in AmazonConnect Public API
* api-change:``qapps``: Private sharing, file upload and data collection feature support for Q Apps
* api-change:``bedrock-agent-runtime``: Custom Orchestration and Streaming configurations API release for AWSBedrockAgents.
* api-change:``bedrock-agent``: Custom Orchestration API release for AWSBedrockAgents.


2.22.5
======

* api-change:``directconnect``: Update DescribeDirectConnectGatewayAssociations API to return associated core network information if a Direct Connect gateway is attached to a Cloud WAN core network.
* api-change:``s3``: Amazon Simple Storage Service / Features: Add support for ETag based conditional writes in PutObject and CompleteMultiPartUpload APIs to prevent unintended object modifications.
* api-change:``networkmanager``: This release adds native Direct Connect integration on Cloud WAN enabling customers to directly attach their Direct Connect gateways to Cloud WAN without the need for an intermediate Transit Gateway.


2.22.4
======

* api-change:``neptune-graph``: Add 4 new APIs to support new Export features, allowing Parquet and CSV formats. Add new arguments in Import APIs to support Parquet import. Add a new query "neptune.read" to run algorithms without loading data into database
* api-change:``autoscaling``: Now, Amazon EC2 Auto Scaling customers can enable target tracking policies to take quicker scaling decisions, enhancing their application performance and EC2 utilization. To get started, specify target tracking to monitor a metric that is available on Amazon CloudWatch at seconds-level interval.
* api-change:``omics``: This release adds support for resource policy based cross account S3 access to sequence store read sets.
* api-change:``chatbot``: Adds support for programmatic management of custom actions and aliases which can be associated with channel configurations.
* api-change:``stepfunctions``: Add support for variables and JSONata in TestState, GetExecutionHistory, DescribeStateMachine, and DescribeStateMachineForExecution
* api-change:``workspaces``: While integrating WSP-DCV rebrand, a few mentions were erroneously renamed from WSP to DCV. This release reverts those mentions back to WSP.
* api-change:``sagemaker``: This release adds APIs for new features for SageMaker endpoint to scale down to zero instances, native support for multi-adapter inference, and endpoint scaling improvements.
* api-change:``lambda``: Add ProvisionedPollerConfig to Lambda event-source-mapping API.
* api-change:``sns``: ArchivePolicy attribute added to Archive and Replay feature
* api-change:``bcm-pricing-calculator``: Initial release of the AWS Billing and Cost Management Pricing Calculator API.
* api-change:``mailmanager``: Added new "DeliverToQBusiness" rule action to MailManager RulesSet for ingesting email data into Amazon Q Business customer applications
* api-change:``bedrock-agent-runtime``: InvokeInlineAgent API release to help invoke runtime agents without any dependency on preconfigured agents.
* api-change:``ses``: This release adds support for starting email contacts in your Amazon Connect instance as an email receiving action.
* api-change:``codepipeline``: AWS CodePipeline V2 type pipelines now support ECRBuildAndPublish and InspectorScan actions.
* api-change:``emr``: Advanced Scaling in Amazon EMR Managed Scaling
* api-change:``connect``: Amazon Connect Service Feature: Add APIs for Amazon Connect Email Channel
* api-change:``ce``: This release adds the Impact field(contains Contribution field) to the GetAnomalies API response under RootCause
* api-change:``cognito-idp``: Add support for users to sign up and sign in without passwords, using email and SMS OTPs and Passkeys. Add support for Passkeys based on WebAuthn. Add support for enhanced branding customization for hosted authentication pages with Amazon Cognito Managed Login. Add feature tiers with new pricing.
* api-change:``inspector2``: Extend inspector2 service model to include ServiceQuotaExceededException.
* api-change:``quicksight``: This release includes: Update APIs to support Image, Layer Map, font customization, and Plugin Visual. Add Identity center related information in ListNamsespace API. Update API for restrictedFolder support in topics and add API for SearchTopics, Describe/Update DashboardsQA Configration.
* api-change:``elbv2``: This release adds support for advertising trusted CA certificate names in associated trust stores.


2.22.3
======

* api-change:``cloudfront``: Adds support for Origin Selection between EMPv2 origins based on media quality score.
* api-change:``resiliencehub``: AWS Resilience Hub's new summary view visually represents applications' resilience through charts, enabling efficient resilience management. It provides a consolidated view of the app portfolio's resilience state and allows data export for custom stakeholder reporting.
* api-change:``iotfleetwise``: AWS IoT FleetWise now includes campaign parameters to store and forward data, configure MQTT topic as a data destination, and collect diagnostic trouble code data. It includes APIs for network agnostic data collection using custom decoding interfaces, and monitoring the last known state of vehicles.
* api-change:``s3``: Add support for conditional deletes for the S3 DeleteObject and DeleteObjects APIs. Add support for write offset bytes option used to append to objects with the S3 PutObject API.
* api-change:``notifications``: This release adds support for AWS User Notifications. You can now configure and view notifications from AWS services in a central location using the AWS SDK.
* api-change:``lambda``: Adds support for metrics for event source mappings for AWS Lambda
* api-change:``ssm-quicksetup``: Add methods that retrieve details about deployed configurations: ListConfigurations, GetConfiguration
* api-change:``notificationscontacts``: This release adds support for AWS User Notifications Contacts. You can now configure and view email contacts for AWS User Notifications using the AWS SDK.
* api-change:``application-autoscaling``: Application Auto Scaling now supports Predictive Scaling to proactively increase the desired capacity ahead of predicted demand, ensuring improved availability and responsiveness for customers' applications. This feature is currently only made available for Amazon ECS Service scalable targets.
* api-change:``iot-jobs-data``: General Availability (GA) release of AWS IoT Device Management - Commands, to trigger light-weight remote actions on targeted devices
* api-change:``elasticache``: Added support to modify the engine type for existing ElastiCache Users and User Groups. Customers can now modify the engine type from redis to valkey.
* api-change:``xray``: AWS X-Ray introduces Transaction Search APIs, enabling span ingestion into CloudWatch Logs for high-scale trace data indexing. These APIs support span-level queries, trace graph generation, and metric correlation for deeper application insights.
* api-change:``iot``: General Availability (GA) release of AWS IoT Device Management - Commands, to trigger light-weight remote actions on targeted devices
* api-change:``cloudtrail``: This release introduces new APIs for creating and managing CloudTrail Lake dashboards. It also adds support for resource-based policies on CloudTrail EventDataStore and Dashboard resource.
* api-change:``ec2``: Adds support for requesting future-dated Capacity Reservations with a minimum commitment duration, enabling IPAM for organizational units within AWS Organizations, reserving EC2 Capacity Blocks that start in 30 minutes, and extending the end date of existing Capacity Blocks.
* api-change:``appsync``: Add support for the Amazon Bedrock Runtime.
* api-change:``logs``: Adds "Create field indexes to improve query performance and reduce scan volume" and "Transform logs during ingestion". Updates documentation for "PutLogEvents with Entity".
* api-change:``elbv2``: This feature adds support for enabling zonal shift on cross-zone enabled Application Load Balancer, as well as modifying HTTP request and response headers.
* api-change:``ssm``: Added support for providing high-level overviews of managed nodes and previewing the potential impact of a runbook execution.
* api-change:``apigateway``: Added support for custom domain names for private APIs.
* api-change:``ce``: This release introduces three new APIs that enable you to estimate the cost, coverage, and utilization impact of Savings Plans you plan to purchase. The three APIs are StartCommitmentPurchaseAnalysis, GetCommitmentPurchaseAnalysis, and ListCommitmentPurchaseAnalyses.
* api-change:``health``: Adds metadata property to an AffectedEntity.


2.22.2
======

* api-change:``bedrock-agent-runtime``: Releasing new Prompt Optimization to enhance your prompts for improved performance
* api-change:``ecs``: This release adds support for the Availability Zone rebalancing feature on Amazon ECS.
* api-change:``controltower``: Adds support for child enabled baselines which allow you to see the enabled baseline status for individual accounts.
* api-change:``mediaconvert``: This release adds the ability to reconfigure concurrent job settings for existing queues and create queues with custom concurrent job settings.
* enhancement:protocol: Added support for header enabling service migration off the AWS Query protocol.
* api-change:``omics``: Enabling call caching feature that allows customers to reuse previously computed results from a set of completed tasks in a new workflow run.
* api-change:``discovery``: Add support to import data from commercially available discovery tools without file manipulation.
* api-change:``lambda``: Add Node 22.x (node22.x) support to AWS Lambda
* api-change:``rds``: This release adds support for scale storage on the DB instance using a Blue/Green Deployment.
* api-change:``cost-optimization-hub``: This release adds action type "Delete" to the GetRecommendation, ListRecommendations and ListRecommendationSummaries APIs to support new EBS and ECS recommendations with action type "Delete".
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate optimization recommendations for Amazon Aurora database instances. It also enables Compute Optimizer to identify idle Amazon EC2 instances, Amazon EBS volumes, Amazon ECS services running on Fargate, and Amazon RDS databases.
* api-change:``rbin``: This release adds support for exclusion tags for Recycle Bin, which allows you to identify resources that are to be excluded, or ignored, by a Region-level retention rule.
* api-change:``workspaces-web``: Added data protection settings with support for inline data redaction.
* api-change:``timestream-query``: This release adds support for Provisioning Timestream Compute Units (TCUs), a new feature that allows provisioning dedicated compute resources for your queries, providing predictable and cost-effective query performance.
* api-change:``elbv2``: This release adds support for configuring Load balancer Capacity Unit reservations
* api-change:``workspaces``: Added support for Rocky Linux 8 on Amazon WorkSpaces Personal.
* api-change:``cloudfront``: Add support for gRPC, VPC origins, and Anycast IP Lists. Allow LoggingConfig IncludeCookies to be set regardless of whether the LoggingConfig is enabled.
* api-change:``mediapackagev2``: MediaPackage v2 now supports the Media Quality Confidence Score (MQCS) published from MediaLive. Customers can control input switching based on the MQCS and publishing HTTP Headers for the MQCS via the API.
* api-change:``ec2``: With this release, customers can express their desire to launch instances only in an ODCR or ODCR group rather than OnDemand capacity. Customers can express their baseline instances' CPU-performance in attribute-based Instance Requirements configuration by referencing an instance family.
* bugfix:``configure``: Fixed ``aws configure sso`` to honor ``--use-device-code``.
* api-change:``datazone``: This release supports Metadata Enforcement Rule feature for Create Subscription Request action.
* api-change:``autoscaling``: With this release, customers can prioritize launching instances into ODCRs using targets from ASGs or Launch Templates. Customers can express their baseline instances' CPU-performance in attribute-based Instance Requirements configuration by referencing an instance family that meets their needs.


2.22.1
======

* api-change:``glue``: AWS Glue Data Catalog now enhances managed table optimizations of Apache Iceberg tables that can be accessed only from a specific Amazon Virtual Private Cloud (VPC) environment.
* api-change:``ecs``: This release introduces support for configuring the version consistency feature for individual containers defined within a task definition. The configuration allows to specify whether ECS should resolve the container image tag specified in the container definition to an image digest.
* api-change:``ec2``: This release adds VPC Block Public Access (VPC BPA), a new declarative control which blocks resources in VPCs and subnets that you own in a Region from reaching or being reached from the internet through internet gateways and egress-only internet gateways.
* api-change:``mwaa``: Amazon MWAA now supports a new environment class, mw1.micro, ideal for workloads requiring fewer resources than mw1.small. This class supports a single instance of each Airflow component: Scheduler, Worker, and Webserver.
* api-change:``efs``: Add support for the new parameters in EFS replication APIs
* api-change:``keyspaces``: Amazon Keyspaces Multi-Region Replication: Adds support to add new regions to multi and single-region keyspaces.
* api-change:``b2bi``: Add new X12 transactions sets and versions
* api-change:``taxsettings``: Release Tax Inheritance APIs,  Tax Exemption APIs, and functionality update for some existing Tax Registration APIs
* api-change:``workspaces``: Releasing new ErrorCodes for Image Validation failure during CreateWorkspaceImage process


2.22.0
======

* feature:``sso``: Add support and default to the OAuth 2.0 Authorization Code Flow with PKCE for ``aws sso login``.
* api-change:``cloudformation``: This release adds a new API, ListHookResults, that allows retrieving CloudFormation Hooks invocation results for hooks invoked during a create change set operation or Cloud Control API operation
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now supports Amazon Application Recovery Controller (ARC) zonal shift and zonal autoshift to help you quickly recover an impaired application from failures in an Availability Zone (AZ).
* api-change:``customer-profiles``: This release introduces Segmentation APIs and new Calculated Attribute Event Filters as part of Amazon Connect Customer Profiles service.
* api-change:``rds-data``: Add support for the automatic pause/resume feature of Aurora Serverless v2.
* api-change:``appconfig``: AWS AppConfig has added a new extension action point, AT_DEPLOYMENT_TICK, to support third-party monitors to trigger an automatic rollback during a deployment.
* api-change:``ecs``: This release adds support for adding VPC Lattice configurations in ECS CreateService/UpdateService APIs. The configuration allows for associating VPC Lattice target groups with ECS Services.
* api-change:``iotsitewise``: The release introduces a generative AI Assistant in AWS IoT SiteWise. It includes: 1) InvokeAssistant API - Invoke the Assistant to get alarm summaries and ask questions. 2) Dataset APIs - Manage knowledge base configuration for the Assistant. 3) Portal APIs enhancement - Manage AI-aware dashboards.
* api-change:``ec2``: Adding request and response elements for managed resources.
* api-change:``connect``: Adds CreateContactFlowVersion and ListContactFlowVersions APIs to create and view the versions of a contact flow.
* api-change:``qconnect``: This release introduces MessageTemplate as a resource in Amazon Q in Connect, along with APIs to create, read, search, update, and delete MessageTemplate resources.
* api-change:``rds``: Add support for the automatic pause/resume feature of Aurora Serverless v2.


2.21.3
======

* api-change:``connectcampaignsv2``: Added Amazon Connect Outbound Campaigns V2 SDK.
* api-change:``datasync``: Doc-only updates and enhancements related to creating DataSync tasks and describing task executions.
* api-change:``pinpoint-sms-voice-v2``: Use rule overrides to always allow or always block messages to specific phone numbers. Use message feedback to monitor if a customer interacts with your message.
* api-change:``outposts``: You can now purchase AWS Outposts rack or server capacity for a 5-year term with one of  the following payment options: All Upfront, Partial Upfront, and No Upfront.
* api-change:``route53resolver``: Route 53 Resolver DNS Firewall Advanced Rules allows you to monitor and block suspicious DNS traffic based on anomalies detected in the queries, such as DNS tunneling and Domain Generation Algorithms (DGAs).
* api-change:``ec2``: Remove non-functional enum variants for FleetCapacityReservationUsageStrategy
* api-change:``iot``: This release allows AWS IoT Core users to enrich MQTT messages with propagating attributes, to associate a thing to a connection, and to enable Online Certificate Status Protocol (OCSP) stapling for TLS X.509 server certificates through private endpoints.
* api-change:``cloudwatch``: Adds support for adding related Entity information to metrics ingested through PutMetricData.


2.21.2
======

* api-change:``partnercentral-selling``: Announcing AWS Partner Central API for Selling: This service launch Introduces new APIs for co-selling opportunity management and related functions. Key features include notifications, a dynamic sandbox for testing, and streamlined validations.


2.21.1
======

* api-change:``quicksight``: This release adds APIs for Custom Permissions management in QuickSight, and APIs to support QuickSight Branding.
* api-change:``accessanalyzer``: Expand analyzer configuration capabilities for unused access analyzers. Unused access analyzer configurations now support the ability to exclude accounts and resource tags from analysis providing more granular control over the scope of analysis.
* api-change:``cloudcontrol``: Added support for CloudFormation Hooks with Cloud Control API. The GetResourceRequestStatus API response now includes an optional HooksProgressEvent and HooksRequestToken parameter for Hooks Invocation Progress as part of resource operation with Cloud Control.
* api-change:``sts``: This release introduces the new API 'AssumeRoot', which returns short-term credentials that you can use to perform privileged tasks.
* api-change:``partnercentral-selling``: Announcing AWS Partner Central API for Selling: This service launch Introduces new APIs for co-selling opportunity management and related functions. Key features include notifications, a dynamic sandbox for testing, and streamlined validations.
* api-change:``s3``: This release updates the ListBuckets API Reference documentation in support of the new 10,000 general purpose bucket default quota on all AWS accounts. To increase your bucket quota from 10,000 to up to 1 million buckets, simply request a quota increase via Service Quotas.
* api-change:``iam``: This release includes support for five new APIs and changes to existing APIs that give AWS Organizations customers the ability to use temporary root credentials, targeted to member accounts in the organization.
* api-change:``deadline``: Adds support for select GPU accelerated instance types when creating new service-managed fleets.
* bugfix:IMDS: Fixed ambiguous error raised when failing to resolve a region from IMDS.
* api-change:``sagemaker``: Add support for Neuron instance types [ trn1/trn1n/inf2 ] on SageMaker Notebook Instances Platform.
* api-change:``redshift``: Adds support for Amazon Redshift S3AccessGrants
* api-change:``ivs``: IVS now offers customers the ability to stream multitrack video to Channels.
* api-change:``license-manager-user-subscriptions``: New and updated API operations to support License Included User-based Subscription of Microsoft Remote Desktop Services (RDS).
* api-change:``iotwireless``: New FuotaTask resource type to enable logging for your FUOTA tasks. A ParticipatingGatewaysforMulticast parameter to choose the list of gateways to receive the multicast downlink message and the transmission interval between them. Descriptor field which will be sent to devices during FUOTA transfer.


2.21.0
======

* api-change:``cloudtrail``: This release adds a new API GenerateQuery that generates a query from a natural language prompt about the event data in your event data store. This operation uses generative artificial intelligence (generative AI) to produce a ready-to-use SQL query from the prompt.
* api-change:``mediaconvert``: This release adds support for ARN inputs in the Kantar credentials secrets name field and the MSPR field to the manifests for PlayReady DRM protected outputs.
* api-change:``billing``: Today, AWS announces the general availability of ListBillingViews API in the AWS SDKs, to enable AWS Billing Conductor (ABC) users to create proforma Cost and Usage Reports (CUR) programmatically.
* feature:macOS: End of support for macOS 10.15
* api-change:``accessanalyzer``: This release adds support for policy validation and external access findings for resource control policies (RCP). IAM Access Analyzer helps you author functional and secure RCPs and awareness that a RCP may restrict external access. Updated service API, documentation, and paginators.
* api-change:``application-signals``: Amazon CloudWatch Application Signals now supports creating Service Level Objectives with burn rates. Users can now create or update SLOs with burn rate configurations to meet their specific business requirements.
* api-change:``organizations``: Add support for policy operations on the Resource Control Polices.
* api-change:``dynamodb``: This release includes supports the new WarmThroughput feature for DynamoDB. You can now provide an optional WarmThroughput attribute for CreateTable or UpdateTable APIs to pre-warm your table or global secondary index. You can also use DescribeTable to see the latest WarmThroughput value.
* api-change:``b2bi``: This release adds a GenerateMapping API to allow generation of JSONata or XSLT transformer code based on input and output samples.
* api-change:``internetmonitor``: Add new query type Routing_Suggestions regarding querying interface
* api-change:``ec2``: This release adds the source AMI details in DescribeImages API


2.20.0
======

* api-change:``codebuild``: AWS CodeBuild now supports non-containerized Linux and Windows builds on Reserved Capacity.
* api-change:``payment-cryptography``: Updated ListAliases API with KeyArn filter.
* feature:shorthand: Adds support to shorthand syntax for loading parameters from files via the ``@=`` assignment operator.
* api-change:``controltower``: Added ResetEnabledControl API.
* api-change:``gamelift``: Amazon GameLift releases container fleets support for general availability. Deploy Linux-based containerized game server software for hosting on Amazon GameLift.
* api-change:``rds``: Updates Amazon RDS documentation for Amazon RDS Extended Support for Amazon Aurora MySQL.
* api-change:``fis``: This release adds support for generating experiment reports with the experiment report configuration


2.19.5
======

* api-change:``opensearch``: Adds Support for new AssociatePackages and DissociatePackages API in Amazon OpenSearch Service that allows association and dissociation operations to be carried out on multiple packages at the same time.
* api-change:``inspector2``: Adds support for filePath filter.
* api-change:``cloudfront``: No API changes from previous release. This release migrated the model to Smithy keeping all features unchanged.
* api-change:``lambda``: Add Python 3.13 (python3.13) support to AWS Lambda
* api-change:``outposts``: This release updates StartCapacityTask to allow an active Outpost to be modified. It also adds a new API to list all running EC2 instances on the Outpost.


2.19.4
======

* api-change:``firehose``: Amazon Data Firehose / Features : Adds support for a new DeliveryStreamType, DatabaseAsSource. DatabaseAsSource hoses allow customers to stream CDC events from their RDS and Amazon EC2 hosted databases, running MySQL and PostgreSQL database engines, to Iceberg Table destinations.
* api-change:``eks``: Adds new error code `Ec2InstanceTypeDoesNotExist` for Amazon EKS managed node groups
* api-change:``controlcatalog``: AWS Control Catalog GetControl public API returns additional data in output, including Implementation and Parameters
* api-change:``bedrock-agent-runtime``: This release adds trace functionality to Bedrock Prompt Flows
* api-change:``qbusiness``: Adds S3 path option to pass group member list for PutGroup API.
* api-change:``lambda``: This release adds support for using AWS KMS customer managed keys to encrypt AWS Lambda .zip deployment packages.
* api-change:``batch``: This feature allows override LaunchTemplates to be specified in an AWS Batch Compute Environment.
* api-change:``chime-sdk-media-pipelines``: Added support for Media Capture Pipeline and Media Concatenation Pipeline for customer managed server side encryption. Now Media Capture Pipeline can use IAM sink role to get access to KMS key and encrypt/decrypt recorded artifacts. KMS key ID can also be supplied with encryption context.
* enhancement:``s3``: Handle HTTP 200 responses with error information for all supported s3 operations.
* api-change:``pinpoint-sms-voice-v2``: Added the RequiresAuthenticationTimestamp field to the RegistrationVersionStatusHistory data type.


2.19.3
======

* api-change:``bedrock-runtime``: Add Prompt management support to Bedrock runtime APIs: Converse, ConverseStream, InvokeModel, InvokeModelWithStreamingResponse
* api-change:``bedrock-agent``: Add prompt support for chat template configuration and agent generative AI resource. Add support for configuring an optional guardrail in Prompt and Knowledge Base nodes in Prompt Flows. Add API to validate flow definition
* api-change:``cleanrooms``: This release introduces support for Custom Models in AWS Clean Rooms ML.
* api-change:``quicksight``: Add Client Credentials based OAuth support for Snowflake and Starburst
* api-change:``cleanroomsml``: This release introduces support for Custom Models in AWS Clean Rooms ML.
* api-change:``autoscaling``: Auto Scaling groups now support the ability to strictly balance instances across Availability Zones by configuring the AvailabilityZoneDistribution parameter. If balanced-only is configured for a group, launches will always be attempted in the under scaled Availability Zone even if it is unhealthy.
* api-change:``resource-explorer-2``: Add GetManagedView, ListManagedViews APIs.
* api-change:``synthetics``: Add support to toggle if a canary will automatically delete provisioned canary resources such as Lambda functions and layers when a canary is deleted.  This behavior can be controlled via the new ProvisionedResourceCleanup property exposed in the CreateCanary and UpdateCanary APIs.


2.19.2
======

* api-change:``lakeformation``: API changes for new named tag expressions feature.
* api-change:``codebuild``: AWS CodeBuild now adds additional compute types for reserved capacity fleet.
* api-change:``qapps``: Introduces category apis in AmazonQApps. Web experience users use Categories to tag and filter library items.
* api-change:``guardduty``: GuardDuty RDS Protection expands support for Amazon Aurora PostgreSQL Limitless Databases.
* api-change:``s3control``: Fix ListStorageLensConfigurations and ListStorageLensGroups deserialization for Smithy SDKs.
* api-change:``verifiedpermissions``: Adding BatchGetPolicy API which supports the retrieval of multiple policies across multiple policy stores within a single request.


2.19.1
======

* api-change:``taxsettings``: Add support for supplemental tax registrations via these new APIs: PutSupplementalTaxRegistration, ListSupplementalTaxRegistrations, and DeleteSupplementalTaxRegistration.
* api-change:``logs``: This release introduces an improvement in PutLogEvents
* api-change:``docdb-elastic``: Amazon DocumentDB Elastic Clusters adds support for pending maintenance actions feature with APIs GetPendingMaintenanceAction, ListPendingMaintenanceActions and ApplyPendingMaintenanceAction
* api-change:``bedrock-agent``: Amazon Bedrock Knowledge Bases now supports using application inference profiles to increase throughput and improve resilience.


2.19.0
======

* api-change:``glue``: Add schedule support for AWS Glue column statistics
* api-change:``autoscaling``: Adds bake time for Auto Scaling group Instance Refresh
* api-change:``sagemaker``: SageMaker HyperPod adds scale-down at instance level via BatchDeleteClusterNodes API and group level via UpdateCluster API. SageMaker Training exposes secondary job status in TrainingJobSummary from ListTrainingJobs API. SageMaker now supports G6, G6e, P5e instances for HyperPod and Training.
* feature:signing: Adds internal support for the new 'auth' trait to allow a priority list of auth types for a service or operation.
* api-change:``batch``: Add `podNamespace` to `EksAttemptDetail` and `containerID` to `EksAttemptContainerDetail`.
* api-change:``amp``: Added support for UpdateScraper API, to enable updating collector configuration in-place
* api-change:``sesv2``: This release enables customers to provide the email template content in the SESv2 SendEmail and SendBulkEmail APIs instead of the name or the ARN of a stored email template.
* api-change:``elbv2``: Add UDP support for AWS PrivateLink and dual-stack Network Load Balancers


2.18.18
=======

* api-change:``ecs``: This release supports service deployments and service revisions which provide a comprehensive view of your Amazon ECS service history.
* api-change:``redshift-serverless``: Adds and updates API members for the Redshift Serverless AI-driven scaling and optimization feature using the price-performance target setting.
* api-change:``opensearchserverless``: Neo Integration via IAM Identity Center (IdC)
* api-change:``geo-places``: Release of Amazon Location Places API. Places enables you to quickly search, display, and filter places, businesses, and locations based on proximity, category, and name
* api-change:``geo-routes``: Release of Amazon Location Routes API. Routes enables you to plan efficient routes and streamline deliveries by leveraging real-time traffic, vehicle restrictions, and turn-by-turn directions.
* api-change:``datasync``: AWS DataSync now supports Enhanced mode tasks. This task mode supports transfer of virtually unlimited numbers of objects with enhanced metrics, more detailed logs, and higher performance than Basic mode. This mode currently supports transfers between Amazon S3 locations.
* api-change:``appsync``: This release adds support for AppSync Event APIs.
* api-change:``redshift``: This release launches S3 event integrations to create and manage integrations from an Amazon S3 source into an Amazon Redshift database.
* api-change:``route53``: This release adds support for TLSA, SSHFP, SVCB, and HTTPS record types.
* api-change:``network-firewall``: AWS Network Firewall now supports configuring TCP idle timeout
* api-change:``sagemaker``: Added support for Model Registry Staging construct. Users can define series of stages that models can progress through for model workflows and lifecycle. This simplifies tracking and managing models as they transition through development, testing, and production stages.
* api-change:``workmail``: This release adds support for Multi-Factor Authentication (MFA) and Personal Access Tokens through integration with AWS IAM Identity Center.
* api-change:``opensearch``: This release introduces the new OpenSearch user interface (Dashboards), a new web-based application that can be associated with multiple data sources across OpenSearch managed clusters, serverless collections, and Amazon S3, so that users can gain a comprehensive insights in an unified interface.
* api-change:``geo-maps``: Release of Amazon Location Maps API. Maps enables you to build digital maps that showcase your locations, visualize your data, and unlock insights to drive your business
* api-change:``ec2``: This release adds two new capabilities to VPC Security Groups: Security Group VPC Associations and Shared Security Groups.
* api-change:``connect``: Updated the public documentation for the UserIdentityInfo object to accurately reflect the character limits for the FirstName and LastName fields, which were previously listed as 1-100 characters.
* api-change:``keyspaces``: Adds support for interacting with user-defined types (UDTs) through the following new operations: Create-Type, Delete-Type, List-Types, Get-Type.


2.18.17
=======

* api-change:``iotfleetwise``: Updated BatchCreateVehicle and BatchUpdateVehicle APIs: LimitExceededException has been added and the maximum number of vehicles in a batch has been set to 10 explicitly
* api-change:``bedrock``: Update Application Inference Profile
* api-change:``logs``: Added support for new optional baseline parameter in the UpdateAnomaly API. For UpdateAnomaly requests with baseline set to True, The anomaly behavior is then treated as baseline behavior. However, more severe occurrences of this behavior will still be reported as anomalies.
* api-change:``cleanrooms``: This release adds the option for customers to configure analytics engine when creating a collaboration, and introduces the new SPARK analytics engine type in addition to maintaining the legacy CLEAN_ROOMS_SQL engine type.
* api-change:``redshift-data``: Adding a new API GetStatementResultV2 that supports CSV formatted results from ExecuteStatement and BatchExecuteStatement calls.
* api-change:``sagemaker``: Adding `notebook-al2-v3` as allowed value to SageMaker NotebookInstance PlatformIdentifier attribute
* api-change:``bedrock-runtime``: Update Application Inference Profile


2.18.16
=======

* api-change:``mediapackagev2``: MediaPackage V2 Live to VOD Harvester is a MediaPackage V2 feature, which is used to export content from an origin endpoint to a S3 bucket.
* api-change:``storagegateway``: Documentation update: Amazon FSx File Gateway will no longer be available to new customers.
* api-change:``opensearch``: Adds support for provisioning dedicated coordinator nodes. Coordinator nodes can be specified using the new NodeOptions parameter in ClusterConfig.
* api-change:``rds``: This release adds support for Enhanced Monitoring and Performance Insights when restoring Aurora Limitless Database DB clusters. It also adds support for the os-upgrade pending maintenance action.


2.18.15
=======

* api-change:``codebuild``: AWS CodeBuild now supports automatically retrying failed builds
* api-change:``lambda``: Add TagsError field in Lambda GetFunctionResponse. The TagsError field contains details related to errors retrieving tags.
* api-change:``logs``: Adding inferred token name for dynamic tokens in Anomalies.
* api-change:``bedrock-agent``: Add support of new model types for Bedrock Agents, Adding inference profile support for Flows and Prompt Management, Adding new field to configure additional inference configurations for Flows and Prompt Management
* api-change:``supplychain``: API doc updates, and also support showing error message on a failed instance


2.18.14
=======

* api-change:``nimble``: The nimble client has been removed following the deprecation of the service.
* api-change:``ecs``: This release adds support for EBS volumes attached to Amazon ECS Windows tasks running on EC2 instances.
* api-change:``pcs``: Documentation update: added the default value of the Slurm configuration parameter scaleDownIdleTimeInSeconds to its description.
* api-change:``appconfig``: This release improves deployment safety by granting customers the ability to REVERT completed deployments, to the last known good state.In the StopDeployment API revert case the status of a COMPLETE deployment will be REVERTED. AppConfig only allows a revert within 72 hours of deployment completion.
* api-change:``ec2``: This release includes a new API to describe some details of the Amazon Machine Images (AMIs) that were used to launch EC2 instances, even if those AMIs are no longer available for use.
* bugfix:shorthand: Improve performance when parsing invalid shorthand syntax.
* api-change:``qbusiness``: Add a new field in chat response. This field can be used to support nested schemas in array fields


2.18.13
=======

* api-change:``payment-cryptography``: Add support for ECC P-256 and P-384 Keys.
* api-change:``ec2``: Amazon EC2 X8g, C8g and M8g instances are powered by AWS Graviton4 processors. X8g provide the lowest cost per GiB of memory among Graviton4 instances. C8g provide the best price performance for compute-intensive workloads. M8g provide the best price performance in for general purpose workloads.
* api-change:``mwaa``: Introducing InvokeRestApi which allows users to invoke the Apache Airflow REST API on the webserver with the specified inputs.
* api-change:``connect``: Amazon Connect Service Feature: Add support to start screen sharing for a web calling contact.
* api-change:``bedrock``: Doc updates for supporting converse
* api-change:``payment-cryptography-data``: Add ECDH support on PIN operations.


2.18.12
=======

* api-change:``bedrock-runtime``: Updating invoke regex to support imported models for converse API
* api-change:``m2``: Add AuthSecretsManagerArn optional parameter to batch job APIs, expand batch parameter limits, and introduce clientToken constraints.
* api-change:``imagebuilder``: Add macOS platform and instance placement options
* api-change:``repostspace``: Adds the BatchAddRole and BatchRemoveRole APIs.
* api-change:``rds``: Global clusters now expose the Endpoint attribute as one of its fields. It is a Read/Write endpoint for the global cluster which resolves to the Global Cluster writer instance.
* api-change:``timestream-query``: This release adds support for Query Insights, a feature that provides details of query execution, enabling users to identify areas for improvement to optimize their queries, resulting in improved query performance and lower query costs.


2.18.11
=======

* api-change:``fms``: Update AWS WAF policy - add the option to retrofit existing web ACLs instead of creating all new web ACLs.
* api-change:``application-insights``: This feature enables customers to specify SNS Topic ARN. CloudWatch Application Insights (CWAI) will utilize this ARN to send problem notifications.
* api-change:``dms``: Added support for tagging in StartReplicationTaskAssessmentRun API and introduced IsLatestTaskAssessmentRun and ResultStatistic fields for enhanced tracking and assessment result statistics.
* api-change:``autoscaling``: Adds support for removing the PlacementGroup setting on an Auto Scaling Group through the UpdateAutoScalingGroup API.
* api-change:``ec2``: Amazon EC2 now allows you to create network interfaces with just the EFA driver and no ENA driver by specifying the network interface type as efa-only.
* api-change:``bedrock-agent-runtime``: Knowledge Bases for Amazon Bedrock now supports custom prompts and model parameters in the orchestrationConfiguration of the RetrieveAndGenerate API. The modelArn field accepts Custom Models and Imported Models ARNs.
* api-change:``wafv2``: Add a property to WebACL to indicate whether it's been retrofitted by Firewall Manager.
* api-change:``payment-cryptography-data``: Adding new API to generate authenticated scripts for EMV pin change use cases.
* api-change:``eks``: This release adds support for Amazon Application Recovery Controller (ARC) zonal shift and zonal autoshift with EKS that enhances the resiliency of multi-AZ cluster environments


2.18.10
=======

* api-change:``bedrock``: Adding converse support to CMI API's
* api-change:``ec2``: RequestSpotInstances and RequestSpotFleet feature release.
* api-change:``bedrock-runtime``: Added converse support for custom imported models
* api-change:``athena``: Removing FEDERATED from Create/List/Delete/GetDataCatalog API
* api-change:``datazone``: Adding the following project member designations: PROJECT_CATALOG_VIEWER, PROJECT_CATALOG_CONSUMER and PROJECT_CATALOG_STEWARD in the CreateProjectMembership API and PROJECT_CATALOG_STEWARD designation in the AddPolicyGrant API.


2.18.9
======

* api-change:``ecs``: This is an Amazon ECS documentation only update to address tickets.
* api-change:``workspaces``: Updated the DomainName pattern for Active Directory
* api-change:``quicksight``: Add StartDashboardSnapshotJobSchedule API. RestoreAnalysis now supports restoring analysis to folders.
* api-change:``pinpoint-sms-voice-v2``: Added the registrations status of REQUIRES_AUTHENTICATION
* api-change:``bedrock-agent``: Removing support for topK property in PromptModelInferenceConfiguration object, Making PromptTemplateConfiguration property as required, Limiting the maximum PromptVariant to 1
* api-change:``rds``: Updates Amazon RDS documentation for TAZ IAM support
* api-change:``pipes``: This release adds validation to require specifying a SecurityGroup and Subnets in the Vpc object under PipesSourceSelfManagedKafkaParameters. It also adds support for iso-e, iso-f, and other non-commercial partitions in ARN parameters.
* api-change:``dataexchange``: This release adds Data Grant support, through which customers can programmatically create data grants to share with other AWS accounts and accept data grants from other AWS accounts.


2.18.8
======

* api-change:``s3``: Add support for the new optional bucket-region and prefix query parameters in the ListBuckets API. For ListBuckets requests that express pagination, Amazon S3 will now return both the bucket names and associated AWS regions in the response.


2.18.7
======

* api-change:``codebuild``: Enable proxy for reserved capacity fleet.
* api-change:``sesv2``: This release adds support for email maximum delivery seconds that allows senders to control the time within which their emails are attempted for delivery.
* api-change:``redshift``: This release launches the CreateIntegration, DeleteIntegration, DescribeIntegrations and ModifyIntegration APIs to create and manage Amazon Redshift Zero-ETL Integrations.
* api-change:``resiliencehub``: AWS Resilience Hub now integrates with the myApplications platform, enabling customers to easily assess the resilience of applications defined in myApplications. The new Resiliency widget provides visibility into application resilience and actionable recommendations for improvement.
* api-change:``ivs``: On a channel that you own, you can now replace an ongoing stream with a new stream by streaming up with the priority parameter appended to the stream key.
* api-change:``cloudformation``: Documentation update for AWS CloudFormation API Reference.
* api-change:``amplify``: Added sourceUrlType field to StartDeployment request
* enhancement:awscrt: Update awscrt version requirement to 0.22.0
* api-change:``qbusiness``: Amazon Q Business now supports embedding the Amazon Q Business web experience on third-party websites.


2.18.6
======

* api-change:``securitylake``: This release updates request validation regex for resource ARNs.
* api-change:``codepipeline``: AWS CodePipeline V2 type pipelines now support automatically retrying failed stages and skipping stage for failed entry conditions.
* api-change:``transfer``: This release enables customers using SFTP connectors to query the transfer status of their files to meet their monitoring needs as well as orchestrate post transfer actions.
* api-change:``mailmanager``: Mail Manager support for viewing and exporting metadata of archived messages.
* api-change:``supplychain``: This release adds AWS Supply Chain instance management functionality. Specifically adding CreateInstance, DeleteInstance, GetInstance, ListInstances, and UpdateInstance APIs.


2.18.5
======

* api-change:``elbv2``: Add zonal_shift.config.enabled attribute. Add new AdministrativeOverride construct in the describe-target-health API response to include information about the override status applied to a target.
* api-change:``robomaker``: Documentation update: added support notices to each API action.
* api-change:``emr``: This release provides new parameter "Context" in instance fleet clusters.
* api-change:``appflow``: Doc only updates for clarification around OAuth2GrantType for Salesforce.
* api-change:``guardduty``: Added a new field for network connection details.


2.18.4
======

* api-change:``neptune-graph``: Support for 16 m-NCU graphs available through account allowlisting
* api-change:``route53resolver``: Route 53 Resolver Forwarding Rules can now include a server name indication (SNI) in the target address for rules that use the DNS-over-HTTPS (DoH) protocol. When a DoH-enabled Outbound Resolver Endpoint forwards a request to a DoH server, it will provide the SNI in the TLS handshake.
* api-change:``iotfleetwise``: Refine campaign related API validations
* api-change:``dms``: Introduces DescribeDataMigrations, CreateDataMigration, ModifyDataMigration, DeleteDataMigration, StartDataMigration, StopDataMigration operations to SDK. Provides FailedDependencyFault error message.
* api-change:``elastic-inference``: Elastic Inference - Documentation update to add service shutdown notice.
* api-change:``acm-pca``: Documentation updates for AWS Private CA.
* api-change:``ec2``: This release adds support for assigning the billing of shared Amazon EC2 On-Demand Capacity Reservations.
* enhancement:cryptography: Update ``cryptography`` version range ceiling to 43.0.1
* api-change:``socialmessaging``: This release for AWS End User Messaging includes a public SDK, providing a suite of APIs that enable sending WhatsApp messages to end users.
* api-change:``outposts``: Adding new "DELIVERED" enum value for Outposts Order status
* api-change:``ecs``: This is a documentation only release that updates to documentation to let customers know that Amazon Elastic Inference is no longer available.
* api-change:``timestream-influxdb``: This release updates our regex based validation rules in regards to valid DbInstance and DbParameterGroup name.


2.18.3
======

* api-change:``codepipeline``: AWS CodePipeline introduces a Compute category


2.18.2
======

* api-change:``memorydb``: Amazon MemoryDB SDK now supports all APIs for newly launched Valkey engine. Please refer to the updated Amazon MemoryDB public documentation for detailed information on API usage.
* api-change:``elasticache``: AWS ElastiCache SDK now supports using APIs with newly launched Valkey engine. Please refer to updated AWS ElastiCache public documentation for detailed information on API usage.
* enhancement:``s3``: Adds logic to gracefully handle invalid timestamps returned in the Expires header.


2.18.1
======

* api-change:``marketplace-reporting``: Documentation-only update for AWS Marketplace Reporting API.
* api-change:``qconnect``: This release adds support for the following capabilities: Configuration of the Gen AI system via AIAgent and AIPrompts. Integration support for Bedrock Knowledge Base.
* api-change:``deadline``: Add support for using the template from a previous job during job creation and listing parameter definitions for a job.
* api-change:``redshift``: Add validation pattern to S3KeyPrefix on the EnableLogging API


2.18.0
======

* api-change:``iot-data``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* feature:s3: Adds ``--checksum-mode`` and ``--checksum-algorithm`` parameters to high-level ``s3`` commands.
* api-change:``ec2``: Documentation updates for Amazon EC2.


2.17.65
=======

* api-change:``mediapackagev2``: Added support for ClipStartTime on the FilterConfiguration object on OriginEndpoint manifest settings objects. Added support for EXT-X-START tags on produced HLS child playlists.
* api-change:``quicksight``: QuickSight: Add support for exporting and importing folders in AssetBundle APIs
* api-change:``connect``: Public GetMetricDataV2 Grouping increase from 3 to 4
* api-change:``ec2``: This release includes a new API for modifying instance cpu-options after launch.
* api-change:``codepipeline``: AWS CodePipeline introduces Commands action that enables you to easily run shell commands as part of your pipeline execution.
* api-change:``iot``: This release adds support for Custom Authentication with X.509 Client Certificates, support for Custom Client Certificate validation, and support for selecting application protocol and authentication type without requiring TLS ALPN for customer's AWS IoT Domain Configurations.
* api-change:``marketplace-reporting``: The AWS Marketplace Reporting service introduces the GetBuyerDashboard API. This API returns a dashboard that provides visibility into your organization's AWS Marketplace agreements and associated spend across the AWS accounts in your organization.


2.17.64
=======

* api-change:``workspaces``: WSP is being rebranded to become DCV.
* api-change:``s3``: This release introduces a header representing the minimum object size limit for Lifecycle transitions.
* api-change:``sagemaker``: releasing builtinlcc to public
* api-change:``appstream``: Added support for Automatic Time Zone Redirection on Amazon AppStream 2.0
* api-change:``ivs-realtime``: Adds new Stage Health EventErrorCodes applicable to RTMP(S) broadcasts. Bug Fix: Enforces that EncoderConfiguration Video height and width must be even-number values.
* api-change:``iotdeviceadvisor``: Add clientToken attribute and implement idempotency for CreateSuiteDefinition.
* api-change:``b2bi``: Added and updated APIs to support outbound EDI transformations
* api-change:``bedrock-agent-runtime``: Added raw model response and usage metrics to PreProcessing and PostProcessing Trace
* api-change:``bedrock-runtime``: Added new fields to Amazon Bedrock Guardrails trace


2.17.63
=======

* api-change:``rds``: This release provides additional support for enabling Aurora Limitless Database DB clusters.
* api-change:``bedrock-agent``: This release adds support to stop an ongoing ingestion job using the StopIngestionJob API in Agents for Amazon Bedrock.
* api-change:``codeartifact``: Add support for the dual stack endpoints.


2.17.62
=======

* api-change:``bedrock``: Add support for custom models via provisioned throughput for Bedrock Model Evaluation
* api-change:``pricing``: Add examples for API operations in model.
* api-change:``verifiedpermissions``: Add examples for API operations in model.
* api-change:``supplychain``: Release DataLakeDataset, DataIntegrationFlow and ResourceTagging APIs for AWS Supply Chain
* api-change:``timestream-influxdb``: Timestream for InfluxDB now supports port configuration and additional customer-modifiable InfluxDB v2 parameters. This release adds Port to the CreateDbInstance and UpdateDbInstance API, and additional InfluxDB v2 parameters to the CreateDbParameterGroup API.
* api-change:``clouddirectory``: Add examples for API operations in model.
* api-change:``connect``: Amazon Connect introduces StartOutboundChatContact API allowing customers to initiate outbound chat contacts
* api-change:``resource-groups``: This update includes new APIs to support application groups and to allow users to manage resource tag-sync tasks in applications.


2.17.61
=======

* api-change:``quicksight``: Adding personalization in QuickSight data stories. Admins can enable or disable personalization through QuickSight settings.
* api-change:``sesv2``: This release adds support for engagement tracking over Https using custom domains.
* api-change:``customer-profiles``: Introduces optional RoleArn parameter for PutIntegration request and includes RoleArn in the response of PutIntegration, GetIntegration and ListIntegrations
* api-change:``securityhub``: Documentation updates for AWS Security Hub


2.17.60
=======

* api-change:``worklink``: The worklink client has been removed following the deprecation of the service.
* api-change:``lambda``: Reverting Lambda resource-based policy and block public access APIs.
* api-change:``rds-data``: Documentation update for RDS Data API to reflect support for Aurora MySQL Serverless v2 and Provisioned DB clusters.
* api-change:``organizations``: Add support for policy operations on the CHATBOT_POLICY policy type.
* api-change:``sagemaker``: Adding `TagPropagation` attribute to Sagemaker API
* api-change:``pcs``: AWS PCS API documentation - Edited the description of the iamInstanceProfileArn parameter of the CreateComputeNodeGroup and UpdateComputeNodeGroup actions; edited the description of the SlurmCustomSetting data type to list the supported parameters for clusters and compute node groups.
* api-change:``chatbot``: Return State and StateReason fields for Chatbot Channel Configurations.


2.17.59
=======

* api-change:``cloudtrail``: Doc-only update for CloudTrail network activity events release (in preview)
* api-change:``fsx``: Doc-only update to address Lustre S3 hard-coded names.
* api-change:``ec2``: Updates to documentation for the transit gateway security group referencing feature.


2.17.58
=======

* api-change:``pinpoint-sms-voice-v2``: AWS End User Messaging SMS-Voice V2 has added support for resource policies. Use the three new APIs to create, view, edit, and delete resource policies.
* api-change:``budgets``: Releasing minor partitional endpoint updates
* api-change:``bedrock``: Add support for Cross Region Inference in Bedrock Model Evaluations.
* api-change:``kinesis``: This release includes support to add tags when creating a stream
* api-change:``sagemaker``: Adding `HiddenInstanceTypes` and `HiddenSageMakerImageVersionAliases` attribute to SageMaker API
* bugfix:copy: Added support for ``ChecksumAlgorithm`` when uploading copy data in parts.


2.17.57
=======

* api-change:``rds``: Support ComputeRedundancy parameter in ModifyDBShardGroup API. Add DBShardGroupArn in DBShardGroup API response. Remove InvalidMaxAcuFault from CreateDBShardGroup and ModifyDBShardGroup API. Both API will throw InvalidParameterValueException for invalid ACU configuration.
* api-change:``ec2``: Amazon EC2 G6e instances powered by NVIDIA L40S Tensor Core GPUs are the most cost-efficient GPU instances for deploying generative AI models and the highest performance GPU instances for spatial computing workloads.
* api-change:``bedrock-agent``: Amazon Bedrock Prompt Flows and Prompt Management now supports using inference profiles to increase throughput and improve resilience.
* api-change:``athena``: List/Get/Update/Delete/CreateDataCatalog now integrate with AWS Glue connections. Users can create a Glue connection through Athena or use a Glue connection to define their Athena federated parameters.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``glue``: Added AthenaProperties parameter to Glue Connections, allowing Athena to store service specific properties on Glue Connections.
* api-change:``resource-explorer-2``: AWS Resource Explorer released ListResources feature which allows customers to list all indexed AWS resources within a view.
* api-change:``emr-serverless``: This release adds support for job concurrency and queuing configuration at Application level.


2.17.56
=======

* enhancement:paginator: Add warning when a non-positive value is provided for the max-items pagination parameter.
* api-change:``workspaces``: Releasing new ErrorCodes for SysPrep failures during ImageImport and CreateImage process
* api-change:``sagemaker``: Amazon SageMaker now supports using manifest files to specify the location of uncompressed model artifacts within Model Packages
* api-change:``dynamodb``: Generate account endpoint for DynamoDB requests when the account ID is available
* api-change:``sagemaker-metrics``: This release introduces support for the SageMaker Metrics BatchGetMetrics API.
* enhancement:openssl: Update bundled OpenSSL version to 1.1.1za for Linux installers
* api-change:``neptune``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.17.55
=======

* api-change:``medialive``: Adds Bandwidth Reduction Filtering for HD AVC and HEVC encodes, multiplex container settings.
* api-change:``mediaconvert``: This release provides support for additional DRM configurations per SPEKE Version 2.0.
* api-change:``codeconnections``: This release adds the PullRequestComment field to CreateSyncConfiguration API input, UpdateSyncConfiguration API input, GetSyncConfiguration API output and ListSyncConfiguration API output
* api-change:``quicksight``: QuickSight: 1. Add new API - ListFoldersForResource. 2. Commit mode adds visibility configuration of Apply button on multi-select controls for authors.
* api-change:``lambda``: Tagging support for Lambda event source mapping, and code signing configuration resources.
* api-change:``workspaces-web``: WorkSpaces Secure Browser now enables Administrators to view and manage end-user browsing sessions via Session Management APIs.
* api-change:``sagemaker``: Introduced support for G6e instance types on SageMaker Studio for JupyterLab and CodeEditor applications.
* api-change:``glue``: This change is for releasing TestConnection api SDK model


2.17.54
=======

* api-change:``ce``: This release extends the GetReservationPurchaseRecommendation API to support recommendations for Amazon DynamoDB reservations.
* api-change:``rds``: Updates Amazon RDS documentation with information upgrading snapshots with unsupported engine versions for RDS for MySQL and RDS for PostgreSQL.
* api-change:``ds-data``: Added new AWS Directory Service Data API, enabling you to manage data stored in AWS Directory Service directories. This includes APIs for creating, reading, updating, and deleting directory users, groups, and group memberships.
* api-change:``s3``: Added SSE-KMS support for directory buckets.
* api-change:``guardduty``: Add `launchType` and `sourceIPs` fields to GuardDuty findings.
* api-change:``mailmanager``: Introduce a new RuleSet condition evaluation, where customers can set up a StringExpression with a MimeHeader condition. This condition will perform the necessary validation based on the X-header provided by customers.
* api-change:``ds``: Added new APIs for enabling, disabling, and describing access to the AWS Directory Service Data API


2.17.53
=======

* api-change:``ecr``: The `DescribeImageScanning` API now includes `fixAvailable`, `exploitAvailable`, and `fixedInVersion` fields to provide more detailed information about the availability of fixes, exploits, and fixed versions for identified image vulnerabilities.
* api-change:``ssm``: Support for additional levels of cross-account, cross-Region organizational units in Automation. Various documentation updates.
* api-change:``codebuild``: GitLab Enhancements - Add support for Self-Hosted GitLab runners in CodeBuild. Add group webhooks
* api-change:``ecs``: This is a documentation only release to address various tickets.
* api-change:``rds``: Updates Amazon RDS documentation with configuration information about the BYOL model for RDS for Db2.
* api-change:``lambda``: Support for JSON resource-based policies and block public access


2.17.52
=======

* api-change:``rds``: Launching Global Cluster tagging.
* api-change:``organizations``: Doc only update for AWS Organizations that fixes several customer-reported issues
* api-change:``medialive``: Removing the ON_PREMISE enum from the input settings field.
* ehancement:python: Update bundled Python interpreter version to 3.12.6
* api-change:``pca-connector-scep``: This is a general availability (GA) release of Connector for SCEP, a feature of AWS Private CA. Connector for SCEP links your SCEP-enabled and mobile device management systems to AWS Private CA for digital signature installation and certificate management.
* api-change:``iot``: This release adds additional enhancements to AWS IoT Device Management Software Package Catalog and Jobs. It also adds SBOM support in Software Package Version.
* api-change:``bedrock``: This feature adds cross account s3 bucket and VPC support to ModelInvocation jobs. To use a cross account bucket, pass in the accountId of the bucket to s3BucketOwner in the ModelInvocationJobInputDataConfig or ModelInvocationJobOutputDataConfig.


2.17.51
=======

* api-change:``amplify``: Doc only update to Amplify to explain platform setting for Next.js 14 SSG only applications
* api-change:``ivschat``: Updates to all tags descriptions.
* api-change:``ivs``: Updates to all tags descriptions.


2.17.50
=======

* api-change:``emr``: Update APIs to allow modification of ODCR options, allocation strategy, and InstanceTypeConfigs on running InstanceFleet clusters.
* api-change:``cognito-idp``: Added email MFA option to user pools with advanced security features.
* api-change:``elbv2``: Correct incorrectly mapped error in ELBv2 waiters
* api-change:``rds``: This release adds support for the os-upgrade pending maintenance action for Amazon Aurora DB clusters.
* api-change:``mediaconvert``: This release includes support for dynamic video overlay workflows, including picture-in-picture and squeezeback
* api-change:``storagegateway``: The S3 File Gateway now supports DSSE-KMS encryption. A new parameter EncryptionType is added to these APIs: CreateSmbFileShare, CreateNfsFileShare, UpdateSmbFileShare, UpdateNfsFileShare, DescribeSmbFileShares, DescribeNfsFileShares. Also, in favor of EncryptionType, KmsEncrypted is deprecated.
* api-change:``synthetics``: This release introduces two features. The first is tag replication, which allows for the propagation of canary tags onto Synthetics related resources, such as Lambda functions. The second is a limit increase in canary name length, which has now been increased from 21 to 255 characters.
* api-change:``glue``: AWS Glue is introducing two new optimizers for Apache Iceberg tables: snapshot retention and orphan file deletion. Customers can enable these optimizers and customize their configurations to perform daily maintenance tasks on their Iceberg tables based on their specific requirements.


2.17.49
=======

* api-change:``guardduty``: Add support for new statistic types in GetFindingsStatistics.
* api-change:``lexv2-models``: Support new Polly voice engines in VoiceSettings: long-form and generative
* api-change:``medialive``: Adds AV1 Codec support, SRT ouputs, and MediaLive Anywhere support.
* api-change:``bedrock-agent-runtime``: Amazon Bedrock Knowledge Bases now supports using inference profiles to increase throughput and improve resilience.
* api-change:``ecr``: Added KMS_DSSE to EncryptionType
* api-change:``bedrock-agent``: Amazon Bedrock Knowledge Bases now supports using inference profiles to increase throughput and improve resilience.


2.17.48
=======

* api-change:``chime-sdk-voice``: Documentation-only update that clarifies the ValidateE911Address action of the Amazon Chime SDK Voice APIs.
* api-change:``cognito-identity``: This release adds sensitive trait to some required shapes.
* api-change:``securityhub``: Documentation update for Security Hub
* api-change:``pipes``: This release adds support for customer managed KMS keys in Amazon EventBridge Pipe


2.17.47
=======

* api-change:``elbv2``: Add paginators for the ELBv2 DescribeListenerCertificates and DescribeRules APIs. Fix broken waiter for the ELBv2 DescribeLoadBalancers API.
* api-change:``kafka``: Amazon MSK Replicator can now replicate data to identically named topics between MSK clusters within the same AWS Region or across different AWS Regions.
* api-change:``sagemaker``: Amazon Sagemaker supports orchestrating SageMaker HyperPod clusters with Amazon EKS
* api-change:``dynamodb``: Doc-only update for DynamoDB. Added information about async behavior for TagResource and UntagResource APIs and updated the description of ResourceInUseException.
* api-change:``sagemaker-runtime``: AWS SageMaker Runtime feature: Add sticky routing to support stateful inference models.
* api-change:``ivs-realtime``: IVS Real-Time now offers customers the ability to broadcast to Stages using RTMP(S).


2.17.46
=======

* api-change:``qapps``: Adds UpdateLibraryItemMetadata api to change status of app for admin verification feature and returns isVerified field in any api returning the app or library item.


2.17.45
=======

* api-change:``codepipeline``: Updates to add recent notes to APIs and to replace example S3 bucket names globally.
* api-change:``application-signals``: Amazon CloudWatch Application Signals now supports creating Service Level Objectives using a new calculation type. Users can now create SLOs which are configured with request-based SLIs to help meet their specific business requirements.
* api-change:``connect``: Amazon Connect Custom Vocabulary now supports Catalan (Spain), Danish (Denmark), Dutch (Netherlands), Finnish (Finland), Indonesian (Indonesia), Malay (Malaysia), Norwegian Bokmal (Norway), Polish (Poland), Swedish (Sweden), and Tagalog/Filipino (Philippines).
* api-change:``kinesisanalyticsv2``: Support for Flink 1.20 in Managed Service for Apache Flink
* api-change:``sagemaker``: Amazon SageMaker now supports idle shutdown of JupyterLab and CodeEditor applications on SageMaker Studio.
* api-change:``gamelift``: Amazon GameLift provides additional events for tracking the fleet creation process.


2.17.44
=======

* api-change:``fis``: This release adds safety levers, a new mechanism to stop all running experiments and prevent new experiments from starting.
* api-change:``s3control``: Amazon Simple Storage Service /S3 Access Grants / Features : This release launches new Access Grants API - ListCallerAccessGrants.
* api-change:``bedrock-agent``: Add support for user metadata inside PromptVariant.
* api-change:``logs``: Update to support new APIs for delivery of logs from AWS services.
* api-change:``finspace``: Updates Finspace documentation for smaller instances.
* api-change:``appsync``: Adds new logging levels (INFO and DEBUG) for additional log output control


2.17.43
=======

* api-change:``medialive``: Added MinQP as a Rate Control option for H264 and H265 encodes.
* api-change:``timestream-influxdb``: Timestream for InfluxDB now supports compute scaling and deployment type conversion. This release adds the DbInstanceType and DeploymentType parameters to the UpdateDbInstance API.
* api-change:``sagemaker``: Amazon SageMaker now supports automatic mounting of a user's home folder in the Amazon Elastic File System (EFS) associated with the SageMaker Studio domain to their Studio Spaces to enable users to share data between their own private spaces.
* api-change:``elbv2``: This release adds support for configuring TCP idle timeout on NLB and GWLB listeners.
* api-change:``mediaconnect``: AWS Elemental MediaConnect introduces thumbnails for Flow source monitoring. Thumbnails provide still image previews of the live content feeding your MediaConnect Flow allowing you to easily verify that your source is operating as expected.
* api-change:``connect``: Release ReplicaConfiguration as part of DescribeInstance
* api-change:``datazone``: Add support to let data publisher specify a subset of the data asset that a subscriber will have access to based on the asset filters provided, when accepting a subscription request.


2.17.42
=======

* api-change:``logs``: This release introduces a new optional parameter: Entity, in PutLogEvents request
* api-change:``datazone``: Amazon DataZone now adds new governance capabilities of Domain Units for organization within your Data Domains, and Authorization Policies for tighter controls.
* api-change:``backup``: The latest update introduces two new attributes, VaultType and VaultState, to the DescribeBackupVault and ListBackupVaults APIs. The VaultState attribute reflects the current status of the vault, while the VaultType attribute indicates the specific category of the vault.
* api-change:``redshift-data``: The release include the new Redshift DataAPI feature for session use, customer execute query with --session-keep-alive-seconds parameter and can submit follow-up queries to same sessions with returned`session-id`


2.17.41
=======

* api-change:``wafv2``: The minimum request rate for a rate-based rule is now 10. Before this, it was 100.
* api-change:``bedrock-runtime``: Add support for imported-model in invokeModel and InvokeModelWithResponseStream.
* api-change:``bedrock-agent-runtime``: Lifting the maximum length on Bedrock KnowledgeBase RetrievalFilter array
* api-change:``stepfunctions``: This release adds support for static analysis to ValidateStateMachineDefinition API, which can now return optional WARNING diagnostics for semantic errors on the definition of an Amazon States Language (ASL) state machine.
* api-change:``personalize``: This releases ability to update automatic training scheduler for customer solutions
* api-change:``quicksight``: Increased Character Limit for Dataset Calculation Field expressions


2.17.40
=======

* api-change:``devicefarm``: This release removed support for Calabash, UI Automation, Built-in Explorer, remote access record, remote access replay, and web performance profile framework in ScheduleRun API.
* api-change:``pcs``: Introducing AWS Parallel Computing Service (AWS PCS), a new service makes it easy to setup and manage high performance computing (HPC) clusters, and build scientific and engineering models at virtually any scale on AWS.
* api-change:``workspaces``: Documentation-only update that clarifies the StartWorkspaces and StopWorkspaces actions, and a few other minor edits.
* api-change:``internetmonitor``: Adds new querying types to show overall traffic suggestion information for monitors
* api-change:``datazone``: Update regex to include dot character to be consistent with IAM role creation in the authorized principal field for create and update subscription target.
* api-change:``appconfig``: This release adds support for deletion protection, which is a safety guardrail to prevent the unintentional deletion of a recently used AWS AppConfig Configuration Profile or Environment. This also includes a change to increase the maximum length of the Name parameter in UpdateConfigurationProfile.
* api-change:``ec2``: Amazon VPC IP Address Manager (IPAM) now allows customers to provision IPv4 CIDR blocks and allocate Elastic IP Addresses directly from IPAM pools with public IPv4 space


2.17.39
=======

* api-change:``polly``: Amazon Polly adds 2 new voices: Jitka (cs-CZ) and Sabrina (de-CH).
* api-change:``chatbot``: Update documentation to be consistent with the API docs
* api-change:``bedrock``: Amazon Bedrock SDK updates for Inference Profile.
* api-change:``bedrock-runtime``: Amazon Bedrock SDK updates for Inference Profile.
* api-change:``omics``: Adds data provenance to import jobs from read sets and references


2.17.38
=======

* api-change:``workspaces``: This release adds support for creating and managing directories that use AWS IAM Identity Center as user identity source. Such directories can be used to create non-Active Directory domain joined WorkSpaces Personal.Updated RegisterWorkspaceDirectory and DescribeWorkspaceDirectories APIs.
* api-change:``iotsitewise``: AWS IoT SiteWise now supports versioning for asset models. It enables users to retrieve active version of their asset model and perform asset model writes with optimistic lock.


2.17.37
=======

* api-change:``bedrock-agent-runtime``: Releasing the support for Action User Confirmation.
* api-change:``bedrock-agent``: Releasing the support for Action User Confirmation.
* api-change:``supplychain``: Update API documentation to clarify the event SLA as well as the data model expectations
* api-change:``qbusiness``: Amazon QBusiness: Enable support for SAML and OIDC federation through AWS IAM Identity Provider integration.
* api-change:``organizations``: Releasing minor partitional endpoint updates.
* api-change:``codebuild``: Added support for the MAC_ARM environment type for CodeBuild fleets.


2.17.36
=======

* api-change:``quicksight``: Explicit query for authors and dashboard viewing sharing for embedded users
* api-change:``bedrock``: Amazon Bedrock Evaluation BatchDeleteEvaluationJob API allows customers to delete evaluation jobs under terminated evaluation job statuses - Stopped, Failed, or Completed. Customers can submit a batch of 25 evaluation jobs to be deleted at once.
* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Malaysia) Region (ap-southeast-5) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``emr-containers``: Correct endpoint for FIPS is configured for US Gov Regions.
* api-change:``inspector2``: Add enums for Agentless scan statuses and EC2 enablement error states
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now provides EBS health check to manage EC2 instance replacement


2.17.35
=======

* api-change:``ses``: Enable email receiving customers to provide SES with access to their S3 buckets via an IAM role for "Deliver to S3 Action"
* api-change:``lambda``: Release FilterCriteria encryption for Lambda EventSourceMapping,  enabling customers to encrypt their filter criteria using a customer-owned KMS key.
* api-change:``codestar``: The codestar client has been removed following the deprecation of the service on July 31, 2024.
* api-change:``entityresolution``: Increase the mapping attributes in Schema to 35.
* api-change:``ec2``: DescribeInstanceStatus now returns health information on EBS volumes attached to Nitro instances
* api-change:``securityhub``: Security Hub documentation and definition updates
* api-change:``glue``: Add optional field JobRunQueuingEnabled to CreateJob and UpdateJob APIs.


2.17.34
=======

* enhancement:tests: Replaced hard-coded smoke tests with a JSON data file.
* api-change:``ecs``: Documentation only release to address various tickets
* api-change:``s3``: Amazon Simple Storage Service / Features : Add support for conditional writes for PutObject and CompleteMultipartUpload APIs.
* api-change:``opensearchserverless``: Added FailureCode and FailureMessage to BatchGetCollectionResponse for BatchGetVPCEResponse for non-Active Collection and VPCE.


2.17.33
=======

* api-change:``ssm-sap``: Add new attributes to the outputs of GetApplication and GetDatabase APIs.
* api-change:``bedrock``: Amazon Bedrock Batch Inference/ Model Invocation is a feature which allows customers to asynchronously run inference on a large set of records/files stored in S3.
* api-change:``lambda``: Release Lambda FunctionRecursiveConfig, enabling customers to turn recursive loop detection on or off on individual functions. This release adds two new APIs, GetFunctionRecursionConfig and PutFunctionRecursionConfig.
* api-change:``deadline``: This release adds additional search fields and provides sorting by multiple fields.
* api-change:``codebuild``: AWS CodeBuild now supports creating fleets with macOS platform for running builds.


2.17.32
=======

* api-change:``sesv2``: Marking use case description field of account details as deprecated.
* api-change:``inspector2``: Update the correct format of key and values for resource tags
* api-change:``sagemaker``: Introduce Endpoint and EndpointConfig Arns in sagemaker:ListPipelineExecutionSteps API response
* api-change:``batch``: Improvements of integration between AWS Batch and EC2.
* enhancement:``codeartifact``: Update login command error message.
* api-change:``quicksight``: Amazon QuickSight launches Customer Managed Key (CMK) encryption for Data Source metadata


2.17.31
=======

* api-change:``s3``: Amazon Simple Storage Service / Features  : Adds support for pagination in the S3 ListBuckets API.
* api-change:``iam``: Make the LastUsedDate field in the GetAccessKeyLastUsed response optional. This may break customers who only call the API for access keys with a valid LastUsedDate. This fixes a deserialization issue for access keys without a LastUsedDate, because the field was marked as required but could be null.
* api-change:``ecs``: This release introduces a new ContainerDefinition configuration to support the customer-managed keys for ECS container restart feature.
* api-change:``docdb``: This release adds Global Cluster Failover capability which enables you to change your global cluster's primary AWS region, the region that serves writes, during a regional outage. Performing a failover action preserves your Global Cluster setup.


2.17.30
=======

* api-change:``codebuild``: AWS CodeBuild now supports using Secrets Manager to store git credentials and using multiple source credentials in a single project.


2.17.29
=======

* api-change:``glue``: Add AttributesToGet parameter support for Glue GetTables
* api-change:``fis``: This release adds support for additional error information on experiment failure. It adds the error code, location, and account id on relevant failures to the GetExperiment and ListExperiment API responses.
* api-change:``amplify``: Add a new field "cacheConfig" that enables users to configure the CDN cache settings for an App
* api-change:``neptune-graph``: Amazon Neptune Analytics provides a new option for customers to load data into a graph using the RDF (Resource Description Framework) NTRIPLES format. When loading NTRIPLES files, use the value `convertToIri` for the `blankNodeHandling` parameter.
* api-change:``appstream``: This release includes following new APIs: CreateThemeForStack, DescribeThemeForStack, UpdateThemeForStack, DeleteThemeForStack to support custom branding programmatically.


2.17.28
=======

* api-change:``sagemaker``: Releasing large data support as part of CreateAutoMLJobV2 in SageMaker Autopilot and CreateDomain API for SageMaker Canvas.
* api-change:``medialive``: AWS Elemental MediaLive now supports now supports editing the PID values for a Multiplex.
* api-change:``compute-optimizer``: Doc only update for Compute Optimizer that fixes several customer-reported issues relating to ECS finding classifications
* api-change:``eks``: Added support for new AL2023 GPU AMIs to the supported AMITypes.
* api-change:``ec2``: This release adds new capabilities to manage On-Demand Capacity Reservations including the ability to split your reservation, move capacity between reservations, and modify the instance eligibility of your reservation.
* api-change:``config``: Documentation update for the OrganizationConfigRuleName regex pattern.
* api-change:``groundstation``: Updating documentation for OEMEphemeris to link to AWS Ground Station User Guide


2.17.27
=======

* api-change:``cognito-idp``: Fixed a description of AdvancedSecurityAdditionalFlows in Amazon Cognito user pool configuration.
* api-change:``connect``: This release supports adding RoutingCriteria via UpdateContactRoutingData public API.
* api-change:``ssm``: Systems Manager doc-only updates for August 2024.


2.17.26
=======

* api-change:``cognito-idp``: Added support for threat protection for custom authentication in Amazon Cognito user pools.
* api-change:``connect``: This release fixes a regression in number of access control tags that are allowed to be added to a security profile in Amazon Connect. You can now add up to four access control tags on a single security profile.
* api-change:``glue``: This release adds support to retrieve the validation status when creating or updating Glue Data Catalog Views. Also added is support for BasicCatalogTarget partition keys.
* api-change:``ec2``: Launch of private IPv6 addressing for VPCs and Subnets. VPC IPAM supports the planning and monitoring of private IPv6 usage.


2.17.25
=======

* api-change:``glue``: Introducing AWS Glue Data Quality anomaly detection, a new functionality that uses ML-based solutions to detect data anomalies users have not explicitly defined rules for.
* api-change:``appintegrations``: Updated CreateDataIntegration and CreateDataIntegrationAssociation API to support bulk data export from Amazon Connect Customer Profiles to the customer S3 bucket.


2.17.24
=======

* enhancement:awscrt: Update awscrt version requirement to 0.21.2
* api-change:``workspaces``: Added support for BYOL_GRAPHICS_G4DN_WSP IngestionProcess
* api-change:``cost-optimization-hub``: This release adds savings percentage support to the ListRecommendationSummaries API.
* api-change:``cognito-idp``: Advanced security feature updates to include password history and log export for Cognito user pools.
* api-change:``bedrock-agent-runtime``: Introduce model invocation output traces for orchestration traces, which contain the model's raw response and usage.


2.17.23
=======

* api-change:``datazone``: This releases Data Product feature. Data Products allow grouping data assets into cohesive, self-contained units for ease of publishing for data producers, and ease of finding and accessing for data consumers.
* api-change:``kinesis-video-webrtc-storage``: Add JoinStorageSessionAsViewer API
* api-change:``ecr``: Released two new APIs along with documentation updates. The GetAccountSetting API is used to view the current basic scan type version setting for your registry, while the PutAccountSetting API is used to update the basic scan type version for your registry.
* api-change:``pi``: Added a description for the Dimension db.sql.tokenized_id on the DimensionGroup data type page.


2.17.22
=======

* api-change:``cloudwatch``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``kinesis``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``waf-regional``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``route53``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``resiliencehub``: Customers are presented with the grouping recommendations and can determine if the recommendations are accurate and apply to their case. This feature simplifies onboarding by organizing resources into appropriate AppComponents.


2.17.21
=======

* api-change:``controlcatalog``: AWS Control Tower provides two new public APIs controlcatalog:ListControls and controlcatalog:GetControl under controlcatalog service namespace, which enable customers to programmatically retrieve control metadata of available controls.
* api-change:``sagemaker``: This release adds support for Amazon EMR Serverless applications in SageMaker Studio for running data processing jobs.
* api-change:``memorydb``: Doc only update for changes to deletion API.
* api-change:``controltower``: Updated Control Tower service documentation for controlcatalog control ARN support with existing Control Tower public APIs
* api-change:``support``: Doc only updates to CaseDetails
* api-change:``bedrock``: API and Documentation for Bedrock Model Copy feature. This feature lets you share and copy a custom model from one region to another or one account to another.
* api-change:``iam``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``rds``: This release adds support for specifying optional MinACU parameter in CreateDBShardGroup and ModifyDBShardGroup API. DBShardGroup response will contain MinACU if specified.
* api-change:``ssm-quicksetup``: This release adds API support for the QuickSetup feature of AWS Systems Manager


2.17.20
=======

* api-change:``codepipeline``: AWS CodePipeline V2 type pipelines now support stage level conditions to enable development teams to safely release changes that meet quality and compliance requirements.
* api-change:``tnb``: This release adds Network Service Update, through which customers will be able to update their instantiated networks to a new network package. See the documentation for limitations. The release also enhances the Get network operation API to return parameter overrides used during the operation.
* api-change:``logs``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``rolesanywhere``: IAM RolesAnywhere now supports custom role session name on the CreateSession. This release adds the acceptRoleSessionName option to a profile to control whether a role session name will be accepted in a session request with a given profile.
* api-change:``elasticache``: Doc only update for changes to deletion API.
* api-change:``workspaces``: Removing multi-session as it isn't supported for pools
* api-change:``events``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``lexv2-models``: This release adds new capabilities to the AMAZON.QnAIntent: Custom prompting, Guardrails integration and ExactResponse support for Bedrock Knowledge Base.
* api-change:``autoscaling``: Increase the length limit for VPCZoneIdentifier from 2047 to 5000
* api-change:``appstream``: Added support for Red Hat Enterprise Linux 8 on Amazon AppStream 2.0
* bugfix:``s3``: Disable usage of mb command with S3 Express directory buckets.
* api-change:``elb``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.17.19
=======

* api-change:``elasticache``: Renaming full service name as it appears in developer documentation.
* api-change:``memorydb``: Renaming full service name as it appears in developer documentation.


2.17.18
=======

* api-change:``application-autoscaling``: Application Auto Scaling is now more responsive to the changes in demand of your SageMaker Inference endpoints. To get started, create or update a Target Tracking policy based on High Resolution CloudWatch metrics.
* api-change:``elbv2``: This release adds support for sharing trust stores across accounts and organizations through integration with AWS Resource Access Manager.
* api-change:``network-firewall``: You can now log events that are related to TLS inspection, in addition to the existing alert and flow logging.
* api-change:``outposts``: Adding default vCPU information to GetOutpostSupportedInstanceTypes and GetOutpostInstanceTypes responses
* api-change:``codecommit``: CreateRepository API now throws OperationNotAllowedException when the account has been restricted from creating a repository.
* api-change:``stepfunctions``: This release adds support to customer managed KMS key encryption in AWS Step Functions.
* api-change:``bedrock-runtime``: Provides ServiceUnavailableException error message
* api-change:``application-signals``: CloudWatch Application Signals now supports application logs correlation with traces and operational health metrics of applications running on EC2 instances. Users can view the most relevant telemetry to troubleshoot application health anomalies such as spikes in latency, errors, and availability.
* api-change:``datazone``: Introduces GetEnvironmentCredentials operation to SDK
* api-change:``ecr``: API and documentation updates for Amazon ECR, adding support for creating, updating, describing and deleting ECR Repository Creation Template.
* api-change:``eks``: This release adds support for EKS cluster to manage extended support.
* api-change:``ec2``: EC2 Fleet now supports using custom identifiers to reference Amazon Machine Images (AMI) in launch requests that are configured to choose from a diversified list of instance types.


2.17.17
=======

* api-change:``cleanrooms``: Three enhancements to the AWS Clean Rooms: Disallowed Output Columns, Flexible Result Receivers, SQL as a Seed
* api-change:``dynamodb``: DynamoDB doc only update for July
* api-change:``medical-imaging``: CopyImageSet API adds copying selected instances between image sets, and overriding inconsistent metadata with a force parameter. UpdateImageSetMetadata API enables reverting to prior versions; updates to Study, Series, and SOP Instance UIDs; and updates to private elements, with a force parameter.
* api-change:``mediapackagev2``: This release adds support for Irdeto DRM encryption in DASH manifests.
* api-change:``pinpoint-sms-voice-v2``: Update for rebrand to AWS End User Messaging SMS and Voice.
* api-change:``iotsitewise``: Adds support for creating SiteWise Edge gateways that run on a Siemens Industrial Edge Device.


2.17.16
=======

* api-change:``cleanrooms``: This release adds AWS Entity Resolution integration to associate ID namespaces & ID mapping workflow resources as part of ID namespace association and  ID mapping table  in AWS Clean Rooms. It also introduces a new ID_MAPPING_TABLE analysis rule to manage the protection on ID mapping table.
* api-change:``datazone``: This release removes the deprecated dataProductItem field from Search API output.
* api-change:``connect``: Added PostContactSummary segment type on ListRealTimeContactAnalysisSegmentsV2 API
* api-change:``entityresolution``: Support First Party ID Mapping
* api-change:``cleanroomsml``: Adds SQL query as the source of seed audience for audience generation job.
* api-change:``appsync``: Adding support for paginators in AppSync list APIs
* api-change:``connect-contact-lens``: Added PostContactSummary segment type on ListRealTimeContactAnalysisSegments API


2.17.15
=======

* api-change:``ivs``: Documentation update for IVS Low Latency API Reference.
* api-change:``datazone``: This release adds 1/ support of register S3 locations of assets in AWS Lake Formation hybrid access mode for DefaultDataLake blueprint. 2/ support of CRUD operations for Asset Filters.
* api-change:``neptune-graph``: Amazon Neptune Analytics provides new options for customers to start with smaller graphs at a lower cost. CreateGraph, CreaateGraphImportTask, UpdateGraph and StartImportTask APIs will now allow 32 and 64 for `provisioned-memory`
* api-change:``redshift-serverless``: Adds dualstack support for Redshift Serverless workgroup.
* api-change:``mobile``: The mobile service has been removed following its deprecation.


2.17.14
=======

* api-change:``connect``: Amazon Connect expands search API coverage for additional resources.  Search for hierarchy groups by name, ID, tag, or other criteria (new endpoint). Search for agent statuses by name, ID, tag, or other criteria (new endpoint). Search for users by their assigned proficiencies (enhanced endpoint)
* api-change:``taxsettings``: Set default endpoint for aws partition. Requests from all regions in aws partition will be forward to us-east-1 endpoint.
* api-change:``workspaces-thin-client``: Documentation update for WorkSpaces Thin Client.
* bugfix:wait: Update waiters to handle expected boolean values when matching errors (`aws/aws-cli#3220 <https://github.com/aws/aws-cli/issues/3220>`__)
* api-change:``medialive``: AWS Elemental MediaLive now supports the SRT protocol via the new SRT Caller input type.
* api-change:``sagemaker``: SageMaker Training supports R5, T3 and R5D instances family. And SageMaker Processing supports G5 and R5D instances family.
* api-change:``secretsmanager``: Doc only update for Secrets Manager
* api-change:``ivschat``: Documentation update for IVS Chat API Reference.
* api-change:``timestream-query``: Doc-only update for TimestreamQuery. Added guidance about the accepted valid value for the QueryPricingModel parameter.
* api-change:``rds``: Updates Amazon RDS documentation to specify an eventual consistency model for DescribePendingMaintenanceActions.
* api-change:``ec2``: Amazon VPC IP Address Manager (IPAM) now supports Bring-Your-Own-IP (BYOIP) for IP addresses registered with any Internet Registry. This feature uses DNS TXT records to validate ownership of a public IP address range.
* api-change:``acm-pca``: Fix broken waiters for the acm-pca client.  Waiters broke in version 1.13.144 of the Boto3 SDK.
* api-change:``firehose``: This release 1) Add configurable buffering hints for Snowflake as destination. 2) Add ReadFromTimestamp for MSK As Source. Firehose will start reading data from MSK Cluster using offset associated with this timestamp. 3) Gated public beta release to add Apache Iceberg tables as destination.


2.17.13
=======

* api-change:``arc-zonal-shift``: Adds the option to subscribe to get notifications when a zonal autoshift occurs in a region.
* api-change:``globalaccelerator``: This feature adds exceptions to the Customer API to avoid throwing Internal Service errors
* api-change:``quicksight``: Vega ally control options and Support for Reviewed Answers in Topics
* api-change:``acm-pca``: Minor refactoring of C2J model for AWS Private CA
* api-change:``pinpoint``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.17.12
=======

* api-change:``groundstation``: Documentation update specifying OEM ephemeris units of measurement
* enhancement:Python: Update bundled Python interpreter version to 3.11.9
* api-change:``glue``: Add recipe step support for recipe node
* api-change:``bedrock``: Add support for contextual grounding check for Guardrails for Amazon Bedrock.
* api-change:``bedrock-agent-runtime``: Introduces query decomposition, enhanced Agents integration with Knowledge bases, session summary generation, and code interpretation (preview) for Claude V3 Sonnet and Haiku models. Also introduces Prompt Flows (preview) to link prompts, foundational models, and resources for end-to-end solutions.
* api-change:``bedrock-agent``: Introduces new data sources and chunking strategies for Knowledge bases, advanced parsing logic using FMs, session summary generation, and code interpretation (preview) for Claude V3 Sonnet and Haiku models. Also introduces Prompt Flows (preview) to link prompts, foundational models, and resources.
* api-change:``ec2``: Add parameters to enable provisioning IPAM BYOIPv4 space at a Local Zone Network Border Group level
* api-change:``license-manager-linux-subscriptions``: Add support for third party subscription providers, starting with RHEL subscriptions through Red Hat Subscription Manager (RHSM). Additionally, add support for tagging subscription provider resources, and detect when an instance has more than one Linux subscription and notify the customer.
* api-change:``batch``: This feature allows AWS Batch Jobs with EKS container orchestration type to be run as Multi-Node Parallel Jobs.
* api-change:``mediaconnect``: AWS Elemental MediaConnect introduces the ability to disable outputs. Disabling an output allows you to keep the output attached to the flow, but stop streaming to the output destination. A disabled output does not incur data transfer costs.
* api-change:``bedrock-runtime``: Add support for contextual grounding check and ApplyGuardrail API for Guardrails for Amazon Bedrock.


2.17.11
=======

* api-change:``opensearch``: This release adds support for enabling or disabling Natural Language Query Processing feature for Amazon OpenSearch Service domains, and provides visibility into the current state of the setup or tear-down.
* api-change:``sagemaker``: This release 1/ enables optimization jobs that allows customers to perform Ahead-of-time compilation and quantization. 2/ allows customers to control access to Amazon Q integration in SageMaker Studio. 3/ enables AdditionalModelDataSources for CreateModel action.
* api-change:``datazone``: This release deprecates dataProductItem field from SearchInventoryResultItem, along with some unused DataProduct shapes
* api-change:``fsx``: Adds support for FSx for NetApp ONTAP 2nd Generation file systems, and FSx for OpenZFS Single AZ HA file systems.


2.17.10
=======

* api-change:``ses``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``es``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``qapps``: This is a general availability (GA) release of Amazon Q Apps, a capability of Amazon Q Business. Q Apps leverages data sources your company has provided to enable users to build, share, and customize apps within your organization.
* api-change:``gamelift``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``dms``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``elasticbeanstalk``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``devicefarm``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``route53resolver``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``codedeploy``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``firehose``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.17.9
======

* api-change:``acm``: Documentation updates, including fixes for xml formatting, broken links, and ListCertificates description.
* api-change:``ecr``: This release for Amazon ECR makes change to bring the SDK into sync with the API.
* api-change:``qbusiness``: Add personalization to Q Applications. Customers can enable or disable personalization when creating or updating a Q application with the personalization configuration.
* api-change:``payment-cryptography-data``: Added further restrictions on logging of potentially sensitive inputs and outputs.


2.17.8
======

* api-change:``organizations``: Added a new reason under ConstraintViolationException in RegisterDelegatedAdministrator API to prevent registering suspended accounts as delegated administrator of a service.
* api-change:``workspaces``: Fix create workspace bundle RootStorage/UserStorage to accept non null values
* api-change:``directconnect``: This update includes documentation for support of new native 400 GBps ports for Direct Connect.
* api-change:``application-autoscaling``: Doc only update for Application Auto Scaling that fixes resource name.
* api-change:``rekognition``: This release adds support for tagging projects and datasets with the CreateProject and CreateDataset APIs.


2.17.7
======

* api-change:``s3``: Added response overrides to Head Object requests.
* api-change:``ec2``: Documentation updates for Elastic Compute Cloud (EC2).
* enhancement:openssl: Update bundled OpenSSL version to 1.1.1y for Linux installers
* api-change:``fms``: Increases Customer API's ManagedServiceData length


2.17.6
======

* api-change:``stepfunctions``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``apigateway``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``eks``: Updates EKS managed node groups to support EC2 Capacity Blocks for ML
* api-change:``payment-cryptography-data``: Adding support for dynamic keys for encrypt, decrypt, re-encrypt and translate pin functions.  With this change, customers can use one-time TR-31 keys directly in dataplane operations without the need to first import them into the service.
* api-change:``connect``: Authentication profiles are Amazon Connect resources (in gated preview) that allow you to configure authentication settings for users in your contact center. This release adds support for new ListAuthenticationProfiles, DescribeAuthenticationProfile and UpdateAuthenticationProfile APIs.
* api-change:``docdb``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``payment-cryptography``: Added further restrictions on logging of potentially sensitive inputs and outputs.
* api-change:``swf``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``cognito-identity``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``wafv2``: JSON body inspection: Update documentation to clarify that JSON parsing doesn't include full validation.


2.17.5
======

* api-change:``acm-pca``: Added CCPC_LEVEL_1_OR_HIGHER KeyStorageSecurityStandard and SM2 KeyAlgorithm and SM3WITHSM2 SigningAlgorithm for China regions.
* api-change:``connect``: This release supports showing PreferredAgentRouting step via DescribeContact API.
* api-change:``opensearch``: This release removes support for enabling or disabling Natural Language Query Processing feature for Amazon OpenSearch Service domains.
* api-change:``kinesisanalyticsv2``: Support for Flink 1.19 in Managed Service for Apache Flink
* api-change:``workspaces``: Added support for Red Hat Enterprise Linux 8 on Amazon WorkSpaces Personal.
* api-change:``pi``: Noting that the filter db.sql.db_id isn't available for RDS for SQL Server DB instances.
* api-change:``cloudhsmv2``: Added 3 new APIs to support backup sharing: GetResourcePolicy, PutResourcePolicy, and DeleteResourcePolicy. Added BackupArn to the output of the DescribeBackups API. Added support for BackupArn in the CreateCluster API.
* api-change:``emr``: This release provides the support for new allocation strategies i.e. CAPACITY_OPTIMIZED_PRIORITIZED for Spot and PRIORITIZED for On-Demand by taking input of priority value for each instance type for instance fleet clusters.
* api-change:``glue``: Added AttributesToGet parameter to Glue GetDatabases, allowing caller to limit output to include only the database name.


2.17.4
======

* api-change:``datazone``: This release supports the data lineage feature of business data catalog in Amazon DataZone.
* api-change:``qconnect``: Adds CreateContentAssociation, ListContentAssociations, GetContentAssociation, and DeleteContentAssociation APIs.
* api-change:``elasticache``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``cloudfront``: Doc only update for CloudFront that fixes customer-reported issue
* api-change:``workspaces``: Added support for WorkSpaces Pools.
* api-change:``chime-sdk-media-pipelines``: Added Amazon Transcribe multi language identification to Chime SDK call analytics. Enabling customers sending single stream audio to generate call recordings using Chime SDK call analytics
* api-change:``sagemaker``: Add capability for Admins to customize Studio experience for the user by showing or hiding Apps and MLTools.
* api-change:``mq``: This release makes the EngineVersion field optional for both broker and configuration and uses the latest available version by default. The AutoMinorVersionUpgrade field is also now optional for broker creation and defaults to 'true'.
* api-change:``rds``: Updates Amazon RDS documentation for TAZ export to S3.
* api-change:``quicksight``: Adding support for Repeating Sections, Nested Filters
* api-change:``application-autoscaling``: Amazon WorkSpaces customers can now use Application Auto Scaling to automatically scale the number of virtual desktops in a WorkSpaces pool.


2.17.3
======

* api-change:``eks``: Added support for disabling unmanaged addons during cluster creation.
* api-change:``kinesisanalyticsv2``: This release adds support for new ListApplicationOperations and DescribeApplicationOperation APIs. It adds a new configuration to enable system rollbacks, adds field ApplicationVersionCreateTimestamp for clarity and improves support for pagination for APIs.
* api-change:``opensearch``: This release adds support for enabling or disabling Natural Language Query Processing feature for Amazon OpenSearch Service domains, and provides visibility into the current state of the setup or tear-down.
* api-change:``ivs-realtime``: IVS Real-Time now offers customers the ability to upload public keys for customer vended participant tokens.
* api-change:``controltower``: Added ListLandingZoneOperations API.


2.17.2
======

* api-change:``autoscaling``: Doc only update for Auto Scaling's TargetTrackingMetricDataQuery
* api-change:``ec2``: This release is for the launch of the new u7ib-12tb.224xlarge, R8g, c7gn.metal and mac2-m1ultra.metal instance types
* api-change:``networkmanager``: This is model changes & documentation update for the Asynchronous Error Reporting feature for AWS Cloud WAN. This feature allows customers to view errors that occur while their resources are being provisioned, enabling customers to fix their resources without needing external support.
* api-change:``workspaces-thin-client``: This release adds the deviceCreationTags field to CreateEnvironment API input, UpdateEnvironment API input and GetEnvironment API output.


2.17.1
======

* api-change:``qbusiness``: Allow enable/disable Q Apps when creating/updating a Q application; Return the Q Apps enablement information when getting a Q application.
* api-change:``ec2``: Fix EC2 multi-protocol info in models.
* api-change:``ssm``: Add sensitive trait to SSM IPAddress property for CloudTrail redaction
* api-change:``customer-profiles``: This release includes changes to ProfileObjectType APIs, adds functionality top set and get capacity for profile object types.
* api-change:``workspaces-web``: Added ability to enable DeepLinking functionality on a Portal via UserSettings as well as added support for IdentityProvider resource tagging.
* api-change:``bedrock-runtime``: Increases Converse API's document name length


2.17.0
======

* api-change:``securityhub``: Documentation updates for Security Hub
* api-change:``cost-optimization-hub``: This release enables AWS Cost Optimization Hub to show cost optimization recommendations for Amazon RDS MySQL and RDS PostgreSQL.
* api-change:``dynamodb``: Doc-only update for DynamoDB. Fixed Important note in 6 Global table APIs - CreateGlobalTable, DescribeGlobalTable, DescribeGlobalTableSettings, ListGlobalTables, UpdateGlobalTable, and UpdateGlobalTableSettings.
* api-change:``glue``: Fix Glue paginators for Jobs, JobRuns, Triggers, Blueprints and Workflows.
* api-change:``codeartifact``: Add support for the Cargo package format.
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate optimization recommendations for Amazon RDS MySQL and RDS PostgreSQL.
* api-change:``sagemaker``: Adds support for model references in Hub service, and adds support for cross-account access of Hubs
* api-change:``ivs-realtime``: IVS Real-Time now offers customers the ability to record individual stage participants to S3.
* api-change:``bedrock-runtime``: This release adds document support to Converse and ConverseStream APIs
* feature:macOS: End of support for macOS 10.14 and prior


2.16.12
=======

* api-change:``artifact``: This release adds an acceptanceType field to the ReportSummary structure (used in the ListReports API response).
* api-change:``opensearch``: This release enables customers to use JSON Web Tokens (JWT) for authentication on their Amazon OpenSearch Service domains.
* api-change:``cur``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``directconnect``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``athena``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``elastictranscoder``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.16.11
=======

* api-change:``lightsail``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``shield``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``sagemaker``: Launched a new feature in SageMaker to provide managed MLflow Tracking Servers for customers to track ML experiments. This release also adds a new capability of attaching additional storage to SageMaker HyperPod cluster instances.
* api-change:``bedrock-runtime``: This release adds support for using Guardrails with the Converse and ConverseStream APIs.
* api-change:``snowball``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``rekognition``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``polly``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``cloudtrail``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``eks``: This release adds support to surface async fargate customer errors from async path to customer through describe-fargate-profile API response.
* api-change:``config``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.16.10
=======

* api-change:``mediaconvert``: This release includes support for creating I-frame only video segments for DASH trick play.
* api-change:``waf``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``cognito-idp``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``efs``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``acm-pca``: Doc-only update that adds name constraints as an allowed extension for ImportCertificateAuthorityCertificate.
* api-change:``ds``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``batch``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``secretsmanager``: Doc only update for Secrets Manager
* api-change:``codebuild``: AWS CodeBuild now supports global and organization GitHub webhooks
* api-change:``glue``: This release introduces a new feature, Usage profiles. Usage profiles allow the AWS Glue admin to create different profiles for various classes of users within the account, enforcing limits and defaults for jobs and sessions.


2.16.9
======

* api-change:``route53domains``: Add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``mediaconvert``: This release adds the ability to search for historical job records within the management console using a search box and/or via the SDK/CLI with partial string matching search on input file name.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``datazone``: This release introduces a new default service blueprint for custom environment creation.
* api-change:``macie2``: This release adds support for managing the status of automated sensitive data discovery for individual accounts in an organization, and determining whether individual S3 buckets are included in the scope of the analyses.


2.16.8
======

* api-change:``iotwireless``: Add RoamingDeviceSNR and RoamingDeviceRSSI to Customer Metrics.
* api-change:``kms``: This feature allows customers to use their keys stored in KMS to derive a shared secret which can then be used to establish a secured channel for communication, provide proof of possession, or establish trust with other parties.
* bugfix:Parsers: Fixes datetime parse error handling for out-of-range and negative timestamps
* api-change:``glue``: This release adds support for configuration of evaluation method for composite rules in Glue Data Quality rulesets.
* api-change:``cloudhsmv2``: Added support for hsm type hsm2m.medium. Added supported for creating a cluster in FIPS or NON_FIPS mode.
* api-change:``mediapackagev2``: This release adds support for CMAF ingest (DASH-IF live media ingest protocol interface 1)


2.16.7
======

* api-change:``securitylake``: This release updates request validation regex to account for non-commercial aws partitions.
* api-change:``apptest``: AWS Mainframe Modernization Application Testing is an AWS Mainframe Modernization service feature that automates functional equivalence testing for mainframe application modernization and migration to AWS, and regression testing.
* api-change:``osis``: SDK changes for self-managed vpc endpoint to OpenSearch ingestion pipelines.
* api-change:``sesv2``: This release adds support for Amazon EventBridge as an email sending events destination.
* api-change:``ec2``: Tagging support for Traffic Mirroring FilterRule resource
* api-change:``redshift``: Updates to remove DC1 and DS2 node types.
* api-change:``backupstorage``: The backupstorage client has been removed following the deprecation of the service.
* api-change:``secretsmanager``: Introducing RotationToken parameter for PutSecretValue API


2.16.6
======

* api-change:``sagemaker``: Introduced Scope and AuthenticationRequestExtraParams to SageMaker Workforce OIDC configuration; this allows customers to modify these options for their private Workforce IdP integration. Model Registry Cross-account model package groups are discoverable.
* api-change:``pca-connector-scep``: Connector for SCEP allows you to use a managed, cloud CA to enroll mobile devices and networking gear. SCEP is a widely-adopted protocol used by mobile device management (MDM) solutions for enrolling mobile devices. With the connector, you can use AWS Private CA with popular MDM solutions.
* api-change:``networkmanager``: This is model changes & documentation update for Service Insertion feature for AWS Cloud WAN. This feature allows insertion of AWS/3rd party security services on Cloud WAN. This allows to steer inter/intra segment traffic via security appliances and provide visibility to the route updates.
* api-change:``accessanalyzer``: IAM Access Analyzer now provides policy recommendations to help resolve unused permissions for IAM roles and users. Additionally, IAM Access Analyzer now extends its custom policy checks to detect when IAM policies grant public access or access to critical resources ahead of deployments.
* enhancement:awscrt: Update ``awscrt`` version range ceiling to 0.20.11
* api-change:``guardduty``: Added API support for GuardDuty Malware Protection for S3.


2.16.5
======

* api-change:``ecs``: This release introduces a new cluster configuration to support the customer-managed keys for ECS managed storage encryption.
* api-change:``imagebuilder``: This release updates the regex pattern for Image Builder ARNs.
* api-change:``application-signals``: This is the initial SDK release for Amazon CloudWatch Application Signals. Amazon CloudWatch Application Signals provides curated application performance monitoring for developers to monitor and troubleshoot application health using pre-built dashboards and Service Level Objectives.


2.16.4
======

* api-change:``b2bi``: Added exceptions to B2Bi List operations and ConflictException to B2Bi StartTransformerJob operation. Also made capabilities field explicitly required when creating a Partnership.
* api-change:``sagemaker``: This release introduces a new optional parameter: InferenceAmiVersion, in ProductionVariant.
* api-change:``verifiedpermissions``: This release adds OpenIdConnect (OIDC) configuration support for IdentitySources, allowing for external IDPs to be used in authorization requests.
* api-change:``codepipeline``: CodePipeline now supports overriding S3 Source Object Key during StartPipelineExecution, as part of Source Overrides.
* api-change:``auditmanager``: New feature: common controls. When creating custom controls, you can now use pre-grouped AWS data sources based on common compliance themes. Also, the awsServices parameter is deprecated because we now manage services in scope for you. If used, the input is ignored and an empty list is returned.


2.16.3
======

* api-change:``account``: This release adds 3 new APIs (AcceptPrimaryEmailUpdate, GetPrimaryEmail, and StartPrimaryEmailUpdate) used to centrally manage the root user email address of member accounts within an AWS organization.
* api-change:``fsx``: This release adds support to increase metadata performance on FSx for Lustre file systems beyond the default level provisioned when a file system is created. This can be done by specifying MetadataConfiguration during the creation of Persistent_2 file systems or by updating it on demand.
* api-change:``firehose``: Adds integration with Secrets Manager for Redshift, Splunk, HttpEndpoint, and Snowflake destinations
* api-change:``glue``: This release adds support for creating and updating Glue Data Catalog Views.
* api-change:``alexaforbusiness``: The alexaforbusiness client has been removed following the deprecation of the service.
* api-change:``sqs``: Doc only updates for SQS. These updates include customer-reported issues and TCX3 modifications.
* api-change:``iotwireless``: Adds support for wireless device to be in Conflict FUOTA Device Status due to a FUOTA Task, so it couldn't be attached to a new one.
* api-change:``storagegateway``: Adds SoftwareUpdatePreferences to DescribeMaintenanceStartTime and UpdateMaintenanceStartTime, a structure which contains AutomaticUpdatePolicy.
* api-change:``location``: Added two new APIs, VerifyDevicePosition and ForecastGeofenceEvents. Added support for putting larger geofences up to 100,000 vertices with Geobuf fields.
* api-change:`honeycode`: The honeycode client has been removed following the deprecation of the service.
* api-change:``sns``: Doc-only update for SNS. These changes include customer-reported issues and TXC3 updates.


2.16.2
======

* api-change:``s3``: Added new params copySource and key to copyObject API for supporting S3 Access Grants plugin. These changes will not change any of the existing S3 API functionality.
* api-change:``glue``: AWS Glue now supports native SaaS connectivity: Salesforce connector available now
* bugfix:emr customization: Update the EC2 service principal when creating the trust policy for EMR default roles to always be ec2.amazonaws.com.
* api-change:``globalaccelerator``: This release contains a new optional ip-addresses input field for the update accelerator and update custom routing accelerator apis. This input enables consumers to replace IPv4 addresses on existing accelerators with addresses provided in the input.


2.16.1
======

* api-change:``ec2``: U7i instances with up to 32 TiB of DDR5 memory and 896 vCPUs are now available. C7i-flex instances are launched and are lower-priced variants of the Amazon EC2 C7i instances that offer a baseline level of CPU performance with the ability to scale up to the full compute performance 95% of the time.
* api-change:``taxsettings``: Initial release of AWS Tax Settings API
* api-change:``pipes``: This release adds Timestream for LiveAnalytics as a supported target in EventBridge Pipes
* api-change:``sagemaker``: Extend DescribeClusterNode response with private DNS hostname and IP address, and placement information about availability zone and availability zone ID.


2.16.0
======

* api-change:``amplify``: This doc-only update identifies fields that are specific to Gen 1 and Gen 2 applications.
* api-change:``iottwinmaker``: Support RESET_VALUE UpdateType for PropertyUpdates to reset property value to default or null
* api-change:``batch``: This release adds support for the AWS Batch GetJobQueueSnapshot API operation.
* feature:logs start-live-tail: Adds support for starting a live tail streaming session for one or more log groups.
* api-change:``eks``: Adds support for EKS add-ons pod identity associations integration


2.15.62
=======

* api-change:``codeguru-security``: This release includes minor model updates and documentation updates.
* api-change:``launch-wizard``: This release adds support for describing workload deployment specifications, deploying additional workload types, and managing tags for Launch Wizard resources with API operations.
* api-change:``codebuild``: AWS CodeBuild now supports Self-hosted GitHub Actions runners for Github Enterprise
* api-change:``elasticache``: Update to attributes of TestFailover and minor revisions.


2.15.61
=======

* api-change:``rds``: Updates Amazon RDS documentation for Aurora Postgres DBname.
* api-change:``cloudtrail``: CloudTrail Lake returns PartitionKeys in the GetEventDataStore API response. Events are grouped into partitions based on these keys for better query performance. For example, the calendarday key groups events by day, while combining the calendarday key with the hour key groups them by day and hour.
* api-change:``bedrock-runtime``: This release adds Converse and ConverseStream APIs to Bedrock Runtime
* api-change:``connect``: Adding associatedQueueIds as a SearchCriteria and response field to the SearchRoutingProfiles API
* api-change:``bedrock-agent``: With this release, Knowledge bases for Bedrock adds support for Titan Text Embedding v2.
* api-change:``sagemaker``: Adds Model Card information as a new component to Model Package. Autopilot launches algorithm selection for TimeSeries modality to generate AutoML candidates per algorithm.
* bugfix:``ssm start-session``: Only provide profile name to session-manager-plugin if provided using --profile flag
* api-change:``emr-serverless``: The release adds support for spark structured streaming.
* api-change:``acm``: add v2 smoke tests and smithy smokeTests trait for SDK testing.


2.15.60
=======

* api-change:``athena``: Throwing validation errors on CreateNotebook with Name containing `/`,`:`,`\`
* api-change:``connect``: This release includes changes to DescribeContact API's response by including ConnectedToSystemTimestamp, RoutingCriteria, Customer, Campaign, AnsweringMachineDetectionStatus, CustomerVoiceActivity, QualityMetrics, DisconnectDetails, and SegmentAttributes information from a contact in Amazon Connect.
* api-change:``securityhub``: Add ROOT type for TargetType model
* api-change:``glue``: Add optional field JobMode to CreateJob and UpdateJob APIs.
* api-change:``codebuild``: AWS CodeBuild now supports manually creating GitHub webhooks


2.15.59
=======

* api-change:``dynamodb``: Doc-only update for DynamoDB. Specified the IAM actions needed to authorize a user to create a table with a resource-based policy.
* api-change:``ec2``: Providing support to accept BgpAsnExtended attribute
* api-change:``kafka``: Adds ControllerNodeInfo in ListNodes response to support Raft mode for MSK
* api-change:``swf``: This release adds new APIs for deleting activity type and workflow type resources.


2.15.58
=======

* api-change:``dynamodb``: Documentation only updates for DynamoDB.
* bugfix:endpoints: Include params set in provide-client-param event handlers in dynamic context params for endpoint resolution.
* api-change:``iotfleetwise``: AWS IoT FleetWise now supports listing vehicles with attributes filter, ListVehicles API is updated to support additional attributes filter.
* api-change:``managedblockchain``: This is a minor documentation update to address the impact of the shut down of the Goerli and Polygon networks.


2.15.57
=======

* api-change:``emr-serverless``: This release adds the capability to run interactive workloads using Apache Livy Endpoint.
* api-change:``opsworks``: Documentation-only update for OpsWorks Stacks.


2.15.56
=======

* api-change:``opensearch``: This release adds support for enabling or disabling a data source configured as part of Zero-ETL integration with Amazon S3, by setting its status.
* api-change:``cloudformation``: Added DeletionMode FORCE_DELETE_STACK for deleting a stack that is stuck in DELETE_FAILED state due to resource deletion failure.
* api-change:``chatbot``: This change adds support for tagging Chatbot configurations.
* api-change:``wafv2``: You can now use Security Lake to collect web ACL traffic data.
* api-change:``kms``: This release includes feature to import customer's asymmetric (RSA, ECC and SM2) and HMAC keys into KMS in China.


2.15.55
=======

* api-change:``storagegateway``: Added new SMBSecurityStrategy enum named MandatoryEncryptionNoAes128, new mode enforces encryption and disables AES 128-bit algorithums.
* api-change:``cloudfront``: Model update; no change to SDK functionality.
* api-change:``lightsail``: This release adds support for Amazon Lightsail instances to switch between dual-stack or IPv4 only and IPv6-only public IP address types.
* api-change:``rds``: Updates Amazon RDS documentation for Db2 license through AWS Marketplace.
* api-change:``pi``: Performance Insights added a new input parameter called AuthorizedActions to support the fine-grained access feature. Performance Insights also restricted the acceptable input characters.
* api-change:``mailmanager``: This release includes a new Amazon SES feature called Mail Manager, which is a set of email gateway capabilities designed to help customers strengthen their organization's email infrastructure, simplify email workflow management, and streamline email compliance control.
* api-change:``glue``: Add Maintenance window to CreateJob and UpdateJob APIs and JobRun response. Add a new Job Run State for EXPIRED.


2.15.54
=======

* api-change:``secretsmanager``: add v2 smoke tests and smithy smokeTests trait for SDK testing
* api-change:``bedrock-agent-runtime``: This release adds support for using Guardrails with Bedrock Agents.
* api-change:``rds``: This release adds support for EngineLifecycleSupport on DBInstances, DBClusters, and GlobalClusters.
* api-change:``controltower``: Added ListControlOperations API and filtering support for ListEnabledControls API. Updates also includes added metadata for enabled controls and control operations.
* api-change:``bedrock-agent``: This release adds support for using Guardrails with Bedrock Agents.
* api-change:``osis``: Add support for creating an OpenSearch Ingestion pipeline that is attached to a provided VPC. Add information about the destinations of an OpenSearch Ingestion pipeline to the GetPipeline and ListPipelines APIs.


2.15.53
=======

* api-change:``transfer``: Enable use of CloudFormation traits in Smithy model to improve generated CloudFormation schema from the Smithy API model.
* api-change:``codebuild``: Aws CodeBuild now supports 36 hours build timeout
* api-change:``application-autoscaling``: add v2 smoke tests and smithy smokeTests trait for SDK testing.
* api-change:``elbv2``: This release adds dualstack-without-public-ipv4 IP address type for ALB.
* api-change:``lakeformation``: Introduces a new API, GetDataLakePrincipal, that returns the identity of the invoking principal


2.15.52
=======

* api-change:``connect``: Adding Contact Flow metrics to the GetMetricDataV2 API
* api-change:``sagemaker``: Introduced WorkerAccessConfiguration to SageMaker Workteam. This allows customers to configure resource access for workers in a workteam.
* api-change:``mwaa``: Amazon MWAA now supports Airflow web server auto scaling to automatically handle increased demand from REST APIs, Command Line Interface (CLI), or more Airflow User Interface (UI) users. Customers can specify maximum and minimum web server instances during environment creation and update workflow.
* api-change:``kafka``: AWS MSK support for Broker Removal.
* api-change:``quicksight``: This release adds DescribeKeyRegistration and UpdateKeyRegistration APIs to manage QuickSight Customer Managed Keys (CMK).
* api-change:``acm-pca``: This release adds support for waiters to fail on AccessDeniedException when having insufficient permissions
* api-change:``secretsmanager``: Documentation updates for AWS Secrets Manager


2.15.51
=======

* api-change:``bedrock-agent-runtime``: Updating Bedrock Knowledge Base Metadata & Filters feature with two new filters listContains and stringContains
* api-change:``medical-imaging``: Added support for importing medical imaging data from Amazon S3 buckets across accounts and regions.
* api-change:``grafana``: This release adds new ServiceAccount and ServiceAccountToken APIs.
* api-change:``securityhub``: Documentation-only update for AWS Security Hub
* api-change:``codebuild``: CodeBuild Reserved Capacity VPC Support
* enhancement:useragent: Update user agent header format
* api-change:``datasync``: Task executions now display a CANCELLING status when an execution is in the process of being cancelled.


2.15.50
=======

* api-change:``s3``: Updated a few x-id in the http uri traits
* api-change:``connect``: Amazon Connect provides enhanced search capabilities for flows & flow modules on the Connect admin website and programmatically using APIs. You can search for flows and flow modules by name, description, type, status, and tags, to filter and identify a specific flow in your Connect instances.


2.15.49
=======

* api-change:``events``: Amazon EventBridge introduces KMS customer-managed key (CMK) encryption support for custom and partner events published on EventBridge Event Bus (including default bus) and UpdateEventBus API.
* api-change:``vpc-lattice``: This release adds TLS Passthrough support. It also increases max number of target group per rule to 10.


2.15.48
=======

* api-change:``greengrassv2``: Mark ComponentVersion in ComponentDeploymentSpecification as required.
* api-change:``sagemaker``: Introduced support for G6 instance types on Sagemaker Notebook Instances and on SageMaker Studio for JupyterLab and CodeEditor applications.
* api-change:``sso-oidc``: Updated request parameters for PKCE support.
* api-change:``discovery``: add v2 smoke tests and smithy smokeTests trait for SDK testing


2.15.47
=======

* api-change:``ec2``: Adding Precision Hardware Clock (PHC) to public API DescribeInstanceTypes
* api-change:``cognito-idp``: Add EXTERNAL_PROVIDER enum value to UserStatusType.
* api-change:``polly``: Add new engine - generative - that builds the most expressive conversational voices.
* api-change:``ssm-sap``: Added support for application-aware start/stop of SAP applications running on EC2 instances, with SSM for SAP
* api-change:``fms``: The policy scope resource tag is always a string value, either a non-empty string or an empty string.
* api-change:``ecr``: This release adds pull through cache rules support for GitLab container registry in Amazon ECR.
* api-change:``sqs``: This release adds MessageSystemAttributeNames to ReceiveMessageRequest to replace AttributeNames.
* api-change:``bedrock-agent-runtime``: This release adds support to provide guardrail configuration and modify inference parameters that are then used in RetrieveAndGenerate API in Agents for Amazon Bedrock.
* api-change:``verifiedpermissions``: Adds policy effect and actions fields to Policy API's.
* api-change:``route53resolver``: Update the DNS Firewall settings to correct a spelling issue.
* api-change:``pinpoint``: This release adds support for specifying email message headers for Email Templates, Campaigns, Journeys and Send Messages.


2.15.46
=======

* api-change:``route53profiles``: Doc only update for Route 53 profiles that fixes some link  issues
* api-change:``budgets``: This release adds tag support for budgets and budget actions.
* api-change:``resiliencehub``: AWS Resilience Hub has expanded its drift detection capabilities by introducing a new type of drift detection - application resource drift. This new enhancement detects changes, such as the addition or deletion of resources within the application's input sources.
* api-change:``b2bi``: Documentation update to clarify the MappingTemplate definition.


2.15.45
=======

* api-change:``datasync``: Updated guidance on using private or self-signed certificate authorities (CAs) with AWS DataSync object storage locations.
* api-change:``connectcases``: This feature supports the release of Files related items
* api-change:``inspector2``: This release adds CSV format to GetCisScanReport for Inspector v2
* api-change:``sesv2``: Adds support for specifying replacement headers per BulkEmailEntry in SendBulkEmail in SESv2.
* api-change:``connect``: This release adds 5 new APIs for managing attachments: StartAttachedFileUpload, CompleteAttachedFileUpload, GetAttachedFile, BatchGetAttachedFileMetadata, DeleteAttachedFile. These APIs can be used to programmatically upload and download attachments to Connect resources, like cases.
* api-change:``sagemaker``: Amazon SageMaker Inference now supports m6i, c6i, r6i, m7i, c7i, r7i and g5 instance types for Batch Transform Jobs
* api-change:``bedrock-agent``: This release adds support for using Provisioned Throughput with Bedrock Agents.
* api-change:``medialive``: AWS Elemental MediaLive now supports configuring how SCTE 35 passthrough triggers segment breaks in HLS and MediaPackage output groups. Previously, messages triggered breaks in all these output groups. The new option is to trigger segment breaks only in groups that have SCTE 35 passthrough enabled.


2.15.44
=======

* api-change:``securityhub``: Updated CreateMembers API request with limits.
* api-change:``redshift-serverless``: Update Redshift Serverless List Scheduled Actions Output Response to include Namespace Name.
* api-change:``personalize-runtime``: This release adds support for a Reason attribute for predicted items generated by User-Personalization-v2.
* api-change:``sesv2``: Fixes ListContacts and ListImportJobs APIs to use POST instead of GET.
* api-change:``bedrock-agent``: This release adds support for using MongoDB Atlas as a vector store when creating a knowledge base.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``ec2``: This release includes a new API for retrieving the public endorsement key of the EC2 instance's Nitro Trusted Platform Module (NitroTPM).
* api-change:``dynamodb``: This release adds support to specify an optional, maximum OnDemandThroughput for DynamoDB tables and global secondary indexes in the CreateTable or UpdateTable APIs. You can also override the OnDemandThroughput settings by calling the ImportTable, RestoreFromPointInTime, or RestoreFromBackup APIs.
* api-change:``personalize``: This releases ability to delete users and their data, including their metadata and interactions data, from a dataset group.


2.15.43
=======

* api-change:``pinpoint-sms-voice-v2``: Amazon Pinpoint has added two new features Multimedia services (MMS) and protect configurations. Use the three new MMS APIs to send media messages to a mobile phone which includes image, audio, text, or video files. Use the ten new protect configurations APIs to block messages to specific countries.
* api-change:``trustedadvisor``: This release adds the BatchUpdateRecommendationResourceExclusion API to support batch updates of Recommendation Resource exclusion statuses and introduces a new exclusion status filter to the ListRecommendationResources and ListOrganizationRecommendationResources APIs.
* api-change:``sagemaker``: Amazon SageMaker Training now supports the use of attribute-based access control (ABAC) roles for training job execution roles. Amazon SageMaker Inference now supports G6 instance types.
* api-change:``codepipeline``: Add ability to manually and automatically roll back a pipeline stage to a previously successful execution.
* api-change:``inspector2``: Update Inspector2 to include new Agentless API parameters.
* api-change:``transcribe``: This update provides error messaging for generative call summarization in Transcribe Call Analytics
* api-change:``rds``: SupportsLimitlessDatabase field added to describe-db-engine-versions to indicate whether the DB engine version supports Aurora Limitless Database.
* api-change:``oam``: This release introduces support for Source Accounts to define which Metrics and Logs to share with the Monitoring Account
* api-change:``amplify``: Updating max results limit for listing any resources (Job, Artifacts, Branch, BackendResources, DomainAssociation) to 50 with the exception of list apps that where max results can be up to 100.
* api-change:``qbusiness``: This is a general availability (GA) release of Amazon Q Business. Q Business enables employees in an enterprise to get comprehensive answers to complex questions and take actions through a unified, intuitive web-based chat experience - using an enterprise's existing content, data, and systems.
* api-change:``quicksight``: New Q embedding supporting Generative Q&A
* api-change:``chime-sdk-voice``: Due to changes made by the Amazon Alexa service, GetSipMediaApplicationAlexaSkillConfiguration and PutSipMediaApplicationAlexaSkillConfiguration APIs are no longer available for use. For more information, refer to the Alexa Smart Properties page.
* api-change:``marketplace-entitlement``: Releasing minor endpoint updates.
* api-change:``omics``: Add support for workflow sharing and dynamic run storage
* api-change:``connectcampaigns``: This release adds support for specifying if Answering Machine should wait for prompt sound.
* api-change:``support``: Releasing minor endpoint updates.
* api-change:``signer``: Documentation updates for AWS Signer. Adds cross-account signing constraint and definitions for cross-account actions.
* api-change:``opensearch``: This release enables customers to create Route53 A and AAAA alias record types to point custom endpoint domain to OpenSearch domain's dualstack search endpoint.
* api-change:``route53resolver``: Release of FirewallDomainRedirectionAction parameter on the Route 53 DNS Firewall Rule.  This allows customers to configure a DNS Firewall rule to inspect all the domains in the DNS redirection chain (default) , such as CNAME, ALIAS, DNAME, etc., or just the first domain and trust the rest.
* api-change:``timestream-query``: This change allows users to update and describe account settings associated with their accounts.
* api-change:``connectcases``: This feature releases DeleteField, DeletedLayout, and DeleteTemplate API's
* api-change:``cognito-idp``: Add LimitExceededException to SignUp errors
* api-change:``fms``: AWS Firewall Manager now supports the network firewall service stream exception policy feature for accounts within your organization.
* api-change:``codeartifact``: Add support for the Ruby package format.


2.15.42
=======

* api-change:``ivs``: Bug Fix: IVS does not support arns with the `svs` prefix
* api-change:``fms``: AWS Firewall Manager adds support for network ACL policies to manage Amazon Virtual Private Cloud (VPC) network access control lists (ACLs) for accounts in your organization.
* api-change:``stepfunctions``: Add new ValidateStateMachineDefinition operation, which performs syntax checking on the definition of a Amazon States Language (ASL) state machine.
* api-change:``gamelift``: Amazon GameLift releases container fleets support for public preview. Deploy Linux-based containerized game server software for hosting on Amazon GameLift.
* api-change:``ec2``: Launching capability for customers to enable or disable automatic assignment of public IPv4 addresses to their network interface
* api-change:``ssm``: Add SSM DescribeInstanceProperties API to public AWS SDK.
* api-change:``entityresolution``: Support Batch Unique IDs Deletion.
* api-change:``emr-containers``: EMRonEKS Service support for SecurityConfiguration enforcement for Spark Jobs.
* api-change:``datasync``: This change allows users to disable and enable the schedules associated with their tasks.
* api-change:``appsync``: UpdateGraphQLAPI documentation update and datasource introspection secret arn update
* api-change:``ivs-realtime``: Bug Fix: IVS Real Time does not support ARNs using the `svs` prefix.
* api-change:``rds``: Updates Amazon RDS documentation for setting local time zones for RDS for Db2 DB instances.


2.15.41
=======

* api-change:``redshift-serverless``: Updates description of schedule field for scheduled actions.
* api-change:``pi``: Clarifies how aggregation works for GetResourceMetrics in the Performance Insights API.
* api-change:``glue``: Adding RowFilter in the response for GetUnfilteredTableMetadata API
* api-change:``personalize``: This releases auto training capability while creating a solution and automatically syncing latest solution versions when creating/updating a campaign
* api-change:``payment-cryptography``: Adding support to TR-31/TR-34 exports for optional headers, allowing customers to add additional metadata (such as key version and KSN) when exporting keys from the service.
* api-change:``transfer``: Adding new API to support remote directory listing using SFTP connector
* api-change:``bedrock-agent``: Releasing the support for simplified configuration and return of control
* api-change:``rds``: Fix the example ARN for ModifyActivityStreamRequest
* api-change:``ec2``: This release introduces EC2 AMI Deregistration Protection, a new AMI property that can be enabled by customers to protect an AMI against an unintended deregistration. This release also enables the AMI owners to view the AMI 'LastLaunchedTime' in DescribeImages API.
* api-change:``bedrock-agent-runtime``: Releasing the support for simplified configuration and return of control
* api-change:``workspaces-web``: Added InstanceType and MaxConcurrentSessions parameters on CreatePortal and UpdatePortal Operations as well as the ability to read Customer Managed Key & Additional Encryption Context parameters on supported resources (Portal, BrowserSettings, UserSettings, IPAccessSettings)
* api-change:``bedrock``: This release introduces Model Evaluation and Guardrails for Amazon Bedrock.
* api-change:``ce``: Added additional metadata that might be applicable to your reservation recommendations.
* api-change:``route53profiles``: Route 53 Profiles allows you to apply a central DNS configuration across many VPCs regardless of account.
* api-change:``bedrock-agent-runtime``: This release introduces zero-setup file upload support for the RetrieveAndGenerate API. This allows you to chat with your data without setting up a Knowledge Base.
* api-change:``sagemaker``: This release adds support for Real-Time Collaboration and Shared Space for JupyterLab App on SageMaker Studio.
* api-change:``internetmonitor``: This update introduces the GetInternetEvent and ListInternetEvents APIs, which provide access to internet events displayed on the Amazon CloudWatch Internet Weather Map.
* api-change:``bedrock-runtime``: This release introduces Guardrails for Amazon Bedrock.
* api-change:``bedrock-agent``: Introducing the ability to create multiple data sources per knowledge base, specify S3 buckets as data sources from external accounts, and exposing levers to define the deletion behavior of the underlying vector store data.
* api-change:``servicediscovery``: This release adds examples to several Cloud Map actions.


2.15.40
=======

* api-change:``workspaces``: Adds new APIs for managing and sharing WorkSpaces BYOL configuration across accounts.
* api-change:``rolesanywhere``: This release introduces the PutAttributeMapping and DeleteAttributeMapping APIs. IAM Roles Anywhere now provides the capability to define a set of mapping rules, allowing customers to specify which data is extracted from their X.509 end-entity certificates.
* api-change:``guardduty``: Added IPv6Address fields for local and remote IP addresses
* api-change:``emr-serverless``: This release adds the capability to publish detailed Spark engine metrics to Amazon Managed Service for Prometheus (AMP) for  enhanced monitoring for Spark jobs.
* api-change:``qbusiness``: This release adds support for IAM Identity Center (IDC) as the identity gateway for Q Business. It also allows users to provide an explicit intent for Q Business to identify how the Chat request should be handled.
* api-change:``drs``: Outpost ARN added to Source Server and Recovery Instance
* api-change:``ec2``: Documentation updates for Elastic Compute Cloud (EC2).
* api-change:``sagemaker``: Removed deprecated enum values and updated API documentation.
* api-change:``quicksight``: This release adds support for the Cross Sheet Filter and Control features, and support for warnings in asset imports for any permitted errors encountered during execution


2.15.39
=======

* api-change:``transfer``: This change releases support for importing self signed certificates to the Transfer Family for sending outbound file transfers over TLS/HTTPS.
* api-change:``kms``: This feature supports the ability to specify a custom rotation period for automatic key rotations, the ability to perform on-demand key rotations, and visibility into your key material rotations.
* api-change:``outposts``: This release adds new APIs to allow customers to configure their Outpost capacity at order-time.
* api-change:``healthlake``: Added new CREATE_FAILED status for data stores. Added new errorCause to DescribeFHIRDatastore API and ListFHIRDatastores API response for additional insights into data store creation and deletion workflows.
* api-change:``config``: Updates documentation for AWS Config
* api-change:``cloudformation``: Adding support for the new parameter "IncludePropertyValues" in the CloudFormation DescribeChangeSet API. When this parameter is included, the DescribeChangeSet response will include more detailed information such as before and after values for the resource properties that will change.
* api-change:``entityresolution``: Cross Account Resource Support .
* api-change:``mediatailor``: Added InsertionMode to PlaybackConfigurations. This setting controls whether players can use stitched or guided ad insertion. The default for players that do not specify an insertion mode is stitched.
* api-change:``emr-serverless``: This release adds support for shuffle optimized disks that allow larger disk sizes and higher IOPS to efficiently run shuffle heavy workloads.
* api-change:``glue``: Modifying request for GetUnfilteredTableMetadata for view-related fields.
* api-change:``m2``: Adding new ListBatchJobRestartPoints API and support for restart batch job.
* api-change:``wellarchitected``: AWS Well-Architected now has a Connector for Jira to allow customers to efficiently track workload risks and improvement efforts and create closed-loop mechanisms.
* api-change:``redshift``: Adds support for Amazon Redshift DescribeClusterSnapshots API to include Snapshot ARN response field.
* api-change:``outposts``: This release adds EXPEDITORS as a valid shipment carrier.
* api-change:``neptune-graph``: Update to API documentation to resolve customer reported issues.
* api-change:``bedrock-agent``: For Create Agent API, the agentResourceRoleArn parameter is no longer required.
* api-change:``iotfleethub``: Documentation updates for AWS IoT Fleet Hub to clarify that Fleet Hub supports organization instance of IAM Identity Center.
* api-change:``iotwireless``: Add PublicGateways in the GetWirelessStatistics call response, indicating the LoRaWAN public network accessed by the device.
* api-change:``lakeformation``: This release adds Lake Formation managed RAM support for the 4 APIs - "DescribeLakeFormationIdentityCenterConfiguration", "CreateLakeFormationIdentityCenterConfiguration", "DescribeLakeFormationIdentityCenterConfiguration", and "DeleteLakeFormationIdentityCenterConfiguration"
* api-change:``mediapackagev2``: Dash v2 is a MediaPackage V2 feature to support egressing on DASH manifest format.


2.15.38
=======

* api-change:``networkmonitor``: Examples were added to CloudWatch Network Monitor commands.
* api-change:``omics``: This release adds support for retrieval of S3 direct access metadata on sequence stores and read sets, and adds support for SHA256up and SHA512up HealthOmics ETags.
* api-change:``medialive``: AWS Elemental MediaLive introduces workflow monitor, a new feature that enables the visualization and monitoring of your media workflows. Create signal maps of your existing workflows and monitor them by creating notification and monitoring template groups.
* api-change:``supplychain``: This release includes API SendDataIntegrationEvent for AWS Supply Chain
* api-change:``connect``: This release adds new Submit Auto Evaluation Action for Amazon Connect Rules.
* api-change:``codebuild``: Support access tokens for Bitbucket sources
* api-change:``cleanrooms``: AWS Clean Rooms Differential Privacy is now fully available. Differential privacy protects against user-identification attempts.
* api-change:``s3control``: Documentation updates for Amazon S3-control.
* api-change:``rekognition``: Added support for ContentType to content moderation detections.
* api-change:``qconnect``: This release adds a new QiC public API updateSession and updates an existing QiC public API createSession
* api-change:``rds``: Updates Amazon RDS documentation for Standard Edition 2 support in RDS Custom for Oracle.
* api-change:``pipes``: LogConfiguration ARN validation fixes
* api-change:``workspaces-thin-client``: Adding tags field to SoftwareSet. Removing tags fields from Summary objects. Changing the list of exceptions in tagging APIs. Fixing an issue where the SDK returns empty tags in Get APIs.
* api-change:``cloudfront``: CloudFront origin access control extends support to AWS Lambda function URLs and AWS Elemental MediaPackage v2 origins.
* api-change:``iam``: For CreateOpenIDConnectProvider API, the ThumbprintList parameter is no longer required.
* api-change:``cloudwatch``: This release adds support for Metric Characteristics for CloudWatch Anomaly Detection. Anomaly Detector now takes Metric Characteristics object with Periodic Spikes boolean field that tells Anomaly Detection that spikes that repeat at the same time every week are part of the expected pattern.
* api-change:``batch``: This release adds the task properties field to attempt details and the name field on EKS container detail.


2.15.37
=======

* api-change:``mgn``: Added USE_SOURCE as default option to LaunchConfigurationTemplate bootMode parameter.
* api-change:``pinpoint``: The OrchestrationSendingRoleArn has been added to the email channel and is used to send emails from campaigns or journeys.
* api-change:``controlcatalog``: This is the initial SDK release for AWS Control Catalog, a central catalog for AWS managed controls. This release includes 3 new APIs - ListDomains, ListObjectives, and ListCommonControls - that vend high-level data to categorize controls across the AWS platform.
* api-change:``rds``: This release adds support for specifying the CA certificate to use for the new db instance when restoring from db snapshot, restoring from s3, restoring to point in time, and creating a db instance read replica.
* api-change:``resource-groups``: Added a new QueryErrorCode RESOURCE_TYPE_NOT_SUPPORTED that is returned by the ListGroupResources operation if the group query contains unsupported resource types.
* api-change:``quicksight``: Adding IAMIdentityCenterInstanceArn parameter to CreateAccountSubscription
* api-change:``verifiedpermissions``: Adding BatchIsAuthorizedWithToken API which supports multiple authorization requests against a PolicyStore given a bearer token.
* api-change:``mediaconvert``: This release includes support for bringing your own fonts to use for burn-in or DVB-Sub captioning workflows.
* api-change:``networkmonitor``: Updated the allowed monitorName length for CloudWatch Network Monitor.
* api-change:``codebuild``: Add new webhook filter types for GitHub webhooks


2.15.36
=======

* api-change:``emr-containers``: This release adds support for integration with EKS AccessEntry APIs to enable automatic Cluster Access for EMR on EKS.
* api-change:``verifiedpermissions``: Adds GroupConfiguration field to Identity Source API's
* api-change:``cleanroomsml``: The release includes a public SDK for AWS Clean Rooms ML APIs, making them globally available to developers worldwide.
* api-change:``datazone``: This release supports the feature of dataQuality to enrich asset with dataQualityResult in Amazon DataZone.
* api-change:``groundstation``: This release adds visibilityStartTime and visibilityEndTime to DescribeContact and ListContacts responses.
* api-change:``cleanrooms``: Feature: New schemaStatusDetails field to the existing Schema object that displays a status on Schema API responses to show whether a schema is queryable or not. New BatchGetSchemaAnalysisRule API to retrieve multiple schemaAnalysisRules using a single API call.
* api-change:``b2bi``: Adding support for X12 5010 HIPAA EDI version and associated transaction sets.
* api-change:``transfer``: Add ability to specify Security Policies for SFTP Connectors
* api-change:``ivs``: API update to include an SRT ingest endpoint and passphrase for all channels.
* api-change:``docdb``: This release adds Global Cluster Switchover capability which enables you to change your global cluster's primary AWS Region, the region that serves writes, while preserving the replication between all regions in the global cluster.
* api-change:``cloudformation``: This release would return a new field - PolicyAction in cloudformation's existed DescribeChangeSetResponse, showing actions we are going to apply on the physical resource (e.g., Delete, Retain) according to the user's template
* api-change:``ec2``: Amazon EC2 G6 instances powered by NVIDIA L4 Tensor Core GPUs can be used for a wide range of graphics-intensive and machine learning use cases. Gr6 instances also feature NVIDIA L4 GPUs and can be used for graphics workloads with higher memory requirements.
* api-change:``medialive``: Cmaf Ingest outputs are now supported in Media Live
* api-change:``lambda``: Add Ruby 3.3 (ruby3.3) support to AWS Lambda
* api-change:``medical-imaging``: SearchImageSets API now supports following enhancements - Additional support for searching on UpdatedAt and SeriesInstanceUID - Support for searching existing filters between dates/times - Support for sorting the search result by Ascending/Descending - Additional parameters returned in the response


2.15.35
=======

* api-change:``rolesanywhere``: This release increases the limit on the roleArns request parameter for the *Profile APIs that support it. This parameter can now take up to 250 role ARNs.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``cloudwatch``: This release adds support for CloudWatch Anomaly Detection on cross-account metrics. SingleMetricAnomalyDetector and MetricDataQuery inputs to Anomaly Detection APIs now take an optional AccountId field.
* api-change:``deadline``: AWS Deadline Cloud is a new fully managed service that helps customers set up, deploy, and scale rendering projects in minutes, so they can improve the efficiency of their rendering pipelines and take on more projects.
* api-change:``emr``: This release fixes a broken link in the documentation.
* api-change:``ecs``: Documentation only update for Amazon ECS.
* api-change:``datazone``: This release supports the feature of AI recommendations for descriptions to enrich the business data catalog in Amazon DataZone.
* api-change:``glue``: Adding View related fields to responses of read-only Table APIs.
* api-change:``lightsail``: This release adds support to upgrade the TLS version of the distribution.
* api-change:``ivschat``: Doc-only update. Changed "Resources" to "Key Concepts" in docs and updated text.


2.15.34
=======

* api-change:``codebuild``: Add new fleet status code for Reserved Capacity.
* api-change:``codeconnections``: Duplicating the CodeStar Connections service into the new, rebranded AWS CodeConnections service.
* api-change:``oam``: This release adds support for sharing AWS::InternetMonitor::Monitor resources.
* api-change:``internetmonitor``: This release adds support to allow customers to track cross account monitors through ListMonitor, GetMonitor, ListHealthEvents, GetHealthEvent, StartQuery APIs.
* api-change:``elasticache``: Added minimum capacity to  Amazon ElastiCache Serverless. This feature allows customer to ensure minimum capacity even without current load
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate recommendations with a new customization preference, Memory Utilization.
* api-change:``batch``: This feature allows AWS Batch to support configuration of imagePullSecrets and allowPrivilegeEscalation for jobs running on EKS
* api-change:``eks``: Add multiple customer error code to handle customer caused failure when managing EKS node groups
* api-change:``b2bi``: Supporting new EDI X12 transaction sets for X12 versions 4010, 4030, and 5010.
* api-change:``iotwireless``: Add support for retrieving key historical and live metrics for LoRaWAN devices and gateways
* api-change:``codecatalyst``: This release adds support for understanding pending changes to subscriptions by including two new response parameters for the GetSubscription API for Amazon CodeCatalyst.
* api-change:``guardduty``: Add EC2 support for GuardDuty Runtime Monitoring auto management.
* api-change:``sagemaker``: This release adds support for custom images for the CodeEditor App on SageMaker Studio
* api-change:``bedrock-agent-runtime``: This release introduces filtering support on Retrieve and RetrieveAndGenerate APIs.
* api-change:``bedrock-agent``: This changes introduces metadata documents statistics and also updates the documentation for bedrock agent.
* enhancement:``s3``: Add parameter to validate source and destination S3 URIs to the ``mv`` command.
* api-change:``neptune-graph``: Add the new API Start-Import-Task for Amazon Neptune Analytics.
* api-change:``quicksight``: Amazon QuickSight: Adds support for setting up VPC Endpoint restrictions for accessing QuickSight Website.
* api-change:``ec2``: Amazon EC2 C7gd, M7gd and R7gd metal instances with up to 3.8 TB of local NVMe-based SSD block-level storage have up to 45% improved real-time NVMe storage performance than comparable Graviton2-based instances.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``marketplace-catalog``: This release enhances the ListEntities API to support ResaleAuthorizationId filter and sort for OfferEntity in the request and the addition of a ResaleAuthorizationId field in the response of OfferSummary.
* api-change:``neptune-graph``: Update ImportTaskCancelled waiter to evaluate task state correctly and minor documentation changes.


2.15.33
=======

* api-change:``ecs``: Documentation only update for Amazon ECS.
* api-change:``kendra``: Documentation update, March 2024. Corrects some docs for Amazon Kendra.
* api-change:``ec2``: Added support for ModifyInstanceMetadataDefaults and GetInstanceMetadataDefaults to set Instance Metadata Service account defaults
* api-change:``finspace``: Add new operation delete-kx-cluster-node and add status parameter to list-kx-cluster-node operation.
* api-change:``sagemaker``: Introduced support for the following new instance types on SageMaker Studio for JupyterLab and CodeEditor applications: m6i, m6id, m7i, c6i, c6id, c7i, r6i, r6id, r7i, and p5
* api-change:``ec2``: Documentation updates for Elastic Compute Cloud (EC2).
* api-change:``ecs``: This is a documentation update for Amazon ECS.
* api-change:``firehose``: Updates Amazon Firehose documentation for message regarding Enforcing Tags IAM Policy.
* api-change:``ce``: Adds support for backfill of cost allocation tags, with new StartCostAllocationTagBackfill and ListCostAllocationTagBackfillHistory API.
* api-change:``medialive``: Exposing TileMedia H265 options
* api-change:``rolesanywhere``: This release relaxes constraints on the durationSeconds request parameter for the *Profile APIs that support it. This parameter can now take on values that go up to 43200.
* api-change:``bedrock-agent-runtime``: This release adds support to customize prompts sent through the RetrieveAndGenerate API in Agents for Amazon Bedrock.
* api-change:``pricing``: Add ResourceNotFoundException to ListPriceLists and GetPriceListFileUrl APIs
* api-change:``codebuild``: Supporting GitLab and GitLab Self Managed as source types in AWS CodeBuild.
* api-change:``globalaccelerator``: AWS Global Accelerator now supports cross-account sharing for bring your own IP addresses.
* api-change:``securityhub``: Added new resource detail object to ASFF, including resource for LastKnownExploitAt
* api-change:``emr-containers``: This release increases the number of supported job template parameters from 20 to 100.


2.15.32
=======

* api-change:``connect``: This release updates the *InstanceStorageConfig APIs to support a new ResourceType: REAL_TIME_CONTACT_ANALYSIS_CHAT_SEGMENTS. Use this resource type to enable streaming for real-time analysis of chat contacts and to associate a Kinesis stream where real-time analysis chat segments will be published.
* api-change:``codebuild``: This release adds support for new webhook events (RELEASED and PRERELEASED) and filter types (TAG_NAME and RELEASE_NAME).
* api-change:``accessanalyzer``: This release adds support for policy validation and external access findings for DynamoDB tables and streams. IAM Access Analyzer helps you author functional and secure resource-based policies and identify cross-account access. Updated service API, documentation, and paginators.
* api-change:``dynamodb``: This release introduces 3 new APIs ('GetResourcePolicy', 'PutResourcePolicy' and 'DeleteResourcePolicy') and modifies the existing 'CreateTable' API for the resource-based policy support. It also modifies several APIs to accept a 'TableArn' for the 'TableName' parameter.
* api-change:``managedblockchain-query``: AMB Query: update GetTransaction to include transactionId as input
* api-change:``codeartifact``: This release adds Package groups to CodeArtifact so you can more conveniently configure package origin controls for multiple packages.
* api-change:``savingsplans``: Introducing the Savings Plans Return feature enabling customers to return their Savings Plans within 7 days of purchase.


2.15.31
=======

* api-change:``cloudformation``: This release supports for a new API ListStackSetAutoDeploymentTargets, which provider auto-deployment configuration as a describable resource. Customers can now view the specific combinations of regions and OUs that are being auto-deployed.
* api-change:``kms``: Adds the ability to use the default policy name by omitting the policyName parameter in calls to PutKeyPolicy and GetKeyPolicy
* api-change:``timestream-query``: Documentation updates, March 2024
* api-change:``rds``: This release launches the ModifyIntegration API and support for data filtering for zero-ETL Integrations.
* api-change:``sagemaker``: Adds m6i, m6id, m7i, c6i, c6id, c7i, r6i r6id, r7i, p5 instance type support to Sagemaker Notebook Instances and miscellaneous wording fixes for previous Sagemaker documentation.
* api-change:``s3``: Documentation updates for Amazon S3.
* api-change:``managedblockchain-query``: Introduces a new API for Amazon Managed Blockchain Query: ListFilteredTransactionEvents.
* api-change:``ec2``: Add media accelerator and neuron device information on the describe instance types API.
* api-change:``codebuild``: AWS CodeBuild now supports overflow behavior on Reserved Capacity.
* api-change:``connect``: This release adds Hierarchy based Access Control fields to Security Profile public APIs and adds support for UserAttributeFilter to SearchUsers API.
* api-change:``mediatailor``: This release adds support to allow customers to show different content within a channel depending on metadata associated with the viewer.
* api-change:``finspace``: Adding new attributes readWrite and onDemand to dataview models for Database Maintenance operations.
* api-change:``workspaces-thin-client``: Removed unused parameter kmsKeyArn from UpdateDeviceRequest
* api-change:``backup``: This release introduces a boolean attribute ManagedByAWSBackupOnly as part of ListRecoveryPointsByResource api to filter the recovery points based on ownership. This attribute can be used to filter out the recovery points protected by AWSBackup.
* api-change:``cloudformation``: Documentation update, March 2024. Corrects some formatting.
* api-change:``s3``: Fix two issues with response root node names.
* api-change:``kinesisanalyticsv2``: Support for Flink 1.18 in Managed Service for Apache Flink
* api-change:``ec2``: This release adds the new DescribeMacHosts API operation for getting information about EC2 Mac Dedicated Hosts. Users can now see the latest macOS versions that their underlying Apple Mac can support without needing to be updated.
* api-change:``logs``: Update LogSamples field in Anomaly model to be a list of LogEvent


2.15.30
=======

* api-change:``elbv2``: This release allows you to configure HTTP client keep-alive duration for communication between clients and Application Load Balancers.
* api-change:``s3``: This release makes the default option for S3 on Outposts request signing to use the SigV4A algorithm when using AWS Common Runtime (CRT).
* api-change:``amplify``: Documentation updates for Amplify. Identifies the APIs available only to apps created using Amplify Gen 1.
* api-change:``ivs-realtime``: adds support for multiple new composition layout configuration options (grid, pip)
* api-change:``timestream-influxdb``: This is the initial SDK release for Amazon Timestream for InfluxDB. Amazon Timestream for InfluxDB is a new time-series database engine that makes it easy for application developers and DevOps teams to run InfluxDB databases on AWS for near real-time time-series applications using open source APIs.
* api-change:iot-roborunner: The iot-roborunner client has been removed following the deprecation of the service.
* api-change:``secretsmanager``: Doc only update for Secrets Manager
* api-change:``rds``: Updates Amazon RDS documentation for EBCDIC collation for RDS for Db2.
* api-change:``fis``: This release adds support for previewing target resources before running a FIS experiment. It also adds resource ARNs for actions, experiments, and experiment templates to API responses.
* api-change:``kinesisanalyticsv2``: Support new RuntimeEnvironmentUpdate parameter within UpdateApplication API allowing callers to change the Flink version upon which their application runs.
* api-change:``ec2-instance-connect``: This release includes a new exception type "SerialConsoleSessionUnsupportedException" for SendSerialConsoleSSHPublicKey API.


2.15.29
=======

* api-change:``connect``: This release increases MaxResults limit to 500 in request for SearchUsers, SearchQueues and SearchRoutingProfiles APIs of Amazon Connect.
* api-change:``cloudformation``: CloudFormation documentation update for March, 2024
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``ssm``: March 2024 doc-only updates for Systems Manager.
* api-change:``kafka``: Added support for specifying the starting position of topic replication in MSK-Replicator.


2.15.28
=======

* api-change:``codebuild``: This release adds support for a new webhook event: PULL_REQUEST_CLOSED.
* api-change:``codestar-connections``: Added a sync configuration enum to disable publishing of deployment status to source providers (PublishDeploymentStatus). Added a sync configuration enum (TriggerStackUpdateOn) to only trigger changes.
* api-change:``mediapackagev2``: This release enables customers to safely update their MediaPackage v2 channel groups, channels and origin endpoints using entity tags.
* api-change:``elasticache``: Revisions to API text that are now to be carried over to SDK text, changing usages of "SFO" in code examples to "us-west-1", and some other typos.
* api-change:``cloudtrail``: Added exceptions to CreateTrail, DescribeTrails, and ListImportFailures APIs.
* api-change:``guardduty``: Add RDS Provisioned and Serverless Usage types
* api-change:``batch``: This release adds JobStateTimeLimitActions setting to the Job Queue API. It allows you to configure an action Batch can take for a blocking job in front of the queue after the defined period of time. The new parameter applies for ECS, EKS, and FARGATE Job Queues.
* api-change:``transfer``: Added DES_EDE3_CBC to the list of supported encryption algorithms for messages sent with an AS2 connector.
* api-change:``cognito-idp``: Add ConcurrentModificationException to SetUserPoolMfaConfig
* api-change:``bedrock-agent-runtime``: Documentation update for Bedrock Runtime Agent


2.15.27
=======

* api-change:``mwaa``: Amazon MWAA adds support for Apache Airflow v2.8.1.
* api-change:``lambda``: Documentation updates for AWS Lambda
* api-change:``grafana``: Adds support for the new GrafanaToken as part of the Amazon Managed Grafana Enterprise plugins upgrade to associate your AWS account with a Grafana Labs account.
* api-change:``verifiedpermissions``: Deprecating details in favor of configuration for GetIdentitySource and ListIdentitySources APIs.
* api-change:``rds``: Updates Amazon RDS documentation for io2 storage for Multi-AZ DB clusters
* api-change:``rds``: Updated the input of CreateDBCluster and ModifyDBCluster to support setting CA certificates. Updated the output of DescribeDBCluster to show current CA certificate setting value.
* api-change:``payment-cryptography-data``: AWS Payment Cryptography EMV Decrypt Feature  Release
* api-change:``dynamodb``: Doc only updates for DynamoDB documentation
* api-change:``imagebuilder``: Add PENDING status to Lifecycle Execution resource status. Add StartTime and EndTime to ListLifecycleExecutionResource API response.
* api-change:``appconfig``: AWS AppConfig now supports dynamic parameters, which enhance the functionality of AppConfig Extensions by allowing you to provide parameter values to your Extensions at the time you deploy your configuration.
* api-change:``redshift``: Update for documentation only. Covers port ranges, definition updates for data sharing, and definition updates to cluster-snapshot documentation.
* api-change:``ec2``: This release adds an optional parameter to RegisterImage and CopyImage APIs to support tagging AMIs at the time of creation.
* api-change:``snowball``: Doc-only update for change to EKS-Anywhere ordering.
* api-change:``wafv2``: You can increase the max request body inspection size for some regional resources. The size setting is in the web ACL association config. Also, the AWSManagedRulesBotControlRuleSet EnableMachineLearning setting now takes a Boolean instead of a primitive boolean type, for languages like Java.
* api-change:``workspaces``: Added note for user decoupling


2.15.26
=======

* api-change:``fsx``: Added support for creating FSx for NetApp ONTAP file systems with up to 12 HA pairs, delivering up to 72 GB/s of read throughput and 12 GB/s of write throughput.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``organizations``: Documentation update for AWS Organizations
* api-change:``sesv2``: Adds support for providing custom headers within SendEmail and SendBulkEmail for SESv2.
* api-change:``cloudformation``: Add DetailedStatus field to DescribeStackEvents and DescribeStacks APIs
* api-change:``organizations``: This release contains an endpoint addition
* api-change:``chatbot``: Minor update to documentation.


2.15.25
=======

* api-change:``eks``: Added support for new AL2023 AMIs to the supported AMITypes.
* api-change:``ec2``: This release increases the range of MaxResults for GetNetworkInsightsAccessScopeAnalysisFindings to 1,000.
* api-change:``autoscaling``: With this release, Amazon EC2 Auto Scaling groups, EC2 Fleet, and Spot Fleet improve the default price protection behavior of attribute-based instance type selection of Spot Instances, to consistently select from a wide range of instance types.
* api-change:``batch``: This release adds Batch support for configuration of multicontainer jobs in ECS, Fargate, and EKS. This support is available for all types of jobs, including both array jobs and multi-node parallel jobs.
* api-change:``lexv2-models``: This release makes AMAZON.QnAIntent generally available in Amazon Lex. This generative AI feature leverages large language models available through Amazon Bedrock to automate frequently asked questions (FAQ) experience for end-users.
* enhancement:openssl: Update bundled openssl version to 1.1.1w
* api-change:``migrationhuborchestrator``: Adds new CreateTemplate, UpdateTemplate and DeleteTemplate APIs.
* api-change:``ce``: This release introduces the new API 'GetApproximateUsageRecords', which retrieves estimated usage records for hourly granularity or resource-level data at daily granularity.
* api-change:``docdb-elastic``: Launched Elastic Clusters Readable Secondaries, Start/Stop, Configurable Shard Instance count, Automatic Backups and Snapshot Copying
* api-change:``ec2``: With this release, Amazon EC2 Auto Scaling groups, EC2 Fleet, and Spot Fleet improve the default price protection behavior of attribute-based instance type selection of Spot Instances, to consistently select from a wide range of instance types.
* api-change:``wafv2``: AWS WAF now supports configurable time windows for request aggregation with rate-based rules. Customers can now select time windows of 1 minute, 2 minutes or 10 minutes, in addition to the previously supported 5 minutes.
* enhancement:Python: Update bundled Python interpreter to 3.11.8
* api-change:``bedrock-agent-runtime``: This release adds support to override search strategy performed by the Retrieve and RetrieveAndGenerate APIs for Amazon Bedrock Agents
* api-change:``quicksight``: TooltipTarget for Combo chart visuals; ColumnConfiguration limit increase to 2000; Documentation Update
* api-change:``iot``: This release reduces the maximum results returned per query invocation from 500 to 100 for the SearchIndex API. This change has no implications as long as the API is invoked until the nextToken is NULL.
* api-change:``accessanalyzer``: Fixed a typo in description field.
* api-change:``securitylake``: Add capability to update the Data Lake's MetaStoreManager Role in order to perform required data lake updates to use Iceberg table format in their data lake or update the role for any other reason.
* api-change:``sagemaker``: Adds support for ModelDataSource in Model Packages to support unzipped models. Adds support to specify SourceUri for models which allows registration of models without mandating a container for hosting. Using SourceUri, customers can decouple the model from hosting information during registration.


2.15.24
=======

* api-change:``rds``: This release adds support for gp3 data volumes for Multi-AZ DB Clusters.
* api-change:``drs``: Added volume status to DescribeSourceServer replicated volumes.
* api-change:``rds``: Add pattern and length based validations for DBShardGroupIdentifier
* api-change:``kafkaconnect``: Adds support for tagging, with new TagResource, UntagResource and ListTagsForResource APIs to manage tags and updates to existing APIs to allow tag on create. This release also adds support for the new DeleteWorkerConfiguration API.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway.
* api-change:``amplifyuibuilder``: We have added the ability to tag resources after they are created
* api-change:``qldb``: Clarify possible values for KmsKeyArn and EncryptionDescription.
* api-change:``appsync``: Documentation only updates for AppSync
* api-change:``rum``: Doc-only update for new RUM metrics that were added


2.15.23
=======

* api-change:``lookoutequipment``: This release adds a field exposing model quality to read APIs for models. It also adds a model quality field to the API response when creating an inference scheduler.
* api-change:``internetmonitor``: This release adds IPv4 prefixes to health events
* api-change:``medialive``: MediaLive now supports the ability to restart pipelines in a running channel.
* api-change:``iotevents``: Increase the maximum length of descriptions for Inputs, Detector Models, and Alarm Models
* api-change:``ssm``: This release adds support for sharing Systems Manager parameters with other AWS accounts.
* api-change:``kinesisvideo``: Increasing NextToken parameter length restriction for List APIs from 512 to 1024.


2.15.22
=======

* api-change:``keyspaces``: Documentation updates for Amazon Keyspaces
* api-change:``firehose``: This release adds support for Data Message Extraction for decompressed CloudWatch logs, and to use a custom file extension or time zone for S3 destinations.
* api-change:``dynamodb``: Publishing quick fix for doc only update.
* api-change:``ivs``: Changed description for latencyMode in Create/UpdateChannel and Channel/ChannelSummary.
* api-change:``firehose``: This release updates a few Firehose related APIs.
* api-change:``chatbot``: This release adds support for AWS Chatbot. You can now monitor, operate, and troubleshoot your AWS resources with interactive ChatOps using the AWS SDK.
* api-change:``sns``: This release marks phone numbers as sensitive inputs.
* api-change:``lambda``: Add .NET 8 (dotnet8) Runtime support to AWS Lambda.
* api-change:``amplify``: This release contains API changes that enable users to configure their Amplify domains with their own custom SSL/TLS certificate.
* api-change:``lambda``: Documentation-only updates for Lambda to clarify a number of existing actions and properties.
* api-change:``emr``: adds fine grained control over Unhealthy Node Replacement to Amazon ElasticMapReduce
* api-change:``config``: Documentation updates for the AWS Config CLI
* api-change:``rds``: Doc only update for a valid option in DB parameter group
* api-change:``connectparticipant``: Doc only update to GetTranscript API reference guide to inform users about presence of events in the chat transcript.
* api-change:``mediatailor``: MediaTailor: marking #AdBreak.OffsetMillis as required.


2.15.21
=======

* api-change:``secretsmanager``: Doc only update for Secrets Manager
* api-change:``opensearch``: Adds additional supported instance types.
* api-change:``codepipeline``: Add ability to override timeout on action level.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``lookoutequipment``: This feature allows customers to see pointwise model diagnostics results for their models.
* api-change:``artifact``: This is the initial SDK release for AWS Artifact. AWS Artifact provides on-demand access to compliance and third-party compliance reports. This release includes access to List and Get reports, along with their metadata. This release also includes access to AWS Artifact notifications settings.
* api-change:``detective``: Doc only updates for content enhancement
* api-change:``healthlake``: This release adds a new response parameter, JobProgressReport, to the DescribeFHIRImportJob and ListFHIRImportJobs API operation. JobProgressReport provides details on the progress of the import job on the server.
* api-change:``polly``: Amazon Polly adds 1 new voice - Burcu (tr-TR)
* api-change:``sagemaker``: This release adds a new API UpdateClusterSoftware for SageMaker HyperPod. This API allows users to patch HyperPod clusters with latest platform softwares.
* api-change:``qbusiness``: This release adds the metadata-boosting feature, which allows customers to easily fine-tune the underlying ranking of retrieved RAG passages in order to optimize Q&A answer relevance. It also adds new feedback reasons for the PutFeedback API.
* api-change:``guardduty``: Marked fields IpAddressV4, PrivateIpAddress, Email as Sensitive.
* api-change:``controltower``: Adds support for new Baseline and EnabledBaseline APIs for automating multi-account governance.


2.15.20
=======

* api-change:``appsync``: Adds support for new options on GraphqlAPIs, Resolvers and  Data Sources for emitting Amazon CloudWatch metrics for enhanced monitoring of AppSync APIs.
* api-change:``neptune-graph``: Adding a new option "parameters" for data plane api ExecuteQuery to support running parameterized query via SDK.
* api-change:``pricing``: Add Throttling Exception to all APIs.
* api-change:``marketplace-catalog``: AWS Marketplace Catalog API now supports setting intent on requests
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``cost-optimization-hub``: Adding includeMemberAccounts field to the response of ListEnrollmentStatuses API.
* api-change:``braket``: Creating a job will result in DeviceOfflineException when using an offline device, and DeviceRetiredException when using a retired device.
* api-change:``securitylake``: Documentation updates for Security Lake
* api-change:``resource-explorer-2``: Resource Explorer now uses newly supported IPv4 'amazonaws.com' endpoints by default.
* api-change:``amp``: Overall documentation updates.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``route53domains``: This release adds bill contact support for RegisterDomain, TransferDomain, UpdateDomainContact and GetDomainDetail API.
* api-change:``ecs``: Documentation only update for Amazon ECS.
* api-change:``lightsail``: This release adds support to upgrade the major version of a database.
* api-change:``iot``: This release allows AWS IoT Core users to enable Online Certificate Status Protocol (OCSP) Stapling for TLS X.509 Server Certificates when creating and updating AWS IoT Domain Configurations with Custom Domain.
* api-change:``batch``: This feature allows Batch to support configuration of repository credentials for jobs running on ECS


2.15.19
=======

* api-change:``quicksight``: General Interactions for Visuals; Waterfall Chart Color Configuration; Documentation Update
* api-change:``workspaces``: This release introduces User-Decoupling feature. This feature allows Workspaces Core customers to provision workspaces without providing users. CreateWorkspaces and DescribeWorkspaces APIs will now take a new optional parameter "WorkspaceName".
* api-change:``datasync``: AWS DataSync now supports manifests for specifying files or objects to transfer.
* api-change:``codepipeline``: Add ability to execute pipelines with new parallel & queued execution modes and add support for triggers with filtering on branches and file paths.
* api-change:``redshift``: LisRecommendations API to fetch Amazon Redshift Advisor recommendations.
* api-change:``lexv2-models``: Update lexv2-models command to latest version


2.15.18
=======

* api-change:``ecs``: This release is a documentation only update to address customer issues.
* api-change:``workspaces``: Added definitions of various WorkSpace states
* api-change:``es``: This release adds clear visibility to the customers on the changes that they make on the domain.
* api-change:``dynamodb``: Any number of users can execute up to 50 concurrent restores (any type of restore) in a given account.
* api-change:``sagemaker``: Amazon SageMaker Canvas adds GenerativeAiSettings support for CanvasAppSettings.
* api-change:``appsync``: Support for environment variables in AppSync GraphQL APIs
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* enhancement:dependency: Update ``flit_core`` version range ceiling to 3.9.0
* api-change:``logs``: This release adds a new field, logGroupArn, to the response of the logs:DescribeLogGroups action.
* api-change:``wafv2``: You can now delete an API key that you've created for use with your CAPTCHA JavaScript integration API.
* api-change:``opensearch``: This release adds clear visibility to the customers on the changes that they make on the domain.
* api-change:``glue``: Introduce Catalog Encryption Role within Glue Data Catalog Settings. Introduce SASL/PLAIN as an authentication method for Glue Kafka connections


2.15.17
=======

* api-change:``ssm``: This release adds an optional Duration parameter to StateManager Associations. This allows customers to specify how long an apply-only-on-cron association execution should run. Once the specified Duration is out all the ongoing cancellable commands or automations are cancelled.
* api-change:``neptune-graph``: Adding new APIs in SDK for Amazon Neptune Analytics. These APIs include operations to execute, cancel, list queries and get the graph summary.
* api-change:``cognito-idp``: Added CreateIdentityProvider and UpdateIdentityProvider details for new SAML IdP features
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``glue``: Update page size limits for GetJobRuns and GetTriggers APIs.
* api-change:``managedblockchain-query``: This release adds support for transactions that have not reached finality. It also removes support for the status property from the response of the GetTransaction operation. You can use the confirmationStatus and executionStatus properties to determine the status of the transaction.
* api-change:``cloudformation``: CloudFormation IaC generator allows you to scan existing resources in your account and select resources to generate a template for a new or existing CloudFormation stack.
* api-change:``ivs``: This release introduces a new resource Playback Restriction Policy which can be used to geo-restrict or domain-restrict channel stream playback when associated with a channel.  New APIs to support this resource were introduced in the form of Create/Delete/Get/Update/List.
* api-change:``mediaconvert``: This release includes support for broadcast-mixed audio description tracks.


2.15.16
=======

* api-change:``mwaa``: This release adds MAINTENANCE environment status for Amazon MWAA environments.
* api-change:``rds``: Introduced support for the InsufficientDBInstanceCapacityFault error in the RDS RestoreDBClusterFromSnapshot and RestoreDBClusterToPointInTime API methods. This provides enhanced error handling, ensuring a more robust experience.
* api-change:``inspector2``: This release adds ECR container image scanning based on their lastRecordedPullTime.
* api-change:``connect``: Update list and string length limits for predefined attributes.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now provides an API to programmatically delete tuning jobs.
* api-change:``comprehend``: Comprehend PII analysis now supports Spanish input documents.
* api-change:``route53``: Update the SDKs for text changes in the APIs.
* api-change:``snowball``: Modified description of createaddress to include direction to add path when providing a JSON file.
* api-change:``ec2``: EC2 Fleet customers who use attribute based instance-type selection can now intuitively define their Spot instances price protection limit as a percentage of the lowest priced On-Demand instance type.
* api-change:``datazone``: Add new skipDeletionCheck to DeleteDomain. Add new skipDeletionCheck to DeleteProject which also automatically deletes dependent objects
* api-change:``autoscaling``: EC2 Auto Scaling customers who use attribute based instance-type selection can now intuitively define their Spot instances price protection limit as a percentage of the lowest priced On-Demand instance type.


2.15.15
=======

* api-change:``rds``: This release adds support for Aurora Limitless Database.
* api-change:``storagegateway``: Add DeprecationDate and SoftwareVersion to response of ListGateways.
* api-change:``ec2``: Introduced a new clientToken request parameter on CreateNetworkAcl and CreateRouteTable APIs. The clientToken parameter allows idempotent operations on the APIs.
* api-change:``acm-pca``: AWS Private CA now supports an option to omit the CDP extension from issued certificates, when CRL revocation is enabled.
* api-change:``lightsail``: This release adds support for IPv6-only instance plans.
* api-change:``outposts``: DeviceSerialNumber parameter is now optional in StartConnection API
* api-change:``ecs``: Documentation updates for Amazon ECS.


2.15.14
=======

* api-change:``cloudfront-keyvaluestore``: This release improves upon the DescribeKeyValueStore API by returning two additional fields, Status of the KeyValueStore and the FailureReason in case of failures during creation of KeyValueStore.
* api-change:``codebuild``: Release CodeBuild Reserved Capacity feature
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``cloud9``: Doc-only update around removing AL1 from list of available AMIs for Cloud9
* api-change:``qconnect``: Increased Quick Response name max length to 100
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``appconfigdata``: Fix FIPS Endpoints in aws-us-gov.
* api-change:``ecs``: This release adds support for Transport Layer Security (TLS) and Configurable Timeout to ECS Service Connect. TLS facilitates privacy and data security for inter-service communications, while Configurable Timeout allows customized per-request timeout and idle timeout for Service Connect services.
* api-change:``organizations``: Doc only update for quota increase change
* api-change:``athena``: Introducing new NotebookS3LocationUri parameter to Athena ImportNotebook API. Payload is no longer required and either Payload or NotebookS3LocationUri needs to be provided (not both) for a successful ImportNotebook API call. If both are provided, an InvalidRequestException will be thrown.
* api-change:``dynamodb``: This release adds support for including ApproximateCreationDateTimePrecision configurations in EnableKinesisStreamingDestination API, adds the same as an optional field in the response of DescribeKinesisStreamingDestination, and adds support for a new UpdateKinesisStreamingDestination API.
* api-change:``connectcases``: This release adds the ability to view audit history on a case and introduces a new parameter, performedBy, for CreateCase and UpdateCase API's.
* api-change:``inspector2``: This release adds support for CIS scans on EC2 instances.
* api-change:``rds``: Introduced support for the InsufficientDBInstanceCapacityFault error in the RDS CreateDBCluster API method. This provides enhanced error handling, ensuring a more robust experience when creating database clusters with insufficient instance capacity.
* api-change:``finspace``: Allow customer to set zip default through command line arguments.


2.15.13
=======

* bugfix:``s3 sync``: Disable S3 Express support for s3 sync command


2.15.12
=======

* api-change:``keyspaces``: This release adds support for Multi-Region Replication with provisioned tables, and Keyspaces auto scaling APIs
* api-change:``b2bi``: Increasing TestMapping inputFileContent file size limit to 5MB and adding file size limit 250KB for TestParsing input file. This release also includes exposing InternalServerException for Tag APIs.
* api-change:``connect``: GetMetricDataV2 now supports 3 groupings
* api-change:``cloudtrail``: This release adds a new API ListInsightsMetricData to retrieve metric data from CloudTrail Insights.
* api-change:``dynamodb``: Updating note for enabling streams for UpdateTable.
* api-change:``firehose``: Allow support for Snowflake as a Kinesis Data Firehose delivery destination.
* api-change:``sagemaker-featurestore-runtime``: Increase BatchGetRecord limits from 10 items to 100 items
* api-change:``drs``: Removed invalid and unnecessary default values.


2.15.11
=======

* api-change:``iot``: Revert release of LogTargetTypes
* api-change:``rekognition``: This release adds ContentType and TaxonomyLevel attributes to DetectModerationLabels and GetMediaAnalysisJob API responses.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``location``: Location SDK documentation update. Added missing fonts to the MapConfiguration data type. Updated note for the SubMunicipality property in the place data type.
* api-change:``supplychain``: This release includes APIs CreateBillOfMaterialsImportJob and GetBillOfMaterialsImportJob.
* api-change:``s3control``: S3 On Outposts team adds dualstack endpoints support for S3Control and S3Outposts API calls.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``sagemaker``: This release will have ValidationException thrown if certain invalid app types are provided. The release will also throw ValidationException if more than 10 account ids are provided in VpcOnlyTrustedAccounts.
* api-change:``mwaa``: This Amazon MWAA feature release includes new fields in CreateWebLoginToken response model. The new fields IamIdentity and AirflowIdentity will let you match identifications, as the Airflow identity length is currently hashed to 64 characters.
* api-change:``transfer``: AWS Transfer Family now supports static IP addresses for SFTP & AS2 connectors and for async MDNs on AS2 servers.
* api-change:``personalize-runtime``: Documentation updates for Amazon Personalize
* api-change:``personalize``: Documentation updates for Amazon Personalize.
* api-change:``connect``: Supervisor Barge for Chat is now supported through the MonitorContact API.
* api-change:``connectparticipant``: Introduce new Supervisor participant role
* api-change:``iotfleetwise``: Updated APIs: SignalNodeType query parameter has been added to ListSignalCatalogNodesRequest and ListVehiclesResponse has been extended with attributes field.
* api-change:``payment-cryptography``: Provide an additional option for key exchange using RSA wrap/unwrap in addition to tr-34/tr-31 in ImportKey and ExportKey operations. Added new key usage (type) TR31_M1_ISO_9797_1_MAC_KEY, for use with Generate/VerifyMac dataplane operations  with ISO9797 Algorithm 1 MAC calculations.
* api-change:``macie2``: This release adds support for analyzing Amazon S3 objects that are encrypted using dual-layer server-side encryption with AWS KMS keys (DSSE-KMS). It also adds support for reporting DSSE-KMS details in statistics and metadata about encryption settings for S3 buckets and objects.


2.15.10
=======

* api-change:``iot``: Add ConflictException to Update APIs of AWS IoT Software Package Catalog
* api-change:``ecs``: This release adds support for adding an ElasticBlockStorage volume configurations in ECS RunTask/StartTask/CreateService/UpdateService APIs. The configuration allows for attaching EBS volumes to ECS Tasks.
* api-change:``workspaces``: Added AWS Workspaces RebootWorkspaces API - Extended Reboot documentation update
* api-change:``iotfleetwise``: The following dataTypes have been removed: CUSTOMER_DECODED_INTERFACE in NetworkInterfaceType; CUSTOMER_DECODED_SIGNAL_INFO_IS_NULL in SignalDecoderFailureReason; CUSTOMER_DECODED_SIGNAL_NETWORK_INTERFACE_INFO_IS_NULL in NetworkInterfaceFailureReason; CUSTOMER_DECODED_SIGNAL in SignalDecoderType
* api-change:``ec2``: This release adds support for adding an ElasticBlockStorage volume configurations in ECS RunTask/StartTask/CreateService/UpdateService APIs. The configuration allows for attaching EBS volumes to ECS Tasks.
* api-change:``secretsmanager``: Doc only update for Secrets Manager
* api-change:``events``: Update events command to latest version
* api-change:``connectcampaigns``: Minor pattern updates for Campaign and Dial Request API fields.
* api-change:``route53``: Route53 now supports geoproximity routing in AWS regions
* api-change:``logs``: Add support for account level subscription filter policies to PutAccountPolicy, DescribeAccountPolicies, and DeleteAccountPolicy APIs. Additionally, PutAccountPolicy has been modified with new optional "selectionCriteria" parameter for resource selection.
* api-change:``location``: This release adds API support for custom layers for the maps service APIs: CreateMap, UpdateMap, DescribeMap.
* api-change:``wisdom``: QueryAssistant and GetRecommendations will be discontinued starting June 1, 2024. To receive generative responses after March 1, 2024 you will need to create a new Assistant in the Connect console and integrate the Amazon Q in Connect JavaScript library (amazon-q-connectjs) into your applications.
* api-change:``redshift-serverless``: Updates to ConfigParameter for RSS workgroup, removal of use_fips_ssl
* api-change:``qconnect``: QueryAssistant and GetRecommendations will be discontinued starting June 1, 2024. To receive generative responses after March 1, 2024 you will need to create a new Assistant in the Connect console and integrate the Amazon Q in Connect JavaScript library (amazon-q-connectjs) into your applications.


2.15.9
======

* api-change:``ec2``: Amazon EC2 R7iz bare metal instances are powered by custom 4th generation Intel Xeon Scalable processors.
* api-change:``redshift-serverless``: use_fips_ssl and require_ssl parameter support for Workgroup, UpdateWorkgroup, and CreateWorkgroup
* api-change:``route53resolver``: This release adds support for query type configuration on firewall rules that enables customers for granular action (ALLOW, ALERT, BLOCK) by DNS query type.
* api-change:``connect``: Minor trait updates for User APIs
* api-change:``codebuild``: Aws CodeBuild now supports new compute type BUILD_GENERAL1_XLARGE
* api-change:``kms``: Documentation updates for AWS Key Management Service (KMS).


2.15.8
======

* api-change:``es``: This release adds support for new or existing Amazon OpenSearch domains to enable TLS 1.3 or TLS 1.2 with perfect forward secrecy cipher suites for domain endpoints.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``docdb``: Adding PerformanceInsightsEnabled and PerformanceInsightsKMSKeyId fields to DescribeDBInstances Response.
* api-change:``opensearch``: This release adds support for new or existing Amazon OpenSearch domains to enable TLS 1.3 or TLS 1.2 with perfect forward secrecy cipher suites for domain endpoints.
* api-change:``lightsail``: This release adds support to set up an HTTPS endpoint on an instance.
* api-change:``connect``: Amazon Connect, Contact Lens Evaluation API increase evaluation notes max length to 3072.
* api-change:``ecs``: This release adds support for managed instance draining which facilitates graceful termination of Amazon ECS instances.
* api-change:``config``: Updated ResourceType enum with new resource types onboarded by AWS Config in November and December 2023.
* api-change:``mediaconvert``: This release includes video engine updates including HEVC improvements, support for ingesting VP9 encoded video in MP4 containers, and support for user-specified 3D LUTs.
* api-change:``sagemaker``: Adding support for provisioned throughput mode for SageMaker Feature Groups
* api-change:``servicecatalog``: Added Idempotency token support to Service Catalog  AssociateServiceActionWithProvisioningArtifact, DisassociateServiceActionFromProvisioningArtifact, DeleteServiceAction API


2.15.7
======

* api-change:``quicksight``: Add LinkEntityArn support for different partitions; Add UnsupportedUserEditionException in UpdateDashboardLinks API; Add support for New Reader Experience Topics
* api-change:``apprunner``: AWS App Runner adds Python 3.11 and Node.js 18 runtimes.
* api-change:``location``: This release introduces a new parameter to bypasses an API key's expiry conditions and delete the key.


2.15.6
======

* api-change:``sagemaker``: Amazon SageMaker Studio now supports Docker access from within app container
* api-change:``codestar-connections``: New integration with the GitLab self-managed provider type.
* api-change:``kinesis-video-archived-media``: NoDataRetentionException thrown when GetImages requested for a Stream that does not retain data (that is, has a DataRetentionInHours of 0).
* api-change:``emr``: Update emr command to latest version


2.15.5
======

* api-change:``mediaconnect``: This release adds the DescribeSourceMetadata API. This API can be used to view the stream information of the flow's source.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``bedrock-agent``: Adding Claude 2.1 support to Bedrock Agents
* api-change:``lakeformation``: This release adds additional configurations on GetTemporaryGlueTableCredentials for Query Session Context.
* api-change:``omics``: Provides minor corrections and an updated description of APIs.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``secretsmanager``: Update endpoint rules and examples.
* api-change:``glue``: This release adds additional configurations for Query Session Context on the following APIs: GetUnfilteredTableMetadata, GetUnfilteredPartitionMetadata, GetUnfilteredPartitionsMetadata.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``networkmonitor``: CloudWatch Network Monitor is a new service within CloudWatch that will help network administrators and operators continuously monitor network performance metrics such as round-trip-time and packet loss between their AWS-hosted applications and their on-premises locations.


2.15.4
======

* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``appintegrations``: The Amazon AppIntegrations service adds DeleteApplication API for deleting applications, and updates APIs to support third party applications reacting to workspace events and make data requests to Amazon Connect for agent and contact events.
* api-change:``neptune-graph``: Adds Waiters for successful creation and deletion of Graph, Graph Snapshot, Import Task and Private Endpoints for Neptune Analytics
* api-change:``rds``: This release adds support for using RDS Data API with Aurora PostgreSQL Serverless v2 and provisioned DB clusters.
* api-change:``codecommit``: AWS CodeCommit now supports customer managed keys from AWS Key Management Service. UpdateRepositoryEncryptionKey is added for updating the key configuration. CreateRepository, GetRepository, BatchGetRepositories are updated with new input or output parameters.
* api-change:``medialive``: MediaLive now supports the ability to configure the audio that an AWS Elemental Link UHD device produces, when the device is configured as the source for a flow in AWS Elemental MediaConnect.
* api-change:``rds-data``: This release adds support for using RDS Data API with Aurora PostgreSQL Serverless v2 and provisioned DB clusters.
* api-change:``eks``: Add support for cluster insights, new EKS capability that surfaces potentially upgrade impacting issues.
* api-change:``amp``: This release updates Amazon Managed Service for Prometheus APIs to support customer managed KMS keys.
* api-change:``sagemaker``: Amazon SageMaker Training now provides model training container access for debugging purposes. Amazon SageMaker Search now provides the ability to use visibility conditions to limit resource access to a single domain or multiple domains.
* api-change:``managedblockchain-query``: Adding Confirmation Status and Execution Status to GetTransaction Response.
* api-change:``guardduty``: This release 1) introduces a new API: GetOrganizationStatistics , and 2) adds a new UsageStatisticType TOP_ACCOUNTS_BY_FEATURE for GetUsageStatistics API
* api-change:``route53``: Amazon Route 53 now supports the Canada West (Calgary) Region (ca-west-1) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``connect``: Adds APIs to manage User Proficiencies and Predefined Attributes. Enhances StartOutboundVoiceContact API input. Introduces SearchContacts API. Enhances DescribeContact API. Adds an API to update Routing Attributes in QueuePriority and QueueTimeAdjustmentSeconds.
* api-change:``mediatailor``: Adds the ability to configure time shifting on MediaTailor channels using the TimeShiftConfiguration field
* api-change:``appstream``: This release introduces configurable clipboard, allowing admins to specify the maximum length of text that can be copied by the users from their device to the remote session and vice-versa.
* api-change:``bedrock-agent``: This release introduces Amazon Aurora as a vector store on Knowledge Bases for Amazon Bedrock


2.15.3
======

* api-change:``cloud9``: Updated Cloud9 API documentation for AL2023 release
* api-change:``eks``: Add support for EKS Cluster Access Management.
* api-change:``chime-sdk-meetings``: Add meeting features to specify a maximum camera resolution, a maximum content sharing resolution, and a maximum number of attendees for a given meeting.
* api-change:``connect``: Adds relatedContactId field to StartOutboundVoiceContact API input. Introduces PauseContact API and ResumeContact API for Task contacts. Adds pause duration, number of pauses, timestamps for last paused and resumed events to DescribeContact API response. Adds new Rule type and new Rule action.
* api-change:``marketplace-catalog``: AWS Marketplace now supports a new API, BatchDescribeEntities, which returns metadata and content for multiple entities.
* api-change:``rds``: RDS - The release adds two new APIs: DescribeDBRecommendations and ModifyDBRecommendation
* enhancement:macOS: Add deprecation warnings for macOS versions 10.14 and prior to the PKG installer and source distribution bundle.
* api-change:``ec2``: Provision BYOIPv4 address ranges and advertise them by specifying the network border groups option in Los Angeles, Phoenix and Dallas AWS Local Zones.
* api-change:``rds``: Updates Amazon RDS documentation by adding code examples
* enhancement:``cloudformation package``: Add support for intrinsic Fn:ForEach (fixes `#8075 <https://github.com/aws/aws-cli/issues/8075>`__)
* api-change:``cognito-idp``: Amazon Cognito now supports trigger versions that define the fields in the request sent to pre token generation Lambda triggers.
* api-change:``appsync``: This release adds additional configurations on GraphQL APIs for limits on query depth, resolver count, and introspection
* api-change:``connectcases``: Increase number of fields that can be included in CaseEventIncludedData from 50 to 200
* api-change:``sagemaker``: This release 1) introduces a new API: DeleteCompilationJob , and 2) adds InfraCheckConfig for Create/Describe training job API
* api-change:``route53resolver``: Add DOH protocols in resolver endpoints.
* api-change:``quicksight``: A docs-only release to add missing entities to the API reference.
* api-change:``fsx``: Added support for FSx for OpenZFS on-demand data replication across AWS accounts and/or regions.Added the IncludeShared attribute for DescribeSnapshots.Added the CopyStrategy attribute for OpenZFSVolumeConfiguration.
* api-change:``kms``: Documentation updates for AWS Key Management Service


2.15.2
======

* api-change:``controltower``: Documentation updates for AWS Control Tower.
* api-change:``quicksight``: Update Dashboard Links support; SingleAxisOptions support; Scatterplot Query limit support.
* api-change:``iot``: This release adds the ability to self-manage certificate signing in AWS IoT Core fleet provisioning using the new certificate provider resource.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``appstream``: This release includes support for images of Windows Server 2022 platform.
* api-change:``opensearch``: Updating documentation for Amazon OpenSearch Service support for new zero-ETL integration with Amazon S3.
* api-change:``workspaces``: Updated note to ensure customers understand running modes.
* api-change:``connect``: This release adds support for more granular billing using tags (key:value pairs)
* api-change:``b2bi``: Documentation updates for AWS B2B Data Interchange
* api-change:``drs``: Adding AgentVersion to SourceServer and RecoveryInstance structures
* api-change:``gamelift``: Amazon GameLift adds the ability to add and update the game properties of active game sessions.
* api-change:``billingconductor``: Billing Conductor is releasing a new API, GetBillingGroupCostReport, which provides the ability to retrieve/view the Billing Group Cost Report broken down by attributes for a specific billing group.
* api-change:``firehose``: This release, 1) adds configurable buffering hints for the Splunk destination, and 2) reduces the minimum configurable buffering interval for supported destinations
* api-change:``neptune-graph``: This is the initial SDK release for Amazon Neptune Analytics


2.15.1
======

* api-change:``location``: This release 1)  adds sub-municipality field in Places API for searching and getting places information, and 2) allows optimizing route calculation based on expected arrival time.
* enhancement:IMDS: Adds a config option to opt out of IMDSv1 fallback
* api-change:``neptune``: This release adds a new parameter configuration setting to the Neptune cluster related APIs that can be leveraged to switch between the underlying supported storage modes.
* api-change:``pinpoint``: This release includes Amazon Pinpoint API documentation updates pertaining to campaign message sending rate limits.
* api-change:``logs``: This release introduces the StartLiveTail API to tail ingested logs in near real time.
* api-change:``imagebuilder``: This release adds the Image Workflows feature to give more flexibility and control over the image building and testing process.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``finspace``: Releasing Scaling Group, Dataview, and Volume APIs
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``ec2``: M2 Mac instances are built on Apple M2 Mac mini computers. I4i instances are powered by 3rd generation Intel Xeon Scalable processors. C7i compute optimized, M7i general purpose and R7i memory optimized instances are powered by custom 4th Generation Intel Xeon Scalable processors.
* api-change:``securityhub``: Added new resource detail objects to ASFF, including resources for AwsDynamoDbTable, AwsEc2ClientVpnEndpoint, AwsMskCluster, AwsS3AccessPoint, AwsS3Bucket


2.15.0
======

* api-change:``backup``: AWS Backup - Features: Add VaultType to the output of DescribeRecoveryPoint, ListRecoveryPointByBackupVault API and add ResourceType to the input of ListRestoreJobs API
* api-change:``payment-cryptography``: AWS Payment Cryptography IPEK feature release
* feature:ContainerProvider: Added Support for EKS container credentials
* api-change:``connect``: Releasing Tagging Support for Instance Management APIS
* api-change:``comprehend``: Documentation updates for Trust and Safety features.
* api-change:``codedeploy``: This release adds support for two new CodeDeploy features: 1) zonal deployments for Amazon EC2 in-place deployments, 2) deployments triggered by Auto Scaling group termination lifecycle hook events.
* api-change:``ec2``: Releasing the new cpuManufacturer attribute within the DescribeInstanceTypes API response which notifies our customers with information on who the Manufacturer is for the processor attached to the instance, for example: Intel.


2.14.6
======

* api-change:``braket``: This release enhances service support to create quantum tasks and hybrid jobs associated with Braket Direct Reservations.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* enchancement:awscrt: Update awscrt version range ceiling to 0.19.19
* api-change:``finspace``: Release General Purpose type clusters
* api-change:``rbin``: Added resource identifier in the output and updated error handling.
* api-change:``cleanroomsml``: Updated service title from cleanroomsml to CleanRoomsML.
* api-change:``ec2``: Adds A10G, T4G, and H100 as accelerator name options and Habana as an accelerator manufacturer option for attribute based selection
* api-change:``cloudformation``: Documentation update, December 2023
* api-change:``cloud9``: This release adds the requirement to include the imageId parameter in the CreateEnvironmentEC2 API call.
* api-change:``cloudformation``: Including UPDATE_* states as a success status for CreateStack waiter.
* api-change:``athena``: Adding IdentityCenter enabled request for interactive query
* api-change:``qconnect``: This release adds the PutFeedback API and allows providing feedback against the specified assistant for the specified target.
* api-change:``medialive``: Adds support for custom color correction on channels using 3D LUT files.
* api-change:``servicecatalog-appregistry``: Documentation-only updates for Dawn
* api-change:``verifiedpermissions``: Adds description field to PolicyStore API's and namespaces field to GetSchema.
* api-change:``billingconductor``: This release adds the ability to specify a linked account of the billing group for the custom line item resource.


2.14.5
======

* api-change:``sagemaker``: This release adds support for 1/ Code Editor, based on Code-OSS, Visual Studio Code Open Source, a new fully managed IDE option in SageMaker Studio  2/ JupyterLab, a new fully managed JupyterLab IDE experience in SageMaker Studio
* api-change:``glue``: Adds observation and analyzer support to the GetDataQualityResult and BatchGetDataQualityResult APIs.
* api-change:``arc-zonal-shift``: This release adds a new capability, zonal autoshift. You can configure zonal autoshift so that AWS shifts traffic for a resource away from an Availability Zone, on your behalf, when AWS determines that there is an issue that could potentially affect customers in the Availability Zone.


2.14.4
======

* api-change:``marketplace-deployment``: AWS Marketplace Deployment is a new service that provides essential features that facilitate the deployment of software, data, and services procured through AWS Marketplace.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``marketplace-catalog``: This release enhances the ListEntities API to support new entity type-specific strongly typed filters in the request and entity type-specific strongly typed summaries in the response.
* api-change:``redshift-serverless``: This release adds the following support for Amazon Redshift Serverless: 1) cross-account cross-VPCs, 2) copying snapshots across Regions, 3) scheduling snapshot creation, and 4) restoring tables from a recovery point.
* api-change:``marketplace-agreement``: The AWS Marketplace Agreement Service provides an API interface that helps AWS Marketplace sellers manage their agreements, including listing, filtering, and viewing details about their agreements.


2.14.3
======

* api-change:``cleanrooms``: AWS Clean Rooms now provides differential privacy to protect against user-identification attempts and machine learning modeling to allow two parties to identify similar users in their data.
* api-change:``cleanroomsml``: Public Preview SDK release of AWS Clean Rooms ML APIs
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``application-autoscaling``: Amazon SageMaker customers can now use Application Auto Scaling to automatically scale the number of Inference Component copies across an endpoint to meet the varying demand of their workloads.
* api-change:``opensearchserverless``: Amazon OpenSearch Serverless collections support an additional attribute called standby-replicas. This allows to specify whether a collection should have redundancy enabled.
* api-change:``sagemaker``: This release adds following support 1/ Improved SDK tooling for model deployment. 2/ New Inference Component based features to lower inference costs and latency 3/ SageMaker HyperPod management. 4/ Additional parameters for FM Fine Tuning in Autopilot
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``opensearch``: Launching Amazon OpenSearch Service support for new zero-ETL integration with Amazon S3. Customers can now manage their direct query data sources to Amazon S3 programatically


2.14.2
======

* api-change:``bedrock-agent``: This release introduces Agents for Amazon Bedrock
* api-change:``bedrock-runtime``: This release adds support for minor versions/aliases for invoke model identifier.
* api-change:``connect``: Added support for following capabilities: Amazon Connect's in-app, web, and video calling. Two-way SMS integrations. Contact Lens real-time chat analytics feature. Amazon Connect Analytics Datalake capability. Capability to configure real time chat rules.
* api-change:``accessanalyzer``: This release adds support for external access findings for S3 directory buckets to help you easily identify cross-account access. Updated service API, documentation, and paginators.
* api-change:``s3``: Adds support for S3 Express One Zone.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``bedrock``: This release adds support for customization types, model life cycle status and minor versions/aliases for model identifiers.
* api-change:``bedrock-agent-runtime``: This release introduces Agents for Amazon Bedrock Runtime
* api-change:``s3control``: Adds support for S3 Express One Zone, and InvocationSchemaVersion 2.0 for S3 Batch Operations.
* api-change:``customer-profiles``: This release introduces DetectProfileObjectType API to auto generate object type mapping.
* enhancement:awscrt: Update awscrt version requirement to 0.19.18
* api-change:``qbusiness``: Amazon Q - a generative AI powered application that your employees can use to ask questions and get answers from knowledge spread across disparate content repositories, summarize reports, write articles, take actions, and much more - all within their company's connected content repositories.
* api-change:``qconnect``: Amazon Q in Connect, an LLM-enhanced evolution of Amazon Connect Wisdom. This release adds generative AI support to Amazon Q Connect QueryAssistant and GetRecommendations APIs.


2.14.1
======

* api-change:``elasticache``: Launching Amazon ElastiCache Serverless that enables you to create a cache in under a minute without any capacity management. ElastiCache Serverless monitors the cache's memory, CPU, and network usage and scales both vertically and horizontally to support your application's requirements.


2.14.0
======

* api-change:``controltower``: This release adds the following support: 1. The EnableControl API can configure controls that are configurable.  2. The GetEnabledControl API shows the configured parameters on an enabled control. 3. The new UpdateEnabledControl API can change parameters on an enabled control.
* enhancement:``s3 cp``: Support streaming uploads from stdin and streaming downloads to stdout for CRT transfer client
* api-change:``b2bi``: This is the initial SDK release for AWS B2B Data Interchange.
* api-change:``efs``: Update efs command to latest version
* enhancement:``s3``: Automatically configure CRC32 checksums for uploads and checksum validation for downloads through the CRT transfer client.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``transcribe``: This release adds support for AWS HealthScribe APIs within Amazon Transcribe
* enchancement:``s3``: Update ``target_bandwidth`` defaults. If not configured, the AWS CLI will use the AWS CRT to attempt to determine a recommended target throughput to use based on the system. If there is no recommended throughput, the AWS CLI now falls back to ten gigabits per second.
* bugfix:``s3``: Support integers (e.g. 1024) and values that do not have a magnitude prefix (e.g. 1024B/s) for s3 rate configurations.
* api-change:``backup``: AWS Backup now supports restore testing, a new feature that allows customers to automate restore testing and validating their backups. Additionally, this release adds support for EBS Snapshots Archive tier.
* api-change:``fis``: AWS FIS adds support for multi-account experiments & empty target resolution. This release also introduces the CreateTargetAccountConfiguration API that allows experiments across multiple AWS accounts, and the ListExperimentResolvedTargets API to list target details.
* feature:``s3``: ``s3`` command integrations with the CRT S3 transfer client is now generally available and supported for production use. The ``preferred_transfer_client`` and ``target_bandwidth`` S3 configurations are also now stable and no longer documented as experimental.
* feature:``s3``: Add ``auto`` as new default option for ``preferred_transfer_client`` S3 configuration. This option auto resolves the S3 transfer client to use based on the system running the ``s3`` transfer commands. In addition, the ``default`` value for the ``preferred_transfer_client`` configuration is now named ``classic``.
* api-change:``appsync``: This update enables introspection of Aurora cluster databases using the RDS Data API
* api-change:``glue``: add observations support to DQ CodeGen config model + update document for connectiontypes supported by ConnectorData entities
* api-change:``securityhub``: Adds and updates APIs to support central configuration. This feature allows the Security Hub delegated administrator to configure Security Hub for their entire AWS Org across multiple regions from a home Region. With this release, findings also include account name and application metadata.
* api-change:``rds``: Updates Amazon RDS documentation for support for RDS for Db2.


2.13.39
=======

* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``iotfleetwise``: AWS IoT FleetWise introduces new APIs for vision system data, such as data collected from cameras, radars, and lidars. You can now model and decode complex data types.
* api-change:``fsx``: Added support for FSx for ONTAP scale-out file systems and FlexGroup volumes. Added the HAPairs field and ThroughputCapacityPerHAPair for filesystem. Added AggregateConfiguration (containing Aggregates and ConstituentsPerAggregate) and SizeInBytes for volume.
* api-change:``eks``: This release adds support for EKS Pod Identity feature. EKS Pod Identity makes it easy for customers to obtain IAM permissions for the applications running in their EKS clusters.
* api-change:``redshift``: This release adds support for multi-data warehouse writes through data sharing.
* api-change:``efs``: Update efs command to latest version
* api-change:``codestar-connections``: This release adds support for the CloudFormation Git sync feature. Git sync enables updating a CloudFormation stack from a template stored in a Git repository.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``config``: Support Periodic Recording for Configuration Recorder
* api-change:``workspaces-thin-client``: Initial release of Amazon WorkSpaces Thin Client
* api-change:``bcm-data-exports``: Users can create, read, update, delete Exports of billing and cost management data.  Users can get details of Export Executions and details of Tables for exporting.  Tagging support is provided for Exports
* api-change:``sagemaker``: This feature adds the end user license agreement status as a model access configuration parameter.
* api-change:``ecs``: Adds a new 'type' property to the Setting structure. Adds a new AccountSetting - guardDutyActivate for ECS.
* api-change:``personalize``: Enables metadata in recommendations, recommendations with themes, and next best action recommendations
* api-change:``kinesis``: This release adds support for resource based policies on streams and consumers.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``s3``: Adding new params - Key and Prefix, to S3 API operations for supporting S3 Access Grants. Note - These updates will not change any of the existing S3 API functionality.
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate recommendations with customization and discounts preferences.
* api-change:``cost-optimization-hub``: This release launches Cost Optimization Hub, a new AWS Billing and Cost Management feature that helps you consolidate and prioritize cost optimization recommendations across your AWS Organizations member accounts and AWS Regions, so that you can get the most out of your AWS spend.
* api-change:``workspaces``: The release introduces Multi-Region Resilience one-way data replication that allows you to replicate data from your primary WorkSpace to a standby WorkSpace in another AWS Region. DescribeWorkspaces now returns the status of data replication.
* api-change:``secretsmanager``: AWS Secrets Manager has released the BatchGetSecretValue API, which allows customers to fetch up to 20 Secrets with a single request using a list of secret names or filters.
* api-change:``lakeformation``: This release adds four new APIs "DescribeLakeFormationIdentityCenterConfiguration", "CreateLakeFormationIdentityCenterConfiguration", "DescribeLakeFormationIdentityCenterConfiguration", and "DeleteLakeFormationIdentityCenterConfiguration", and also updates the corresponding documentation.
* api-change:``freetier``: This is the initial SDK release for the AWS Free Tier GetFreeTierUsage API
* api-change:``quicksight``: This release launches new APIs for trusted identity propagation setup and supports creating datasources using trusted identity propagation as authentication method for QuickSight accounts configured with IAM Identity Center.
* enhancement:awscrt: Update awscrt version range ceiling to 0.19.16
* api-change:``personalize-events``: This release enables PutActions and PutActionInteractions
* api-change:``detective``: Added new APIs in Detective to support resource investigations
* api-change:``logs``: Added APIs to Create, Update, Get, List and Delete LogAnomalyDetectors and List and Update Anomalies in Detector. Added LogGroupClass attribute for LogGroups to classify loggroup as Standard loggroup with all capabilities or InfrequentAccess loggroup with limited capabilities.
* api-change:``personalize-runtime``: Enables metadata in recommendations and next best action recommendations
* api-change:``cloudtrail``: CloudTrail Lake now supports federating event data stores. giving users the ability to run queries against their event data using Amazon Athena.
* api-change:``s3control``: Amazon S3 Batch Operations now manages buckets or prefixes in a single step.
* api-change:``accessanalyzer``: IAM Access Analyzer now continuously monitors IAM roles and users in your AWS account or organization to generate findings for unused access. Additionally, IAM Access Analyzer now provides custom policy checks to validate that IAM policies adhere to your security standards ahead of deployments.
* api-change:``securityhub``: Adds and updates APIs to support customizable security controls. This feature allows Security Hub customers to provide custom parameters for security controls. With this release, findings for controls that support custom parameters will include the parameters used to generate the findings.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``amp``: This release adds support for the Amazon Managed Service for Prometheus collector, a fully managed, agentless Prometheus metrics scraping capability.
* api-change:``eks-auth``: This release adds support for EKS Pod Identity feature. EKS Pod Identity makes it easy for customers to obtain IAM permissions for their applications running in the EKS clusters.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``repostspace``: Initial release of AWS re:Post Private
* api-change:``controltower``: Add APIs to create and manage a landing zone.
* api-change:``s3control``: Introduce Amazon S3 Access Grants, a new S3 access control feature that maps identities in directories such as Active Directory, or AWS Identity and Access Management (IAM) Principals, to datasets in S3.
* api-change:``transcribe``: This release adds support for transcriptions from audio sources in 64 new languages and introduces generative call summarization in Transcribe Call Analytics (Post call)
* api-change:``guardduty``: Add support for Runtime Monitoring for ECS and ECS-EC2.
* api-change:``managedblockchain``: Add optional NetworkType property to Accessor APIs
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version


2.13.38
=======

* api-change:``trustedadvisor``: AWS Trusted Advisor introduces new APIs to enable you to programmatically access Trusted Advisor best practice checks, recommendations, and prioritized recommendations. Trusted Advisor APIs enable you to integrate Trusted Advisor with your operational tools to automate your workloads.
* api-change:``mgn``: Removed invalid and unnecessary default values.
* api-change:``kinesisvideo``: Docs only build to bring up-to-date with public docs.
* api-change:``events``: Update events command to latest version
* api-change:``cloudfront-keyvaluestore``: This release adds support for CloudFront KeyValueStore, a globally managed key value datastore associated with CloudFront Functions.
* api-change:``ec2``: This release adds new features for Amazon VPC IP Address Manager (IPAM) Allowing a choice between Free and Advanced Tiers, viewing public IP address insights across regions and in Amazon Cloudwatch, use IPAM to plan your subnet IPs within a VPC and bring your own autonomous system number to IPAM.
* api-change:``appmesh``: Change the default value of these fields from 0 to null: MaxConnections, MaxPendingRequests, MaxRequests, HealthCheckThreshold, PortNumber, and HealthCheckPolicy -> port. Users are not expected to perceive the change, except that badRequestException is thrown when required fields missing configured.
* api-change:``sso-admin``: Improves support for configuring RefreshToken and TokenExchange grants on applications.
* api-change:``s3``: Add support for automatic date based partitioning in S3 Server Access Logs.
* api-change:``iotsitewise``: Adds 1/ user-defined unique identifier for asset and model metadata, 2/ asset model components, and 3/ query API for asset metadata and telemetry data. Supports 4/ multi variate anomaly detection using Amazon Lookout for Equipment, 5/ warm storage tier, and 6/ buffered ingestion of time series data.
* api-change:``codepipeline``: CodePipeline now supports overriding source revisions to achieve manual re-deploy of a past revision
* api-change:``medialive``: MediaLive has now added support for per-output static image overlay.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``verifiedpermissions``: Adding BatchIsAuthorized API which supports multiple authorization requests against a PolicyStore
* api-change:``s3``: Removes all default 0 values for numbers and false values for booleans
* api-change:``inspector-scan``: This release adds support for the new Amazon Inspector Scan API. The new Inspector Scan API can synchronously scan SBOMs adhering to the CycloneDX v1.5 format.
* api-change:``athena``: Adding SerivicePreProcessing time metric
* api-change:``ivs``: type & defaulting refinement to various range properties
* api-change:``connect``: This release adds WISDOM_QUICK_RESPONSES as new IntegrationType of Connect IntegrationAssociation resource and bug fixes.
* api-change:``location``: Remove default value and allow nullable for request parameters having minimum value larger than zero.
* api-change:``internetmonitor``: Adds new querying capabilities for running data queries on a monitor
* api-change:``emr``: Update emr command to latest version
* api-change:``sts``: API updates for the AWS Security Token Service
* api-change:``sso-oidc``: Adding support for `sso-oauth:CreateTokenWithIAM`.
* api-change:``osis``: Add support for enabling a persistent buffer when creating or updating an OpenSearch Ingestion pipeline. Add tags to Pipeline and PipelineSummary response models.
* api-change:``dlm``: Added support for SAP HANA in Amazon Data Lifecycle Manager EBS snapshot lifecycle policies with pre and post scripts.
* api-change:``codestar-connections``: This release adds support for the CloudFormation Git sync feature. Git sync enables updating a CloudFormation stack from a template stored in a Git repository.
* api-change:``codestar-connections``: This release updates a few CodeStar Connections related APIs.
* api-change:``redshift``: Updated SDK for Amazon Redshift, which you can use to configure a connection with IAM Identity Center to manage access to databases. With these, you can create a connection through a managed application. You can also change a managed application, delete it, or get information about an existing one.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``wisdom``: This release adds QuickResponse as a new Wisdom resource and Wisdom APIs for import, create, read, search, update and delete QuickResponse resources.
* api-change:``ec2``: This release adds support for Security group referencing over Transit gateways, enabling you to simplify Security group management and control of instance-to-instance traffic across VPCs that are connected by Transit gateway.
* api-change:``rds``: This release adds support for option groups and replica enhancements to Amazon RDS Custom.
* api-change:``cloudfront``: This release adds support for CloudFront KeyValueStore, a globally managed key value datastore associated with CloudFront Functions.
* api-change:``redshift-serverless``: Updated SDK for Amazon Redshift Serverless, which provides the ability to configure a connection with IAM Identity Center to manage user and group access to databases.
* api-change:``cloud9``: A minor doc only update related to changing the date of an API change.
* api-change:``ivschat``: type & defaulting refinement to various range properties
* api-change:``iottwinmaker``: This release adds following support. 1. New APIs for metadata bulk operations. 2. Modify the component type API to support composite component types - nesting component types within one another. 3. New list APIs for components and properties. 4. Support the larger scope digital twin modeling.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``docdb``: Amazon DocumentDB updates for new cluster storage configuration: Amazon DocumentDB I/O-Optimized.
* api-change:``pipes``: TargetParameters now properly supports BatchJobParameters.ArrayProperties.Size and BatchJobParameters.RetryStrategy.Attempts being optional, and EcsTaskParameters.Overrides.EphemeralStorage.SizeInGiB now properly required when setting EphemeralStorage
* api-change:``ecr``: Documentation and operational updates for Amazon ECR, adding support for pull through cache rules for upstream registries that require authentication.
* api-change:``cloudformation``: This release adds a new flag ImportExistingResources to CreateChangeSet. Specify this parameter on a CREATE- or UPDATE-type change set to import existing resources with custom names instead of recreating them.
* api-change:``macie``: The macie client has been removed following the deprecation of the service.


2.13.37
=======

* api-change:``polly``: Add new engine - long-form - dedicated for longer content, such as news articles, training materials, or marketing videos.
* api-change:``codecatalyst``: This release adds functionality for retrieving information about workflows and workflow runs and starting workflow runs in Amazon CodeCatalyst.
* api-change:``kafka``: Added a new API response field which determines if there is an action required from the customer regarding their cluster.
* api-change:``ivs-realtime``: This release introduces server side composition and recording for stages.
* api-change:``glue``: Introduces new column statistics APIs to support statistics generation for tables within the Glue Data Catalog.
* api-change:``imagebuilder``: This release adds the Image Lifecycle Management feature to automate the process of deprecating, disabling and deleting outdated images and their associated resources.
* api-change:``ssm-incidents``: Introduces new APIs ListIncidentFindings and BatchGetIncidentFindings to use findings related to an incident.
* api-change:``autoscaling``: This release introduces Instance Maintenance Policy, a new EC2 Auto Scaling capability that allows customers to define whether instances are launched before or after existing instances are terminated during instance replacement operations.
* api-change:``cloudtrail``: The Lake Repricing feature lets customers configure a BillingMode for an event data store. The BillingMode determines the cost for ingesting and storing events and the default and maximum retention period for the event data store.
* api-change:``dlm``: This release adds support for Amazon Data Lifecycle Manager default policies for EBS snapshots and EBS-backed AMIs.
* api-change:``sso-admin``: Instances bound to a single AWS account, API operations for managing instances and applications, and assignments to applications are now supported. Trusted identity propagation is also supported, with new API operations for managing trusted token issuers and application grants and scopes.
* api-change:``finspace-data``: Adding deprecated trait to APIs in this name space.
* api-change:``fsx``: Enables customers to update their PerUnitStorageThroughput on their Lustre file systems.
* api-change:``finspace``: Adding deprecated trait on Dataset Browser Environment APIs
* api-change:``iot``: GA release the ability to index and search devices based on their GeoLocation data. With GeoQueries you can narrow your search to retrieve devices located in the desired geographic boundary.
* api-change:``pinpoint-sms-voice-v2``: Amazon Pinpoint now offers additional operations as part of version 2 of the SMS and voice APIs. This release includes 26 new APIs to create and manage phone number registrations, add verified destination numbers, and request sender IDs.
* api-change:``ssm``: This release introduces the ability to filter automation execution steps which have parent steps. In addition, runbook variable information is returned by GetAutomationExecution and parent step information is returned by the DescribeAutomationStepExecutions API.
* api-change:``transfer``: Introduced S3StorageOptions for servers to enable directory listing optimizations and added Type fields to logical directory mappings.
* api-change:``mediapackage``: DRM_TOP_LEVEL_COMPACT allows placing content protection elements at the MPD level and referenced at the AdaptationSet level
* api-change:``mwaa``: This Amazon MWAA release adds support for customer-managed VPC endpoints. This lets you choose whether to create, and manage your environment's VPC endpoints, or to have Amazon MWAA create, and manage them for you.
* api-change:``quicksight``: Custom permission support for QuickSight roles; Three new datasources STARBURST, TRINO, BIGQUERY; Lenient mode changes the default behavior to allow for exporting and importing with certain UI allowed errors, Support for permissions and tags export and import.
* api-change:``rds``: Updates Amazon RDS documentation for support for upgrading RDS for MySQL snapshots from version 5.7 to version 8.0.
* api-change:``lambda``: Adds support for logging configuration in Lambda Functions. Customers will have more control how their function logs are captured and to which cloud watch log group they are delivered also.
* api-change:``ec2``: AWS EBS now supports Snapshot Lock, giving users the ability to lock an EBS Snapshot to prohibit deletion of the snapshot. This release introduces the LockSnapshot, UnlockSnapshot & DescribeLockedSnapshots APIs to manage lock configuration for snapshots. The release also includes the dl2q_24xlarge.
* api-change:``lambda``: Add Java 21 (java21) support to AWS Lambda
* api-change:``sagemaker``: Amazon SageMaker Studio now supports Trainium instance types - trn1.2xlarge, trn1.32xlarge, trn1n.32xlarge.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``s3control``: Add 5 APIs to create, update, get, list, delete S3 Storage Lens group(eg. CreateStorageLensGroup), 3 APIs for tagging(TagResource,UntagResource,ListTagsForResource), and update to StorageLensConfiguration to allow metrics to be aggregated on Storage Lens groups.
* api-change:``redshift``: The custom domain name SDK for Amazon Redshift provisioned clusters is updated with additional required parameters for modify and delete operations. Additionally, users can provide domain names with longer top-level domains.
* api-change:``codecatalyst``: This release includes updates to the Dev Environment APIs to include an optional vpcConnectionName parameter that supports using Dev Environments with Amazon VPC.
* api-change:``ec2``: Enable use of tenant-specific PublicSigningKeyUrl from device trust providers and onboard jumpcloud as a new device trust provider.
* api-change:``ssm-sap``: Update the default value of MaxResult to 50.
* enhancement:``ssm`` Session Manager: Pass StartSession API response as environment variable to session-manager-plugin
* api-change:``macie2``: This release adds support for configuring Macie to assume an IAM role when retrieving sample occurrences of sensitive data reported by findings.


2.13.36
=======

* api-change:``iot``: This release introduces new attributes in API CreateSecurityProfile, UpdateSecurityProfile and DescribeSecurityProfile to support management of Metrics Export for AWS IoT Device Defender Detect.
* api-change:``pipes``: Added support (via new LogConfiguration field in CreatePipe and UpdatePipe APIs) for logging to Amazon CloudWatch Logs, Amazon Simple Storage Service (Amazon S3), and Amazon Kinesis Data Firehose
* api-change:``emr``: Update emr command to latest version
* api-change:``dataexchange``: Removed Required trait for DataSet.OriginDetails.ProductId.
* api-change:``marketplace-entitlement``: Update marketplace-entitlement command to latest version
* api-change:``sagemaker``: This release makes Model Registry Inference Specification fields as not required.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``controltower``: AWS Control Tower supports tagging for enabled controls. This release introduces TagResource, UntagResource and ListTagsForResource APIs to manage tags in existing enabled controls. It updates EnabledControl API to tag resources at creation time.
* api-change:``backup``: AWS Backup - Features: Provide Job Summary for your backup activity.
* api-change:``cur``: This release adds support for tagging and customers can now tag report definitions. Additionally, ReportStatus is now added to report definition to show when the last delivered time stamp and if it succeeded or not.
* api-change:``resource-explorer-2``: Resource Explorer supports multi-account search. You can now use Resource Explorer to search and discover resources across AWS accounts within your organization or organizational unit.
* api-change:``mediatailor``: Removed unnecessary default values.
* api-change:``ec2``: EC2 adds API updates to enable ENA Express at instance launch time.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``signer``: Documentation updates for AWS Signer
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``ec2``: Adds the new EC2 DescribeInstanceTopology API, which you can use to retrieve the network topology of your running instances on select platform types to determine their relative proximity to each other.
* api-change:``connect``: Introducing SegmentAttributes parameter for StartChatContact API
* api-change:``fms``: Adds optimizeUnassociatedWebACL flag to ManagedServiceData, updates third-party firewall examples, and other minor documentation updates.
* api-change:``glue``: Introduces new storage optimization APIs to support automatic compaction of Apache Iceberg tables.
* api-change:``mediaconvert``: This release includes the ability to specify any input source as the primary input for corresponding follow modes, and allows users to specify fit and fill behaviors without resizing content.
* api-change:``cleanrooms``: This feature provides the ability for the collaboration creator to configure either the member who can run queries or a different member in the collaboration to be billed for query compute costs.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``servicecatalog-appregistry``: When the customer associates a resource collection to their application with this new feature, then a new application tag will be applied to all supported resources that are part of that collection. This allows customers to more easily find the application that is associated with those resources.
* api-change:``rds``: Updates Amazon RDS documentation for zero-ETL integrations.
* api-change:``dms``: Added new Db2 LUW Target endpoint with related endpoint settings. New executeTimeout endpoint setting for mysql endpoint. New ReplicationDeprovisionTime field for serverless describe-replications.
* api-change:``ecs``: Adds a Client Token parameter to the ECS RunTask API. The Client Token parameter allows for idempotent RunTask requests.
* api-change:``lambda``: Add Python 3.12 (python3.12) support to AWS Lambda


2.13.35
=======

* enhancement:awscrt: Update awscrt version range ceiling to 0.19.12. Fixes `#8320 <https://github.com/aws/aws-cli/issues/8320>`__


2.13.34
=======

* api-change:``connectcases``: This release adds the ability to add/view comment authors through CreateRelatedItem and SearchRelatedItems API. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``datasync``: This change allows for 0 length access keys and secret keys for object storage locations. Users can now pass in empty string credentials.
* api-change:``ec2``: AWS EBS now supports Block Public Access for EBS Snapshots. This release introduces the EnableSnapshotBlockPublicAccess, DisableSnapshotBlockPublicAccess and GetSnapshotBlockPublicAccessState APIs to manage account-level public access settings for EBS Snapshots in an AWS Region.
* api-change:``connect``: This release adds the ability to integrate customer lambda functions with Connect attachments for scanning and updates the ListIntegrationAssociations API to support filtering on IntegrationArn.
* api-change:``omics``: Adding Run UUID and Run Output URI: GetRun and StartRun API response has two new fields "uuid" and "runOutputUri".
* api-change:``lambda``: Add Node 20 (nodejs20.x) support to AWS Lambda.
* api-change:``connect``: This release clarifies in our public documentation that InstanceId is a requirement for SearchUsers API requests.
* api-change:``omics``: Support UBAM filetype for Omics Storage and make referenceArn optional
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``comprehend``: This release adds support for toxicity detection and prompt safety classification.
* api-change:``cloudformation``: Added new ConcurrencyMode feature for AWS CloudFormation StackSets for faster deployments to target accounts.
* api-change:``logs``: Update to support new APIs for delivery of logs from AWS services.
* api-change:``eks``: Adding EKS Anywhere subscription related operations.
* api-change:``lambda``: Add Custom runtime on Amazon Linux 2023 (provided.al2023) support to AWS Lambda.
* api-change:``resiliencehub``: AWS Resilience Hub enhances Resiliency Score, providing actionable recommendations to improve application resilience. Amazon Elastic Kubernetes Service (EKS) operational recommendations have been added to help improve the resilience posture of your applications.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``rds``: This Amazon RDS release adds support for patching the OS of an RDS Custom for Oracle DB instance. You can now upgrade the database or operating system using the modify-db-instance command.
* api-change:``guardduty``: Added API support for new GuardDuty EKS Audit Log finding types.
* api-change:``cloudtrail``: The Insights in Lake feature lets customers enable CloudTrail Insights on a source CloudTrail Lake event data store and create a destination event data store to collect Insights events based on unusual management event activity in the source event data store.
* api-change:``sqs``: This release enables customers to call SQS using AWS JSON-1.0 protocol and bug fix.
* api-change:``redshift-serverless``: Added a new parameter in the workgroup that helps you control your cost for compute resources. This feature provides a ceiling for RPUs that Amazon Redshift Serverless can scale up to. When automatic compute scaling is required, having a higher value for MaxRPU can enhance query throughput.
* enhancement:awscrt: Update awscrt version range ceiling to 0.19.10
* api-change:``sqs``: This release enables customers to call SQS using AWS JSON-1.0 protocol.


2.13.33
=======

* api-change:``dataexchange``: Updated SendDataSetNotificationRequest Comment to be maximum length 4096.
* api-change:``launch-wizard``: AWS Launch Wizard is a service that helps reduce the time it takes to deploy applications to the cloud while providing a guided deployment experience.
* api-change:``dlm``: Added support for pre and post scripts in Amazon Data Lifecycle Manager EBS snapshot lifecycle policies.
* api-change:``docdb``: Update the input of CreateDBInstance and ModifyDBInstance to support setting CA Certificates. Update the output of DescribeDBInstance and DescribeDBEngineVersions to show current and supported CA certificates.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``codebuild``: AWS CodeBuild now supports AWS Lambda compute.
* api-change:``connect``: Added new API that allows Amazon Connect Outbound Campaigns to create contacts in Amazon Connect when ingesting your dial requests.
* api-change:``ce``: This release extends the GetReservationPurchaseRecommendation API to support recommendations for Amazon MemoryDB reservations.
* api-change:``iotwireless``: Added LoRaWAN version 1.0.4 support
* api-change:``rds``: This Amazon RDS release adds support for the multi-tenant configuration. In this configuration, an RDS DB instance can contain multiple tenant databases. In RDS for Oracle, a tenant database is a pluggable database (PDB).
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``connect``: Amazon Connect Chat introduces Create Persistent Contact Association API, allowing customers to choose when to resume previous conversations from previous chats, eliminating the need to repeat themselves and allowing agents to provide personalized service with access to entire conversation history.
* api-change:``config``: Updated ResourceType enum with new resource types onboarded by AWS Config in October 2023.
* bugfix:``help``: Relax line length limit for rendered ``help`` pages
* api-change:``mwaa``: This release adds support for Apache Airflow version 2.7.2. This version release includes support for deferrable operators and triggers.
* api-change:``route53``: Add partitional endpoints for iso-e and iso-f.
* api-change:``polly``: Amazon Polly adds new US English voices - Danielle and Gregory. Danielle and Gregory are available as Neural voices only.
* api-change:``iam``: Add partitional endpoint for iso-e.


2.13.32
=======

* api-change:``sagemaker``: Support for batch transform input in Model dashboard
* api-change:``network-firewall``: This release introduces the stateless rule analyzer, which enables you to analyze your stateless rules for asymmetric routing.
* api-change:``quicksight``: This release introduces Float Decimal Type as SubType in QuickSight SPICE datasets and Custom week start and Custom timezone options in Analysis and Dashboard
* api-change:``connect``: GetMetricDataV2 API: Update to include new metrics PERCENT_NON_TALK_TIME, PERCENT_TALK_TIME, PERCENT_TALK_TIME_AGENT, PERCENT_TALK_TIME_CUSTOMER
* api-change:``rds``: This release adds support for customized networking resources to Amazon RDS Custom.
* api-change:``apprunner``: AWS App Runner now supports using dual-stack address type for the public endpoint of your incoming traffic.
* api-change:``globalaccelerator``: Global Accelerator now support accelerators with cross account endpoints.
* api-change:``redshift``: Added support for Multi-AZ deployments for Provisioned RA3 clusters that provide 99.99% SLA availability.
* api-change:``connect``: Adds the BatchGetFlowAssociation API which returns flow associations (flow-resource) corresponding to the list of resourceArns supplied in the request. This release also adds IsDefault, LastModifiedRegion and LastModifiedTime fields to the responses of several Describe and List APIs.
* api-change:``glue``: This release introduces Google BigQuery Source and Target in AWS Glue CodeGenConfigurationNode.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``gamelift``: Amazon GameLift adds support for shared credentials, which allows applications that are deployed on managed EC2 fleets to interact with other AWS resources.


2.13.31
=======

* api-change:``mediapackagev2``: This feature allows customers to create a combination of manifest filtering, startover and time delay configuration that applies to all egress requests by default.
* api-change:``neptunedata``: Minor change to not retry CancelledByUserException
* api-change:``s3outposts``: Updated ListOutpostsWithS3 API response to include S3OutpostArn for use with AWS RAM.
* api-change:``redshift``: added support to create a dual stack cluster
* api-change:``neptune``: Update TdeCredentialPassword type to SensitiveString
* api-change:``finspace``: Introducing new API UpdateKxClusterCodeConfiguration, introducing new cache types for clusters and introducing new deployment modes for updating clusters.
* api-change:``amplify``: Add backend field to CreateBranch and UpdateBranch requests. Add pagination support for ListApps, ListDomainAssociations, ListBranches, and ListJobs
* api-change:``translate``: Added support for Brevity translation settings feature.
* api-change:``emr``: Update emr command to latest version
* api-change:``rds``: This release launches the CreateIntegration, DeleteIntegration, and DescribeIntegrations APIs to manage zero-ETL Integrations.
* api-change:``m2``: Added name filter ability for ListDataSets API, added ForceUpdate for Updating environment and BatchJob submission using S3BatchJobIdentifier
* api-change:``connect``: This release adds InstanceId field for phone number APIs.
* api-change:``resiliencehub``: Introduced the ability to filter applications by their last assessment date and time and have included metrics for the application's estimated workload Recovery Time Objective (RTO) and estimated workload Recovery Point Objective (RPO).
* api-change:``application-insights``: Automate attaching managed policies
* api-change:``datasync``: Platform version changes to support AL1 deprecation initiative.
* api-change:``wisdom``: This release added necessary API documents on creating a Wisdom knowledge base to integrate with S3.
* api-change:``dataexchange``: We added a new API action: SendDataSetNotification.
* api-change:``wafv2``: Updates the descriptions for the calls that manage web ACL associations, to provide information for customer-managed IAM policies.
* api-change:``ec2``: Capacity Blocks for ML are a new EC2 purchasing option for reserving GPU instances on a future date to support short duration machine learning (ML) workloads. Capacity Blocks automatically place instances close together inside Amazon EC2 UltraClusters for low-latency, high-throughput networking.
* api-change:``redshift-serverless``: Added support for custom domain names for Amazon Redshift Serverless workgroups. This feature enables customers to create a custom domain name and use ACM to generate fully secure connections to it.
* api-change:``pinpoint``: Updated documentation to describe the case insensitivity for EndpointIds.


2.13.30
=======

* api-change:``groundstation``: This release will allow KMS alias names to be used when creating Mission Profiles
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``opensearch``: You can specify ipv4 or dualstack IPAddressType for cluster endpoints. If you specify IPAddressType as dualstack, the new endpoint will be visible under the 'EndpointV2' parameter and will support IPv4 and IPv6 requests. Whereas, the 'Endpoint' will continue to serve IPv4 requests.
* api-change:``connectcases``: Increase maximum length of CommentBody to 3000, and increase maximum length of StringValue to 1500
* api-change:``iam``: Updates to GetAccessKeyLastUsed action to replace NoSuchEntity error with AccessDeniedException error.
* api-change:``redshift``: Add Redshift APIs GetResourcePolicy, DeleteResourcePolicy, PutResourcePolicy and DescribeInboundIntegrations for the new Amazon Redshift Zero-ETL integration feature, which can be used to control data ingress into Redshift namespace, and view inbound integrations.
* api-change:``transfer``: No API changes from previous release. This release migrated the model to Smithy keeping all features unchanged.
* api-change:``sns``: Message Archiving and Replay is now supported in Amazon SNS for FIFO topics.
* api-change:``ec2``: Launching GetSecurityGroupsForVpc API. This API gets security groups that can be associated by the AWS account making the request with network interfaces in the specified VPC.
* api-change:``appstream``: This release introduces multi-session fleets, allowing customers to provision more than one user session on a single fleet instance.
* enhancement:awscrt: Update awscrt version range ceiling to 0.19.6
* api-change:``network-firewall``: Network Firewall now supports inspection of outbound SSL/TLS traffic.
* api-change:``ssm-sap``: AWS Systems Manager for SAP added support for registration and discovery of SAP ABAP applications
* api-change:``sagemaker``: Amazon Sagemaker Autopilot now supports Text Generation jobs.


2.13.29
=======

* api-change:``iam``: Add the partitional endpoint for IAM in iso-f.
* api-change:``networkmanager``: This release adds API support for Tunnel-less Connect (NoEncap Protocol) for AWS Cloud WAN
* api-change:``connect``: This release adds support for updating phone number metadata, such as phone number description.
* api-change:``medical-imaging``: Updates on documentation links
* api-change:``eks``: Added support for Cluster Subnet and Security Group mutability.
* api-change:``discovery``: This release introduces three new APIs: StartBatchDeleteConfigurationTask, DescribeBatchDeleteConfigurationTask, and BatchDeleteAgents.
* api-change:``migrationhubstrategy``: This release introduces multi-data-source feature in Migration Hub Strategy Recommendations. This feature now supports vCenter as a data source to fetch inventory in addition to ADS and Import from file workflow that is currently supported with MHSR collector.
* api-change:``redshift-serverless``: This release adds support for customers to see the patch version and workgroup version in Amazon Redshift Serverless.
* api-change:``codepipeline``: Add ability to trigger pipelines from git tags, define variables at pipeline level and new pipeline type V2.
* api-change:``opensearchserverless``: This release includes the following new APIs: CreateLifecyclePolicy, UpdateLifecyclePolicy, BatchGetLifecyclePolicy, DeleteLifecyclePolicy, ListLifecyclePolicies and BatchGetEffectiveLifecyclePolicy to support the data lifecycle management feature.
* api-change:``appintegrations``: Updated ScheduleConfig to be an optional input to CreateDataIntegration to support event driven downloading of files from sources such as Amazon s3 using Amazon Connect AppIntegrations.
* api-change:``ssm``: This release introduces a new API: DeleteOpsItem. This allows deletion of an OpsItem.
* api-change:``appconfig``: Update KmsKeyIdentifier constraints to support AWS KMS multi-Region keys.
* api-change:``migrationhub-config``: This release introduces DeleteHomeRegionControl API that customers can use to delete the Migration Hub Home Region configuration
* api-change:``ec2``: This release updates the documentation for InstanceInterruptionBehavior and HibernationOptionsRequest to more accurately describe the behavior of these two parameters when using Spot hibernation.
* api-change:``rekognition``: Amazon Rekognition introduces StartMediaAnalysisJob, GetMediaAnalysisJob, and ListMediaAnalysisJobs operations to run a bulk analysis of images with a Detect Moderation model.
* api-change:``marketplacecommerceanalytics``: The StartSupportDataExport operation has been deprecated as part of the Product Support Connection deprecation. As of December 2022, Product Support Connection is no longer supported.


2.13.28
=======

* api-change:``dynamodb``: Updating descriptions for several APIs.
* api-change:``gamesparks``: The gamesparks client has been removed following the deprecation of the service.
* api-change:``managedblockchain-query``: This release adds support for Ethereum Sepolia network
* api-change:``cloud9``: Update to imageId parameter behavior and dates updated.
* api-change:``ec2``: Amazon EC2 C7a instances, powered by 4th generation AMD EPYC processors, are ideal for high performance, compute-intensive workloads such as high performance computing. Amazon EC2 R7i instances are next-generation memory optimized and powered by custom 4th Generation Intel Xeon Scalable processors.
* api-change:``wisdom``: This release adds an max limit of 25 recommendation ids for NotifyRecommendationsReceived API.
* api-change:``verifiedpermissions``: Improving Amazon Verified Permissions Create experience
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``opensearch``: Added Cluster Administrative options for node restart, opensearch process restart and opensearch dashboard restart for Multi-AZ without standby domains
* api-change:``workspaces``: Documentation updates for WorkSpaces
* api-change:``omics``: This change enables customers to retrieve failure reasons with detailed status messages for their failed runs
* api-change:``neptunedata``: Doc changes to add IAM action mappings for the data actions.
* api-change:``servicecatalog``: Introduce support for EXTERNAL product and provisioning artifact type in CreateProduct and CreateProvisioningArtifact APIs.
* api-change:``quicksight``: This release adds the following: 1) Trino and Starburst Database Connectors 2) Custom total for tables and pivot tables 3) Enable restricted folders 4) Add rolling dates for time equality filters 5) Refine DataPathValue and introduce DataPathType 6) Add SeriesType to ReferenceLineDataConfiguration
* api-change:``rds``: This release adds support for upgrading the storage file system configuration on the DB instance using a blue/green deployment or a read replica.
* api-change:``kendra``: Changes for a new feature in Amazon Kendra's Query API to Collapse/Expand query results


2.13.27
=======

* api-change:``ecs``: Documentation only updates to address Amazon ECS tickets.
* api-change:``drs``: Updated exsiting API to allow AWS Elastic Disaster Recovery support of launching recovery into existing EC2 instances.
* api-change:``transfer``: Documentation updates for AWS Transfer Family
* api-change:``redshift-serverless``: Added support for managing credentials of serverless namespace admin using AWS Secrets Manager.
* api-change:``globalaccelerator``: Fixed error where ListCustomRoutingEndpointGroups did not have a paginator
* api-change:``mediapackagev2``: This release allows customers to manage MediaPackage v2 resource using CloudFormation.
* api-change:``sesv2``: This release provides enhanced visibility into your SES identity verification status. This will offer you more actionable insights, enabling you to promptly address any verification-related issues.
* api-change:``kafka``: AWS Managed Streaming for Kafka is launching MSK Replicator, a new feature that enables customers to reliably replicate data across Amazon MSK clusters in same or different AWS regions. You can now use SDK to create, list, describe, delete, update, and manage tags of MSK Replicators.
* api-change:``codepipeline``: Add retryMode ALL_ACTIONS to RetryStageExecution API that retries a failed stage starting from first action in the stage
* api-change:``guardduty``: Add domainWithSuffix finding field to dnsRequestAction
* api-change:``entityresolution``: This launch expands our matching techniques to include provider-based matching to help customer match, link, and enhance records with minimal data movement. With data service providers, we have removed the need for customers to build bespoke integrations,.
* api-change:``managedblockchain-query``: This release introduces two new APIs: GetAssetContract and ListAssetContracts. This release also adds support for Bitcoin Testnet.
* api-change:``cloudformation``: SDK and documentation updates for UpdateReplacePolicy
* api-change:``route53-recovery-control-config``: Adds permissions for GetResourcePolicy to support returning details about AWS Resource Access Manager resource policies for shared resources.
* api-change:``discovery``: This release introduces three new APIs: StartBatchDeleteConfigurationTask, DescribeBatchDeleteConfigurationTask, and BatchDeleteAgents.
* api-change:``redshift``: Added support for managing credentials of provisioned cluster admin using AWS Secrets Manager.
* api-change:``route53-recovery-cluster``: Adds Owner field to ListRoutingControls API.
* api-change:``opensearch``: This release allows customers to list and associate optional plugin packages with compatible Amazon OpenSearch Service clusters for enhanced functionality.
* api-change:``xray``: This releases enhances GetTraceSummaries API to support new TimeRangeType Service to query trace summaries by segment end time.


2.13.26
=======

* api-change:``ec2``: This release adds Ubuntu Pro as a supported platform for On-Demand Capacity Reservations and adds support for setting an Amazon Machine Image (AMI) to disabled state. Disabling the AMI makes it private if it was previously shared, and prevents new EC2 instance launches from it.
* api-change:``fsx``: After performing steps to repair the Active Directory configuration of a file system, use this action to initiate the process of attempting to recover to the file system.
* api-change:``machinelearning``: This release marks Password field as sensitive
* bugfix:``SSE-C``: Pass SSECustomer* arguments to CompleteMultipartUpload for upload operations
* api-change:``config``: Add enums for resource types supported by Config
* api-change:``auditmanager``: This release introduces a new limit to the awsAccounts parameter. When you create or update an assessment, there is now a limit of 200 AWS accounts that can be specified in the assessment scope.
* api-change:``ec2``: Documentation updates for Elastic Compute Cloud (EC2).
* api-change:``pricing``: Documentation updates for Price List
* api-change:``location``: This release adds endpoint updates for all AWS Location resource operations.
* api-change:``rds``: This release adds support for adding a dedicated log volume to open-source RDS instances.
* api-change:``customer-profiles``: Adds sensitive trait to various shapes in Customer Profiles Calculated Attribute API model.
* api-change:``controltower``: Added new EnabledControl resource details to ListEnabledControls API and added new GetEnabledControl API.
* api-change:``inspector2``: Add MacOs ec2 platform support
* enhancement:Python: Update bundled Python interpreter to 3.11.6
* api-change:``ivs-realtime``: Update GetParticipant to return additional metadata.
* api-change:``textract``: This release adds 9 new APIs for adapter and adapter version management, 3 new APIs for tagging, and updates AnalyzeDocument and StartDocumentAnalysis API parameters for using adapters.
* api-change:``transfer``: This release updates the max character limit of PreAuthenticationLoginBanner and PostAuthenticationLoginBanner to 4096 characters
* api-change:``glue``: Extending version control support to GitLab and Bitbucket from AWSGlue
* api-change:``sagemaker``: Amazon SageMaker Canvas adds KendraSettings and DirectDeploySettings support for CanvasAppSettings
* api-change:``lambda``: Adds support for Lambda functions to access Dual-Stack subnets over IPv6, via an opt-in flag in CreateFunction and UpdateFunctionConfiguration APIs
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``quicksight``: NullOption in FilterListConfiguration; Dataset schema/table max length increased; Support total placement for pivot table visual; Lenient mode relaxes the validation to create resources with definition; Data sources can be added to folders; Redshift data sources support IAM Role-based authentication
* api-change:``marketplace-catalog``: This release adds support for Document type as an alternative for stringified JSON for StartChangeSet, DescribeChangeSet and DescribeEntity APIs
* api-change:``transcribe``: This release is to enable m4a format to customers
* api-change:``rekognition``: Amazon Rekognition introduces support for Custom Moderation. This allows the enhancement of accuracy for detect moderation labels operations by creating custom adapters tuned on customer data.
* api-change:``workspaces``: Updated the CreateWorkspaces action documentation to clarify that the PCoIP protocol is only available for Windows bundles.
* api-change:``autoscaling``: Update the NotificationMetadata field to only allow visible ascii characters. Add paginators to DescribeInstanceRefreshes, DescribeLoadBalancers, and DescribeLoadBalancerTargetGroups


2.13.25
=======

* api-change:``securityhub``: Added new resource detail objects to ASFF, including resources for AwsEventsEventbus, AwsEventsEndpoint, AwsDmsEndpoint, AwsDmsReplicationTask, AwsDmsReplicationInstance, AwsRoute53HostedZone, and AwsMskCluster
* api-change:``sagemaker``: Adding support for AdditionalS3DataSource, a data source used for training or inference that is in addition to the input dataset or model data.
* api-change:``appconfig``: AWS AppConfig introduces KMS customer-managed key (CMK) encryption support for data saved to AppConfig's hosted configuration store.
* api-change:``mgn``: This release includes the following new APIs: ListConnectors, CreateConnector,  UpdateConnector, DeleteConnector and UpdateSourceServer to support the source action framework feature.
* api-change:``mediatailor``: Updates DescribeVodSource to include a list of ad break opportunities in the response
* api-change:``route53``: Add hostedzonetype filter to ListHostedZones API.
* api-change:``omics``: Add Etag Support for Omics Storage in ListReadSets and GetReadSetMetadata API
* api-change:``rds``: Updates Amazon RDS documentation for corrections and minor improvements.
* api-change:``datazone``: Initial release of Amazon DataZone
* api-change:``workspaces``: This release introduces Manage applications. This feature allows users to manage their WorkSpaces applications by associating or disassociating their WorkSpaces with applications. The DescribeWorkspaces API will now additionally return OperatingSystemName in its responses.
* api-change:``storagegateway``: Add SoftwareVersion to response of DescribeGatewayInformation.


2.13.24
=======

* api-change:``oam``: This release adds support for sharing AWS::ApplicationInsights::Application resources.
* api-change:``location``: Amazon Location Service adds support for bounding polygon queries. Additionally, the GeofenceCount field has been added to the DescribeGeofenceCollection API response.
* api-change:``sagemaker``: This release allows users to run Selective Execution in SageMaker Pipelines without SourcePipelineExecutionArn if selected steps do not have any dependent steps.
* api-change:``wellarchitected``: AWS Well-Architected now supports Review Templates that allows you to create templates with pre-filled answers for Well-Architected and Custom Lens best practices.
* api-change:``mediaconvert``: This release adds the ability to replace video frames without modifying the audio essence.
* api-change:``connect``: GetMetricDataV2 API: Update to include new metrics CONTACTS_RESOLVED_IN_X , AVG_HOLD_TIME_ALL_CONTACTS , AVG_RESOLUTION_TIME , ABANDONMENT_RATE , AGENT_NON_RESPONSE_WITHOUT_CUSTOMER_ABANDONS with added features: Interval Period, TimeZone, Negate MetricFilters, Extended date time range.


2.13.23
=======

* api-change:``ec2``: Adds support for Customer Managed Key encryption for Amazon Verified Access resources
* api-change:``iotfleetwise``: AWS IoT FleetWise now supports encryption through a customer managed AWS KMS key. The PutEncryptionConfiguration and GetEncryptionConfiguration APIs were added.
* api-change:``transfer``: Documentation updates for AWS Transfer Family
* api-change:``sso``: Fix FIPS Endpoints in aws-us-gov.
* api-change:``wafv2``: Correct and improve the documentation for the FieldToMatch option JA3 fingerprint.
* api-change:``bedrock-runtime``: Run Inference: Added support to run the inference on models.  Includes set of APIs for running inference in streaming and non-streaming mode.
* api-change:``firehose``: Features : Adding support for new data ingestion source to Kinesis Firehose - AWS Managed Services Kafka.
* api-change:``sts``: STS API updates for assumeRole
* api-change:``sagemaker-featurestore-runtime``: Feature Store supports read/write of records with collection type features.
* api-change:``iot``: Added support for IoT Rules Engine Kafka Action Headers
* api-change:``managedblockchain``: Remove Rinkeby as option from Ethereum APIs
* api-change:``bedrock-runtime``: Add model timeout exception for InvokeModelWithResponseStream API and update validator for invoke model identifier.
* api-change:``bedrock``: Model Invocation logging added to enable or disable logs in customer account. Model listing and description support added. Provisioned Throughput feature added. Custom model support added for creating custom models. Also includes list, and delete functions for custom model.
* api-change:``cognito-idp``: The UserPoolType Status field is no longer used.
* api-change:``textract``: This release adds new feature - Layout to Analyze Document API which can automatically extract layout elements such as titles, paragraphs, headers, section headers, lists, page numbers, footers, table areas, key-value areas and figure areas and order the elements as a human would read.
* api-change:``budgets``: Update DescribeBudgets and DescribeBudgetNotificationsForAccount MaxResults limit to 1000.
* api-change:``sagemaker``: Online store feature groups supports Standard and InMemory tier storage types for low latency storage for real-time data retrieval. The InMemory tier supports collection types List, Set, and Vector.
* api-change:``ec2``: Introducing Amazon EC2 R7iz instances with 3.9 GHz sustained all-core turbo frequency and deliver up to 20% better performance than previous generation z1d instances.
* api-change:``bedrock``: Provisioned throughput feature with Amazon and third-party base models, and update validators for model identifier and taggable resource ARNs.
* api-change:``rds``: Adds DefaultCertificateForNewLaunches field in the DescribeCertificates API response.


2.13.22
=======

* api-change:``emr-serverless``: This release adds support for application-wide default job configurations.
* api-change:``s3``: This release adds a new field COMPLETED to the ReplicationStatus Enum. You can now use this field to validate the replication status of S3 objects using the AWS SDK.
* api-change:``chime-sdk-media-pipelines``: Adds support for sending WebRTC audio to Amazon Kineses Video Streams.
* api-change:``braket``: This release adds support to view the device queue depth (the number of queued quantum tasks and hybrid jobs on a device) and queue position for a quantum task and hybrid job.
* api-change:``dynamodb``: Amazon DynamoDB now supports Incremental Export as an enhancement to the existing Export Table
* api-change:``dms``: new vendors for DMS CSF: MongoDB, MariaDB, DocumentDb and Redshift
* api-change:``wafv2``: You can now perform an exact match against the web request's JA3 fingerprint.
* api-change:``guardduty``: Add `EKS_CLUSTER_NAME` to filter and sort key.
* api-change:``ec2``: EC2 M2 Pro Mac instances are powered by Apple M2 Pro Mac Mini computers featuring 12 core CPU, 19 core GPU, 32 GiB of memory, and 16 core Apple Neural Engine and uniquely enabled by the AWS Nitro System through high-speed Thunderbolt connections.
* api-change:``lakeformation``: This release adds three new API support "CreateLakeFormationOptIn", "DeleteLakeFormationOptIn" and "ListLakeFormationOptIns", and also updates the corresponding documentation.
* api-change:``appintegrations``: The Amazon AppIntegrations service adds a set of APIs (in preview) to manage third party applications to be used in Amazon Connect agent workspace.
* api-change:``amplifyuibuilder``: Support for generating code that is compatible with future versions of amplify project dependencies.
* api-change:``codedeploy``: CodeDeploy now supports In-place and Blue/Green EC2 deployments with multiple Classic Load Balancers and multiple Target Groups.
* enhancement:compression: Adds support for the ``requestcompression`` operation trait.
* api-change:``ssm``: This release updates the enum values for ResourceType in SSM DescribeInstanceInformation input and ConnectionStatus in GetConnectionStatus output.
* api-change:``finspace-data``: Adding sensitive trait to attributes. Change max SessionDuration from 720 to 60. Correct "ApiAccess" attribute to "apiAccess" to maintain consistency between APIs.
* api-change:``efs``: Update efs command to latest version
* api-change:``connect``: This release updates a set of Amazon Connect APIs that provides the ability to integrate third party applications in the Amazon Connect agent workspace.
* api-change:``quicksight``: Added ability to tag users upon creation.
* api-change:``mediaconvert``: This release supports the creation of of audio-only tracks in CMAF output groups.
* api-change:``ec2``: The release includes AWS verified access to support FIPs compliance in North America regions
* api-change:``apprunner``: This release allows an App Runner customer to specify a custom source directory to run the build & start command. This change allows App Runner to support monorepo based repositories
* api-change:``pinpoint``: Update documentation for RemoveAttributes to more accurately reflect its behavior when attributes are deleted.


2.13.21
=======

* api-change:``logs``: Add ClientToken to QueryDefinition CFN Handler in CWL
* api-change:``sso-oidc``: Update FIPS endpoints in aws-us-gov.
* api-change:``apprunner``: This release adds improvements for managing App Runner auto scaling configuration resources. New APIs: UpdateDefaultAutoScalingConfiguration and ListServicesForAutoScalingConfiguration. Updated API: DeleteAutoScalingConfiguration.
* api-change:``codeartifact``: Add support for the Swift package format.
* enhancement:``codeartifact login``: Add Swift support for CodeArtifact login command
* api-change:``appconfig``: Enabling boto3 paginators for list APIs and adding documentation around ServiceQuotaExceededException errors
* api-change:``servicediscovery``: Adds a new DiscoverInstancesRevision API and also adds InstanceRevision field to the DiscoverInstances API response.
* api-change:``kinesisvideo``: Updated DescribeMediaStorageConfiguration, StartEdgeConfigurationUpdate, ImageGenerationConfiguration$SamplingInterval, and UpdateMediaStorageConfiguration to match AWS Docs.
* api-change:``s3``: Fix an issue where the SDK can fail to unmarshall response due to NumberFormatException


2.13.20
=======

* api-change:``discovery``: Add sensitive protection for customer information
* api-change:``macie2``: This release changes the default managedDataIdentifierSelector setting for new classification jobs to RECOMMENDED. By default, new classification jobs now use the recommended set of managed data identifiers.
* api-change:``workmail``: This release includes four new APIs UpdateUser, UpdateGroup, ListGroupsForEntity and DescribeEntity, along with RemoteUsers and some enhancements to existing APIs.
* api-change:``sagemaker``: This release adds support for one-time model monitoring schedules that are executed immediately without delay, explicit data analysis windows for model monitoring schedules and exclude features attributes to remove features from model monitor analysis.
* enhancement:``codeartifact login``: Include stderr output from underlying login tool when subprocess fails
* api-change:``ec2``: This release adds support for C7i, and R7a instance types.
* api-change:``outposts``: This release adds the InstanceFamilies field to the ListAssets response.


2.13.19
=======

* api-change:``lookoutequipment``: This release adds APIs for the new scheduled retraining feature.
* api-change:``connect``: New rule type (OnMetricDataUpdate) has been added
* api-change:``sagemaker``: This release introduces Skip Model Validation for Model Packages
* api-change:``ivs-realtime``: Doc only update that changes description for ParticipantToken.
* api-change:``appstream``: This release introduces multi-session fleets, allowing customers to provision more than one user session on a single fleet instance.
* api-change:``simspaceweaver``: Edited the introductory text for the API reference.
* api-change:``internetmonitor``: This release updates the Amazon CloudWatch Internet Monitor API domain name.
* api-change:``cloud9``: Update to include information on Ubuntu 18 deprecation.
* api-change:``xray``: Add StartTime field in GetTraceSummaries API response for each TraceSummary.
* api-change:``firehose``: DocumentIdOptions has been added for the Amazon OpenSearch destination.
* api-change:``appstream``: This release introduces app block builder, allowing customers to provision a resource to package applications into an app block
* api-change:``datasync``: Documentation-only updates for AWS DataSync.
* api-change:``entityresolution``: Changed "ResolutionTechniques" and "MappedInputFields" in workflow and schema mapping operations to be required fields.
* api-change:``drs``: Updated existing APIs and added new ones to support using AWS Elastic Disaster Recovery post-launch actions. Added support for new regions.
* api-change:``guardduty``: Add `managementType` field to ListCoverage API response.
* api-change:``cloudformation``: Documentation updates for AWS CloudFormation


2.13.18
=======

* api-change:``kendra``: Amazon Kendra now supports confidence score buckets for retrieved passage results using the Retrieve API.
* api-change:``events``: Update events command to latest version
* api-change:``sso-admin``: Content updates to IAM Identity Center API for China Regions.
* api-change:``quicksight``: This release launches new updates to QuickSight KPI visuals - support for sparklines, new templated layout and new targets for conditional formatting rules.
* api-change:``workspaces``: A new field "ErrorDetails" will be added to the output of "DescribeWorkspaceImages" API call. This field provides in-depth details about the error occurred during image import process. These details include the possible causes of the errors and troubleshooting information.
* api-change:``sagemaker``: Autopilot APIs will now support holiday featurization for Timeseries models. The models will now hold holiday metadata and should be able to accommodate holiday effect during inference.
* api-change:``fsx``: Amazon FSx documentation fixes
* api-change:``ec2``: This release adds support for restricting public sharing of AMIs through AMI Block Public Access
* api-change:``ecr``: This release will have ValidationException be thrown from ECR LifecyclePolicy APIs in regions LifecyclePolicy is not supported, this includes existing Amazon Dedicated Cloud (ADC) regions. This release will also change Tag: TagValue and Tag: TagKey to required.
* api-change:``medialive``: AWS Elemental Link now supports attaching a Link UHD device to a MediaConnect flow.


2.13.17
=======

* api-change:``simspaceweaver``: BucketName and ObjectKey are now required for the S3Location data type. BucketName is now required for the S3Destination data type.
* api-change:``neptunedata``: Minor changes to send unsigned requests to Neptune clusters
* api-change:``ec2``: This release adds 'outpost' location type to the DescribeInstanceTypeOfferings API, allowing customers that have been allowlisted for outpost to query their offerings in the API.
* api-change:``wafv2``: The targeted protection level of the Bot Control managed rule group now provides optional, machine-learning analysis of traffic statistics to detect some bot-related activity. You can enable or disable the machine learning functionality through the API.
* api-change:``appflow``: Adding OAuth2.0 support for servicenow connector.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``medialive``: Adds advanced Output Locking options for Epoch Locking: Custom Epoch and Jam Sync Time


2.13.16
=======

* api-change:``vpc-lattice``: This release adds Lambda event structure version config support for LAMBDA target groups. It also adds newline support for auth policies.
* api-change:``billingconductor``: This release adds support for line item filtering in for the custom line item resource.
* api-change:``cloud9``: Added support for Ubuntu 22.04 that was not picked up in a previous Trebuchet request. Doc-only update.
* api-change:``identitystore``: New Identity Store content for China Region launch
* api-change:``sagemaker``: SageMaker Neo now supports data input shape derivation for Pytorch 2.0  and XGBoost compilation job for cloud instance targets. You can skip DataInputConfig field during compilation job creation. You can also access derived information from model in DescribeCompilationJob response.
* api-change:``connect``: Amazon Connect adds the ability to read, create, update, delete, and list view resources, and adds the ability to read, create, delete, and list view versions.
* api-change:``rds``: Add support for feature integration with AWS Backup.
* api-change:``ecs``: Documentation only update for Amazon ECS.
* api-change:``ec2``: Introducing Amazon EC2 C7gd, M7gd, and R7gd Instances with up to 3.8 TB of local NVMe-based SSD block-level storage. These instances are powered by AWS Graviton3 processors, delivering up to 25% better performance over Graviton2-based instances.
* api-change:``chime-sdk-media-pipelines``: This release adds support for the Voice Analytics feature for customer-owned KVS streams as part of the Amazon Chime SDK call analytics.
* api-change:``compute-optimizer``: This release adds support to provide recommendations for G4dn and P3 instances that use NVIDIA GPUs.
* enhancement:Python: Update bundled Python interpreter to 3.11.5
* api-change:``neptunedata``: Removed the descriptive text in the introduction.
* api-change:``events``: Update events command to latest version


2.13.15
=======

* api-change:``connectparticipant``: Amazon Connect Participant Service adds the ability to get a view resource using a view token, which is provided in a participant message, with the release of the DescribeView API.
* api-change:``cleanrooms``: This release decouples member abilities in a collaboration. With this change, the member who can run queries no longer needs to be the same as the member who can receive results.
* api-change:``health``: Adds new API DescribeEntityAggregatesForOrganization that retrieves entity aggregates across your organization. Also adds support for resource status filtering in DescribeAffectedEntitiesForOrganization, resource status aggregates in the DescribeEntityAggregates response, and new resource statuses.
* api-change:``neptunedata``: Allows customers to execute data plane actions like bulk loading graphs, issuing graph queries using Gremlin and openCypher directly from the SDK.
* api-change:``cloudhsm``: Deprecating CloudHSM Classic API Service.
* api-change:``pca-connector-ad``: The Connector for AD allows you to use a fully-managed AWS Private CA as a drop-in replacement for your self-managed enterprise CAs without local agents or proxy servers. Enterprises that use AD to manage Windows environments can reduce their private certificate authority (CA) costs and complexity.
* api-change:``network-firewall``: Network Firewall increasing pagination token string length
* api-change:``customer-profiles``: Adds sensitive trait to various shapes in Customer Profiles API model.
* api-change:``auditmanager``: This release marks some assessment metadata as sensitive. We added a sensitive trait to the following attributes: assessmentName, emailAddress, scope, createdBy, lastUpdatedBy, and userName.
* api-change:``grafana``: Marking SAML RoleValues attribute as sensitive and updating VpcConfiguration attributes to match documentation.
* api-change:``ivs``: Updated "type" description for CreateChannel, UpdateChannel, Channel, and ChannelSummary.
* api-change:``apprunner``: App Runner adds support for Bitbucket. You can now create App Runner connection that connects to your Bitbucket repositories and deploy App Runner service with the source code stored in a Bitbucket repository.
* api-change:``datasync``: AWS DataSync introduces Task Reports, a new feature that provides detailed reports of data transfer operations for each task execution.
* api-change:``chime-sdk-media-pipelines``: This release adds support for feature Voice Enhancement for Call Recording as part of Amazon Chime SDK call analytics.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``kafkaconnect``: Minor model changes for Kafka Connect as well as endpoint updates.
* api-change:``ecs``: This release adds support for an account-level setting that you can use to configure the number of days for AWS Fargate task retirement.
* api-change:``connectcampaigns``: Amazon Connect outbound campaigns has launched agentless dialing mode which enables customers to make automated outbound calls without agent engagement. This release updates three of the campaign management API's to support the new agentless dialing mode and the new dialing capacity field.
* api-change:``payment-cryptography-data``: Make KeyCheckValue field optional when using asymmetric keys as Key Check Values typically only apply to symmetric keys
* api-change:``appflow``: Add SAP source connector parallel and pagination feature
* api-change:``sagemaker``: Amazon SageMaker Canvas adds IdentityProviderOAuthSettings support for CanvasAppSettings


2.13.14
=======

* api-change:``omics``: Add RetentionMode support for Runs.
* api-change:``securitylake``: Remove incorrect regex enforcement on pagination tokens.
* api-change:``workspaces-web``: WorkSpaces Web now enables Admins to configure which cookies are synchronized from an end-user's local browser to the in-session browser. In conjunction with a browser extension, this feature enables enhanced Single-Sign On capability by reducing the number of times an end-user has to authenticate.
* api-change:``sesv2``: Adds support for the new Export and Message Insights features: create, get, list and cancel export jobs; get message insights.
* api-change:``service-quotas``: Service Quotas now supports viewing the applied quota value and requesting a quota increase for a specific resource in an AWS account.
* api-change:``backup``: Add support for customizing time zone for backup window in backup plan rules.
* api-change:``detective``: Added protections to interacting with fields containing customer information.
* api-change:``cloudtrail``: Add ThrottlingException with error code 429 to handle CloudTrail Delegated Admin request rate exceeded on organization resources.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``fsx``: Documentation updates for project quotas.
* api-change:``organizations``: Documentation updates for permissions and links.
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate licensing optimization recommendations for sql server running on EC2 instances.
* api-change:``cognito-idp``: Added API example requests and responses for several operations. Fixed the validation regex for user pools Identity Provider name.


2.13.13
=======

* api-change:``mediatailor``: Adds new source location AUTODETECT_SIGV4 access type.
* api-change:``polly``: Amazon Polly adds 1 new voice - Zayd (ar-AE)
* api-change:``ec2``: Marking fields as sensitive on BundleTask and GetPasswordData
* api-change:``mediaconvert``: This release includes additional audio channel tags in Quicktime outputs, support for film grain synthesis for AV1 outputs, ability to create audio-only FLAC outputs, and ability to specify Amazon S3 destination storage class.
* api-change:``s3control``: Updates to endpoint ruleset tests to address Smithy validation issues and standardize the capitalization of DualStack.
* api-change:``glue``: Added API attributes that help in the monitoring of sessions.
* api-change:``rds``: This release updates the supported versions for Percona XtraBackup in Aurora MySQL.
* api-change:``ec2``: Amazon EC2 M7a instances, powered by 4th generation AMD EPYC processors, deliver up to 50% higher performance compared to M6a instances. Amazon EC2 Hpc7a instances, powered by 4th Gen AMD EPYC processors, deliver up to 2.5x better performance compared to Amazon EC2 Hpc6a instances.
* api-change:``medialive``: MediaLive now supports passthrough of KLV data to a HLS output group with a TS container. MediaLive now supports setting an attenuation mode for AC3 audio when the coding mode is 3/2 LFE. MediaLive now supports specifying whether to include filler NAL units in RTMP output group settings.
* api-change:``quicksight``: Excel support in Snapshot Export APIs. Removed Required trait for some insight Computations. Namespace-shared Folders support. Global Filters support. Table pin Column support.
* api-change:``verifiedpermissions``: Documentation updates for Amazon Verified Permissions.
* api-change:``apigateway``: This release adds RootResourceId to GetRestApi response.


2.13.12
=======

* api-change:``securityhub``: Added Inspector Lambda code Vulnerability section to ASFF, including GeneratorDetails, EpssScore, ExploitAvailable, and CodeVulnerabilities.
* api-change:``verifiedpermissions``: Documentation updates for Amazon Verified Permissions. Increases max results per page for ListPolicyStores, ListPolicies, and ListPolicyTemplates APIs from 20 to 50.
* api-change:``globalaccelerator``: Global Accelerator now supports Client Ip Preservation for Network Load Balancer endpoints.
* api-change:``ec2``: The DeleteKeyPair API has been updated to return the keyPairId when an existing key pair is deleted.
* api-change:``cloud9``: Doc only update to add Ubuntu 22.04 as an Image ID option for Cloud9
* api-change:``rds``: Adding support for RDS Aurora Global Database Unplanned Failover
* api-change:``route53domains``: Fixed typos in description fields
* api-change:``ce``: This release adds the LastUpdatedDate and LastUsedDate timestamps to help you manage your cost allocation tags.
* api-change:``codecommit``: Add new ListFileCommitHistory operation to retrieve commits which introduced changes to a specific file.
* api-change:``finspace``: Allow customers to manage outbound traffic from their Kx Environment when attaching a transit gateway by providing network acl entries. Allow the customer to choose how they want to update the databases on a cluster allowing updates to possibly be faster than usual.
* api-change:``rds``: Adding parameters to CreateCustomDbEngineVersion reserved for future use.


2.13.11
=======

* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``gamelift``: Amazon GameLift updates its instance types support.
* api-change:``ec2``: Adds support for SubnetConfigurations to allow users to select their own IPv4 and IPv6 addresses for Interface VPC endpoints
* api-change:``lexv2-models``: Update lexv2-models command to latest version


2.13.10
=======

* api-change:``ec2``: Amazon EC2 P5 instances, powered by the latest NVIDIA H100 Tensor Core GPUs, deliver the highest performance in EC2 for deep learning (DL) and HPC applications. M7i-flex and M7i instances are next-generation general purpose instances powered by custom 4th Generation Intel Xeon Scalable processors.
* api-change:``ses``: Update ses command to latest version
* api-change:``transfer``: Documentation updates for AWS Transfer Family
* api-change:``glue``: AWS Glue Crawlers can now accept SerDe overrides from a custom csv classifier. The two SerDe options are LazySimpleSerDe and OpenCSVSerDe. In case, the user wants crawler to do the selection, "None" can be selected for this purpose.
* api-change:``swf``: This release adds new API parameters to override workflow task list for workflow executions.
* api-change:``omics``: This release provides support for annotation store versioning and cross account sharing for Omics Analytics
* api-change:``amplifybackend``: Adds sensitive trait to required input shapes.
* api-change:``mediapackage``: Fix SDK logging of certain fields.
* api-change:``ec2``: Documentation updates for Elastic Compute Cloud (EC2).
* api-change:``quicksight``: New Authentication method for Account subscription - IAM Identity Center. Hierarchy layout support, default column width support and related style properties for pivot table visuals. Non-additive topic field aggregations for Topic API
* api-change:``pi``: AWS Performance Insights for Amazon RDS is launching Performance Analysis On Demand, a new feature that allows you to analyze database performance metrics and find out the performance issues. You can now use SDK to create, list, get, delete, and manage tags of performance analysis reports.
* api-change:``chime-sdk-meetings``: Updated API documentation to include additional exceptions.
* api-change:``config``: Updated ResourceType enum with new resource types onboarded by AWS Config in July 2023.
* api-change:``sagemaker``: SageMaker Inference Recommender now provides SupportedResponseMIMETypes from DescribeInferenceRecommendationsJob response
* api-change:``route53domains``: Provide explanation if CheckDomainTransferability return false. Provide requestId if a request is already submitted.  Add sensitive protection for customer information


2.13.9
======

* api-change:``globalaccelerator``: Documentation update for dualstack EC2 endpoint support
* api-change:``guardduty``: Added autoEnable ALL to UpdateOrganizationConfiguration and DescribeOrganizationConfiguration APIs.
* api-change:``connect``: This release adds APIs to provision agents that are global / available in multiple AWS regions and distribute them across these regions by percentage.
* api-change:``fsx``: For FSx for Lustre, add new data repository task type, RELEASE_DATA_FROM_FILESYSTEM, to release files that have been archived to S3. For FSx for Windows, enable support for configuring and updating SSD IOPS, and for updating storage type. For FSx for OpenZFS, add new deployment type, MULTI_AZ_1.
* api-change:``chime-sdk-voice``: Updating CreatePhoneNumberOrder, UpdatePhoneNumber and BatchUpdatePhoneNumbers APIs, adding phone number name
* api-change:``cloudtrail``: Documentation updates for CloudTrail.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``sagemaker``: This release adds support for cross account access for SageMaker Model Cards through AWS RAM.
* api-change:``secretsmanager``: Add additional InvalidRequestException to list of possible exceptions for ListSecret.
* api-change:``omics``: This release adds instanceType to GetRunTask & ListRunTasks responses.
* api-change:``transfer``: Documentation updates for AW Transfer Family


2.13.8
======

* api-change:``detective``: Updated the email validation regex to be in line with the TLD name specifications.
* api-change:``datasync``: Display cloud storage used capacity at a cluster level.
* api-change:``kinesisvideo``: This release enables minimum of Images SamplingInterval to be as low as 200 milliseconds in Kinesis Video Stream Image feature.
* api-change:``acm-pca``: Documentation correction for AWS Private CA
* api-change:``ivs-realtime``: Add QUOTA_EXCEEDED and PUBLISHER_NOT_FOUND to EventErrorCode for stage health events.
* api-change:``rekognition``: This release adds code snippets for Amazon Rekognition Custom Labels.
* api-change:``ecs``: This is a documentation update to address various tickets.
* api-change:``servicecatalog``: Introduce support for HashiCorp Terraform Cloud in Service Catalog by addying TERRAFORM_CLOUD product type in CreateProduct and CreateProvisioningArtifact API.
* api-change:``kinesis-video-archived-media``: This release enables minimum of Images SamplingInterval to be as low as 200 milliseconds in Kinesis Video Stream Image feature.
* api-change:``connect``: Added a new API UpdateRoutingProfileAgentAvailabilityTimer to update agent availability timer of a routing profile.
* api-change:``sagemaker``: Including DataCaptureConfig key in the Amazon Sagemaker Search's transform job object
* api-change:``backup``: This release introduces a new logically air-gapped vault (Preview) in AWS Backup that stores immutable backup copies, which are locked by default and isolated with encryption using AWS owned keys. Logically air-gapped vault (Preview) allows secure recovery of application data across accounts.
* api-change:``elasticache``: Added support for cluster mode in online migration and test migration API


2.13.7
======

* api-change:``ec2``: This release adds new parameter isPrimaryIPv6 to  allow assigning an IPv6 address as a primary IPv6 address to a network interface which cannot be changed to give equivalent functionality available for network interfaces with primary IPv4 address.
* api-change:``sagemaker``: Amazon SageMaker now supports running training jobs on p5.48xlarge instance types.
* api-change:``glue``: This release includes additional Glue Streaming KAKFA SASL property types.
* api-change:``dms``: The release makes public API for DMS Schema Conversion feature.
* api-change:``cloud9``: Updated the deprecation date for Amazon Linux. Doc only update.
* api-change:``resiliencehub``: Drift Detection capability added when applications policy has moved from a meet to breach state. Customers will be able to exclude operational recommendations and receive credit in their resilience score. Customers can now add ARH permissions to an existing or new role.
* api-change:``cognito-idp``: New feature that logs Cognito user pool error messages to CloudWatch logs.
* api-change:``budgets``: As part of CAE tagging integration we need to update our budget names regex filter to prevent customers from using "/action/" in their budget names.
* api-change:``sagemaker``: SageMaker Inference Recommender introduces a new API GetScalingConfigurationRecommendation to recommend auto scaling policies based on completed Inference Recommender jobs.
* api-change:``autoscaling``: Documentation changes related to Amazon EC2 Auto Scaling APIs.


2.13.6
======

* api-change:``lookoutequipment``: This release includes new import resource, model versioning and resource policy features.
* api-change:``cloudformation``: This SDK release is for the feature launch of AWS CloudFormation RetainExceptOnCreate. It adds a new parameter retainExceptOnCreate in the following APIs: CreateStack, UpdateStack, RollbackStack, ExecuteChangeSet.
* api-change:``dms``: Adding new API describe-engine-versions which provides information about the lifecycle of a replication instance's version.
* api-change:``connect``: This release adds support for new number types.
* api-change:``cleanrooms``: This release introduces custom SQL queries - an expanded set of SQL you can run. This release adds analysis templates, a new resource for storing pre-defined custom SQL queries ahead of time. This release also adds the Custom analysis rule, which lets you approve analysis templates for querying.
* api-change:``sagemaker``: Add Stairs TrafficPattern and FlatInvocations to RecommendationJobStoppingConditions
* api-change:``route53``: Amazon Route 53 now supports the Israel (Tel Aviv) Region (il-central-1) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``pinpoint``: Added support for sending push notifications using the FCM v1 API with json credentials. Amazon Pinpoint customers can now deliver messages to Android devices using both FCM v1 API and the legacy FCM/GCM API
* api-change:``rds``: This release adds support for Aurora MySQL local write forwarding, which allows for forwarding of write operations from reader DB instances to the writer DB instance.
* api-change:``codestar-connections``: New integration with the Gitlab provider type.
* api-change:``amplifyuibuilder``: Amplify Studio releases GraphQL support for codegen job action.
* api-change:``polly``: Amazon Polly adds new French Belgian voice - Isabelle. Isabelle is available as Neural voice only.
* api-change:``inspector2``: This release adds 1 new API: BatchGetFindingDetails to retrieve enhanced vulnerability intelligence details for findings.
* api-change:``batch``: This release adds support for price capacity optimized allocation strategy for Spot Instances.
* api-change:``internetmonitor``: This release adds a new feature for Amazon CloudWatch Internet Monitor that enables customers to set custom thresholds, for performance and availability drops, for impact limited to a single city-network to trigger creation of a health event.
* api-change:``scheduler``: This release introduces automatic deletion of schedules in EventBridge Scheduler. If configured, EventBridge Scheduler automatically deletes a schedule after the schedule has completed its last invocation.
* api-change:``medialive``: AWS Elemental Link devices now report their Availability Zone. Link devices now support the ability to change their Availability Zone.
* api-change:``autoscaling``: You can now configure an instance refresh to set its status to 'failed' when it detects that a specified CloudWatch alarm has gone into the ALARM state. You can also choose to roll back the instance refresh automatically when the alarm threshold is met.
* api-change:``cloudfront``: Add a new JavaScript runtime version for CloudFront Functions.
* api-change:``kafka``: Amazon MSK has introduced new versions of ListClusterOperations and DescribeClusterOperation APIs. These v2 APIs provide information and insights into the ongoing operations of both MSK Provisioned and MSK Serverless clusters.
* api-change:``rds``: Added support for deleted clusters PiTR.
* api-change:``drs``: Add support for in-aws right sizing
* api-change:``omics``: Add CreationType filter for ListReadSets
* api-change:``application-insights``: This release enable customer to add/remove/update more than one workload for a component


2.13.5
======

* api-change:``glue``: Release Glue Studio Snowflake Connector Node for SDK/CLI
* api-change:``sagemaker``: Expose ProfilerConfig attribute in SageMaker Search API response.
* api-change:``omics``: The service is renaming as a part of AWS Health.
* api-change:``eks``: Add multiple customer error code to handle customer caused failure when managing EKS node groups
* api-change:``managedblockchain-query``: Amazon Managed Blockchain (AMB) Query provides serverless access to standardized, multi-blockchain datasets with developer-friendly APIs.
* api-change:``entityresolution``: AWS Entity Resolution can effectively match a source record from a customer relationship management (CRM) system with a source record from a marketing system containing campaign information.
* api-change:``opensearchserverless``: This release adds new collection type VectorSearch.
* api-change:``autoscaling``: This release updates validation for instance types used in the AllowedInstanceTypes and ExcludedInstanceTypes parameters of the InstanceRequirements property of a MixedInstancesPolicy.
* api-change:``polly``: Amazon Polly adds 1 new voice - Lisa (nl-BE)
* api-change:``mediaconvert``: This release includes general updates to user documentation.
* api-change:``sqs``: Documentation changes related to SQS APIs.
* api-change:``healthlake``: Updating the HealthLake service documentation.
* api-change:``ebs``: SDK and documentation updates for Amazon Elastic Block Store API
* api-change:``ec2``: SDK and documentation updates for Amazon Elastic Block Store APIs
* api-change:``cloudcontrol``: Updates the documentation for CreateResource.
* api-change:``route53``: Update that corrects the documents for received feedback.


2.13.4
======

* api-change:``cloudformation``: This release supports filtering by DRIFT_STATUS for existing API ListStackInstances and adds support for a new API ListStackInstanceResourceDrifts. Customers can now view resource drift information from their StackSet management accounts.
* api-change:``apigatewayv2``: Documentation updates for Amazon API Gateway.
* api-change:``emr-serverless``: This release adds support for publishing application logs to CloudWatch.
* api-change:``ec2``: This release adds an instance's peak and baseline network bandwidth as well as the memory sizes of an instance's inference accelerators to DescribeInstanceTypes.
* api-change:``glue``: This release adds support for AWS Glue Crawler with Apache Hudi Tables, allowing Crawlers to discover Hudi Tables in S3 and register them in Glue Data Catalog for query engines to query against.
* api-change:``dynamodb``: Documentation updates for DynamoDB
* api-change:``securityhub``: Add support for CONTAINS and NOT_CONTAINS comparison operators for Automation Rules string filters and map filters
* api-change:``ec2``: Add "disabled" enum value to SpotInstanceState.
* api-change:``sagemaker``: Mark ContentColumn and TargetLabelColumn as required Targets in TextClassificationJobConfig in CreateAutoMLJobV2API
* api-change:``lambda``: Add Python 3.11 (python3.11) support to AWS Lambda
* api-change:``datasync``: AWS DataSync now supports Microsoft Azure Blob Storage locations.
* api-change:``transfer``: This release adds support for SFTP Connectors.
* api-change:``chime-sdk-media-pipelines``: AWS Media Pipeline compositing enhancement and Media Insights Pipeline auto language identification.
* api-change:``quicksight``: This release launches new Snapshot APIs for CSV and PDF exports, adds support for info icon for filters and parameters in Exploration APIs, adds modeled exception to the DeleteAccountCustomization API, and introduces AttributeAggregationFunction's ability to add UNIQUE_VALUE aggregation in tooltips.
* api-change:``billingconductor``: Added support for Auto-Assocate Billing Groups for CreateBillingGroup, UpdateBillingGroup, and ListBillingGroups.
* api-change:``customer-profiles``: Amazon Connect Customer Profiles now supports rule-based resolution to match and merge similar profiles into unified profiles, helping companies deliver faster and more personalized customer service by providing access to relevant customer information for agents and automated experiences.
* api-change:``rds``: Adds support for the DBSystemID parameter of CreateDBInstance to RDS Custom for Oracle.
* api-change:``mediaconvert``: This release includes improvements to Preserve 444 handling, compatibility of HEVC sources without frame rates, and general improvements to MP4 outputs.
* api-change:``sts``: API updates for the AWS Security Token Service
* api-change:``workspaces``: Fixed VolumeEncryptionKey descriptions
* api-change:``ce``: This release introduces the new API 'GetSavingsPlanPurchaseRecommendationDetails', which retrieves the details for a Savings Plan recommendation. It also updates the existing API 'GetSavingsPlansPurchaseRecommendation' to include the recommendation detail ID.
* api-change:``wisdom``: This release added two new data types: AssistantIntegrationConfiguration, and SessionIntegrationConfiguration to support Wisdom integration with Amazon Connect Chat
* api-change:``rds``: This release adds support for monitoring storage optimization progress on the DescribeDBInstances API.
* api-change:``glue``: Added support for Data Preparation Recipe node in Glue Studio jobs


2.13.3
======

* api-change:``savingsplans``: Savings Plans endpoints update
* api-change:``connectcases``: This release adds the ability to assign a case to a queue or user.
* api-change:``transcribe``: Added API argument --toxicity-detection to startTranscriptionJob API, which allows users to view toxicity scores of submitted audio.
* api-change:``grafana``: Amazon Managed Grafana now supports grafanaVersion update for existing workspaces with UpdateWorkspaceConfiguration API. DescribeWorkspaceConfiguration API additionally returns grafanaVersion. A new ListVersions API lists available versions or, if given a workspaceId, the versions it can upgrade to.
* api-change:``ec2``: Amazon EC2 documentation updates.
* api-change:``securitylake``: Adding support for Tags on Create and Resource Tagging API.
* api-change:``codecatalyst``: This release adds support for updating and deleting spaces and projects in Amazon CodeCatalyst. It also adds support for creating, getting, and deleting source repositories in CodeCatalyst projects.
* api-change:``route53resolver``: This release adds support for Route 53 On Outposts, a new feature that allows customers to run Route 53 Resolver and Resolver endpoints locally on their Outposts.
* api-change:``wafv2``: Added the URI path to the custom aggregation keys that you can specify for a rate-based rule.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``cloudformation``: SDK and documentation updates for GetTemplateSummary API (unrecognized resources)
* api-change:``ram``: This release adds support for securely sharing with AWS service principals.
* api-change:``ssm-sap``: Added support for SAP Hana High Availability discovery (primary and secondary nodes) and Backint agent installation with SSM for SAP.
* api-change:``sagemaker``: Cross account support for SageMaker Feature Store
* api-change:``medical-imaging``: General Availability (GA) release of AWS Health Imaging, enabling customers to store, transform, and analyze medical imaging data at petabyte-scale.
* api-change:``s3``: Improve performance of S3 clients by simplifying and optimizing endpoint resolution.
* api-change:``sagemaker-featurestore-runtime``: Cross account support for SageMaker Feature Store


2.13.2
======

* api-change:``glue``: Adding new supported permission type flags to get-unfiltered endpoints that callers may pass to indicate support for enforcing Lake Formation fine-grained access control on nested column attributes.
* api-change:``es``: Regex Validation on the ElasticSearch Engine Version attribute
* bugfix:``ec2-instance-connect ssh``: Fix runtime error when HTTP_PROXY environment variable is set and NO_PROXY is not set for eice connection type `#8023 <https://github.com/aws/aws-cli/issues/8023>`__
* api-change:``connect``: GetMetricDataV2 API: Update to include Contact Lens Conversational Analytics Metrics
* api-change:``snowball``: Adds support for RACK_5U_C. This is the first AWS Snow Family device designed to meet U.S. Military Ruggedization Standards (MIL-STD-810H) with 208 vCPU device in a portable, compact 5U, half-rack width form-factor.
* api-change:``m2``: Allows UpdateEnvironment to update the environment to 0 host capacity. New GetSignedBluinsightsUrl API
* api-change:``translate``: Added DOCX word document support to TranslateDocument API
* api-change:``codeguru-security``: Documentation updates for CodeGuru Security.
* api-change:``lakeformation``: Adds supports for ReadOnlyAdmins and AllowFullTableExternalDataAccess. Adds NESTED_PERMISSION and NESTED_CELL_PERMISSION to SUPPORTED_PERMISSION_TYPES enum. Adds CREATE_LF_TAG on catalog resource and ALTER, DROP, and GRANT_WITH_LF_TAG_EXPRESSION on LF Tag resource.
* api-change:``ec2``: Add Nitro TPM support on DescribeInstanceTypes
* api-change:``ivs``: This release provides the flexibility to configure what renditions or thumbnail qualities to record when creating recording configuration.
* api-change:``docdb``: Added major version upgrade option in ModifyDBCluster API
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``codeartifact``: Doc only update for AWS CodeArtifact


2.13.1
======

* api-change:``cognito-idp``: API model updated in Amazon Cognito
* api-change:``cognito-idp``: API model updated in Amazon Cognito
* api-change:``dms``: Releasing DMS Serverless. Adding support for PostgreSQL 15.x as source and target endpoint. Adding support for DocDB Elastic Clusters with sharded collections, PostgreSQL datatype mapping customization and disabling hostname validation of the certificate authority in Kafka endpoint settings
* api-change:``proton``: This release adds support for deployment history for Proton provisioned resources
* api-change:``medialive``: This release enables the use of Thumbnails in AWS Elemental MediaLive.
* api-change:``sagemaker``: Amazon SageMaker Canvas adds WorkspeceSettings support for CanvasAppSettings
* api-change:``mediatailor``: The AWS Elemental MediaTailor SDK for Channel Assembly has added support for EXT-X-CUE-OUT and EXT-X-CUE-IN tags to specify ad breaks in HLS outputs, including support for EXT-OATCLS, EXT-X-ASSET, and EXT-X-CUE-OUT-CONT accessory tags.
* api-change:``logs``: Add CMK encryption support for CloudWatch Logs Insights query result data
* api-change:``dms``: Enhanced PostgreSQL target endpoint settings for providing Babelfish support.
* api-change:``mediatailor``: Adds categories to MediaTailor channel assembly alerts
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``connect``: Add support for deleting Queues and Routing Profiles.
* api-change:``personalize``: This release provides ability to customers to change schema associated with their datasets in Amazon Personalize
* api-change:``datasync``: Added LunCount to the response object of DescribeStorageSystemResourcesResponse, LunCount represents the number of LUNs on a storage system resource.
* api-change:``ec2``: This release adds support for the C7gn and Hpc7g instances. C7gn instances are powered by AWS Graviton3 processors and the fifth-generation AWS Nitro Cards. Hpc7g instances are powered by AWS Graviton 3E processors and provide up to 200 Gbps network bandwidth.
* api-change:``s3``: S3 Inventory now supports Object Access Control List and Object Owner as available object metadata fields in inventory reports.
* api-change:``fsx``: Amazon FSx for NetApp ONTAP now supports SnapLock, an ONTAP feature that enables you to protect your files in a volume by transitioning them to a write once, read many (WORM) state.
* api-change:``glue``: This release enables customers to create new Apache Iceberg tables and associated metadata in Amazon S3 by using native AWS Glue CreateTable operation.


2.13.0
======

* feature:configuration: Configure the endpoint URL in the shared configuration file or via an environment variable for a specific AWS service or all AWS services.
* api-change:``ec2``: Add Nitro Enclaves support on DescribeInstanceTypes
* api-change:``connect``: GetMetricDataV2 API: Channels filters do not count towards overall limitation of 100 filter values.
* api-change:``comprehendmedical``: Update to Amazon Comprehend Medical documentation.
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``mgn``: This release introduces the Global view feature and new Replication state APIs.
* api-change:``quicksight``: This release includes below three changes: small multiples axes improvement, field based coloring, removed required trait from Aggregation function for TopBottomFilter.
* api-change:``rds``: Updates Amazon RDS documentation for creating DB instances and creating Aurora global clusters.
* api-change:``kms``: Added Dry Run Feature to cryptographic and cross-account mutating KMS APIs (14 in all). This feature allows users to test their permissions and parameters before making the actual API call.
* api-change:``outposts``: Added paginator support to several APIs. Added the ISOLATED enum value to AssetState.
* api-change:``location``: This release adds support for authenticating with Amazon Location Service's Places & Routes APIs with an API Key. Also, with this release developers can publish tracked device position updates to Amazon EventBridge.


2.12.7
======

* api-change:``sagemaker``: This release adds support for rolling deployment in SageMaker Inference.
* api-change:``amp``: AWS SDK service model  generation tool version upgrade.
* api-change:``ivs``: Corrects the HTTP response code in the generated docs for PutMetadata and DeleteRecordingConfiguration APIs.
* api-change:``mediaconvert``: This release includes improved color handling of overlays and general updates to user documentation.
* api-change:``sagemaker``: SageMaker Inference Recommender now accepts new fields SupportedEndpointType and ServerlessConfiguration to support serverless endpoints.
* api-change:``ecs``: Added new field  "credentialspecs" to the ecs task definition to support gMSA of windows/linux in both domainless and domain-joined mode
* api-change:``batch``: This feature allows customers to use AWS Batch with Linux with ARM64 CPU Architecture and X86_64 CPU Architecture with Windows OS on Fargate Platform.
* api-change:``transfer``: Add outbound Basic authentication support to AS2 connectors
* api-change:``verifiedpermissions``: This release corrects several broken links in the documentation.


2.12.6
======

* api-change:``gamelift``: Amazon GameLift now supports game builds that use the Amazon Linux 2023 (AL2023) operating system.
* api-change:``cleanrooms``: This release adds support for the OR operator in RSQL join match conditions and the ability to control which operators (AND, OR) are allowed in a join match condition.
* api-change:``dynamodb``: This release adds ReturnValuesOnConditionCheckFailure parameter to PutItem, UpdateItem, DeleteItem, ExecuteStatement, BatchExecuteStatement and ExecuteTransaction APIs. When set to ALL_OLD,  API returns a copy of the item as it was when a conditional write failed
* api-change:``sagemaker``: Adding support for timeseries forecasting in the CreateAutoMLJobV2 API.
* api-change:``chime``: The Amazon Chime SDK APIs in the Chime namespace are no longer supported.  Customers should use APIs in the dedicated Amazon Chime SDK namespaces: ChimeSDKIdentity, ChimeSDKMediaPipelines, ChimeSDKMeetings, ChimeSDKMessaging, and ChimeSDKVoice.
* api-change:``appstream``: This release introduces app block builder, allowing customers to provision a resource to package applications into an app block
* api-change:``glue``: This release adds support for AWS Glue Crawler with Iceberg Tables, allowing Crawlers to discover Iceberg Tables in S3 and register them in Glue Data Catalog for query engines to query against.


2.12.5
======

* api-change:``rds``: Amazon Relational Database Service (RDS) now supports joining a RDS for SQL Server instance to a self-managed Active Directory.
* api-change:``lambda``: Surface ResourceConflictException in DeleteEventSourceMapping
* api-change:``omics``: Add Common Workflow Language (CWL) as a supported language for Omics workflows
* api-change:``s3``: The S3 LISTObjects, ListObjectsV2 and ListObjectVersions API now supports a new optional header x-amz-optional-object-attributes. If header contains RestoreStatus as the value, then S3 will include Glacier restore status i.e. isRestoreInProgress and RestoreExpiryDate in List response.
* api-change:``kinesisanalyticsv2``: Support for new runtime environment in Kinesis Data Analytics Studio: Zeppelin-0.10, Apache Flink-1.15
* api-change:``sagemaker``: This release adds support for Model Cards Model Registry integration.
* api-change:``internetmonitor``: This release adds a new feature for Amazon CloudWatch Internet Monitor that enables customers to set custom thresholds, for performance and availability drops, for triggering when to create a health event.


2.12.4
======

* api-change:``iam``: Support for a new API "GetMFADevice" to present MFA device metadata such as device certifications
* api-change:``sagemaker-featurestore-runtime``: Introducing TTL for online store records for feature groups.
* api-change:``kinesisvideo``: General Availability (GA) release of Kinesis Video Streams at Edge, enabling customers to provide a configuration for the Kinesis Video Streams EdgeAgent running on an on-premise IoT device. Customers can now locally record from cameras and stream videos to the cloud on a configured schedule.
* api-change:``appflow``: This release adds support to bypass SSO with the SAPOData connector when connecting to an SAP instance.
* api-change:``pinpoint``: Added time zone estimation support for journeys
* api-change:``glue``: Timestamp Starting Position For Kinesis and Kafka Data Sources in a Glue Streaming Job
* api-change:``verifiedpermissions``: This update fixes several broken links to the Cedar documentation.
* api-change:``macie2``: This release adds support for configuring new classification jobs to use the set of managed data identifiers that we recommend for jobs. For the managed data identifier selection type (managedDataIdentifierSelector), specify RECOMMENDED.
* api-change:``ivs``: IVS customers can now revoke the viewer session associated with an auth token, to prevent and stop playback using that token.
* api-change:``devops-guru``: This release adds support for encryption via customer managed keys.
* api-change:``appfabric``: Initial release of AWS AppFabric for connecting SaaS applications for better productivity and security.
* api-change:``connect``: This release provides a way to search for existing tags within an instance. Before tagging a resource, ensure consistency by searching for pre-existing key:value pairs.
* api-change:``privatenetworks``: This release allows Private5G customers to choose different commitment plans (60-days, 1-year, 3-years) when placing new orders, enables automatic renewal option for 1-year and 3-years commitments. It also allows customers to update the commitment plan of an existing radio unit.
* api-change:``ssm``: Systems Manager doc-only update for June 2023.
* api-change:``rds``: Documentation improvements for create, describe, and modify DB clusters and DB instances.
* api-change:``guardduty``: Add support for user.extra.sessionName in Kubernetes Audit Logs Findings.
* api-change:``fsx``: Update to Amazon FSx documentation.
* api-change:``emr-serverless``: This release adds support to update the release label of an EMR Serverless application to upgrade it to a different version of Amazon EMR via UpdateApplication API.
* api-change:``verifiedpermissions``: Added improved descriptions and new code samples to SDK documentation.
* api-change:``sagemaker``: Introducing TTL for online store records in feature groups.


2.12.3
======

* api-change:``dynamodb``: Documentation updates for DynamoDB
* api-change:``emr``: Update emr command to latest version
* api-change:``mediaconvert``: This release introduces the bandwidth reduction filter for the HEVC encoder, increases the limits of outputs per job, and updates support for the Nagra SDK to version 1.14.7.
* api-change:``sagemaker``: This release provides support in SageMaker for output files in training jobs to be uploaded without compression and enable customer to deploy uncompressed model from S3 to real-time inference Endpoints. In addition, ml.trn1n.32xlarge is added to supported instance type list in training job.
* api-change:``transfer``: This release adds a new parameter StructuredLogDestinations to CreateServer, UpdateServer APIs.
* api-change:``kendra``: Introducing Amazon Kendra Retrieve API that can be used to retrieve relevant passages or text excerpts given an input query.
* api-change:``chime-sdk-messaging``: ChannelMessages can be made visible to sender and intended recipient rather than all channel members with the target attribute. For example, a user can send messages to a bot and receive messages back in a group channel without other members seeing them.
* api-change:``mq``: The Cross Region Disaster Recovery feature allows to replicate a brokers state from one region to another in order to provide customers with multi-region resiliency in the event of a regional outage.
* api-change:``inspector2``: This release adds support for Software Bill of Materials (SBOM) export and the general availability of code scanning for AWS Lambda functions.
* api-change:``chime-sdk-identity``: AppInstanceBots can be configured to be invoked or not using the Target or the CHIME.mentions attribute for ChannelMessages
* api-change:``stepfunctions``: Update stepfunctions command to latest version


2.12.2
======

* api-change:``route53domains``: Update MaxItems upper bound to 1000 for ListPricesRequest
* api-change:``s3``: This release adds SDK support for request-payer request header and request-charged response header in the "GetBucketAccelerateConfiguration", "ListMultipartUploads", "ListObjects", "ListObjectsV2" and "ListObjectVersions" S3 APIs.
* api-change:``connect``: Updates the *InstanceStorageConfig APIs to support a new ResourceType: SCREEN_RECORDINGS to enable screen recording and specify the storage configurations for publishing the recordings. Also updates DescribeInstance and ListInstances APIs to include InstanceAccessUrl attribute in the API response.
* api-change:``ec2``: Adds support for targeting Dedicated Host allocations by assetIds in AWS Outposts
* api-change:``pricing``: This release updates the PriceListArn regex pattern.
* api-change:``sagemaker``: Amazon Sagemaker Autopilot releases CreateAutoMLJobV2 and DescribeAutoMLJobV2 for Autopilot customers with ImageClassification, TextClassification and Tabular problem type config support.
* api-change:``account``: Improve pagination support for ListRegions
* api-change:``cloudformation``: Specify desired CloudFormation behavior in the event of ChangeSet execution failure using the CreateChangeSet OnStackFailure parameter
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``appflow``: This release adds new API to reset connector metadata cache
* api-change:``ecs``: Documentation only update to address various tickets.
* api-change:``lambda``: This release adds RecursiveInvocationException to the Invoke API and InvokeWithResponseStream API.
* enhancement:Python: Update bundled Python interpreter to 3.11.4
* api-change:``ec2``: API changes to AWS Verified Access to include data from trust providers in logs
* api-change:``config``: Updated ResourceType enum with new resource types onboarded by AWS Config in May 2023.
* api-change:``redshift``: Added support for custom domain names for Redshift Provisioned clusters. This feature enables customers to create a custom domain name and use ACM to generate fully secure connections to it.
* api-change:``glue``: This release adds support for creating cross region table/database resource links
* api-change:``discovery``: Add Amazon EC2 instance recommendations export
* enhancement:openssl: Update bundled openssl version to 1.1.1u


2.12.1
======

* api-change:``guardduty``: Updated descriptions for some APIs.
* api-change:``efs``: Update efs command to latest version
* enhancement:dependency: Bump pyinstaller from 5.10.1 to 5.12.0
* api-change:``location``: Amazon Location Service adds categories to places, including filtering on those categories in searches. Also, you can now add metadata properties to your geofences.
* api-change:``auditmanager``: This release introduces 2 Audit Manager features: CSV exports and new manual evidence options. You can now export your evidence finder results in CSV format. In addition, you can now add manual evidence to a control by entering free-form text or uploading a file from your browser.


2.12.0
======

* api-change:``securityhub``: Add support for Security Hub Automation Rules
* api-change:``simspaceweaver``: This release fixes using aws-us-gov ARNs in API calls and adds documentation for snapshot APIs.
* api-change:``fsx``: Amazon FSx for NetApp ONTAP now supports joining a storage virtual machine (SVM) to Active Directory after the SVM has been created.
* api-change:``imagebuilder``: Change the Image Builder ImagePipeline dateNextRun field to more accurately describe the data.
* api-change:``rekognition``: This release adds support for improved accuracy with user vector in Amazon Rekognition Face Search. Adds new APIs: AssociateFaces, CreateUser, DeleteUser, DisassociateFaces, ListUsers, SearchUsers, SearchUsersByImage. Also adds new face metadata that can be stored: user vector.
* api-change:``wellarchitected``: AWS Well-Architected now supports Profiles that help customers prioritize which questions to focus on first by providing a list of prioritized questions that are better aligned with their business goals and outcomes.
* api-change:``lightsail``: This release adds pagination for the Get Certificates API operation.
* feature:``ec2-instance-connect``: Add ``ssh`` and ``open-tunnel`` commands for connecting to an EC2 instance via an OpenSSH client and a websocket tunnel respectively.
* api-change:``amplifyuibuilder``: AWS Amplify UIBuilder is launching Codegen UI, a new feature that enables you to generate your amplify uibuilder components and forms.
* api-change:``ec2``: This release introduces a new feature, EC2 Instance Connect Endpoint, that enables you to connect to a resource over TCP, without requiring the resource to have a public IPv4 address.
* api-change:``s3``: Integrate double encryption feature to SDKs.
* api-change:``acm-pca``: Document-only update to refresh CLI  documentation for AWS Private CA. No change to the service.
* api-change:``codeguru-security``: Initial release of Amazon CodeGuru Security APIs
* api-change:``verifiedpermissions``: GA release of Amazon Verified Permissions.
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``connect``: This release adds search APIs for Prompts, Quick Connects and Hours of Operations, which can be used to search for those resources within a Connect Instance.
* api-change:``sagemaker``: Sagemaker Neo now supports compilation for inferentia2 (ML_INF2) and Trainium1 (ML_TRN1) as available targets. With these devices, you can run your workloads at highest performance with lowest cost. inferentia2 (ML_INF2) is available in CMH and Trainium1 (ML_TRN1) is available in IAD currently
* api-change:``opensearch``: This release adds support for SkipUnavailable connection property for cross cluster search
* api-change:``wafv2``: You can now detect and block fraudulent account creation attempts with the new AWS WAF Fraud Control account creation fraud prevention (ACFP) managed rule group AWSManagedRulesACFPRuleSet.
* api-change:``cloudtrail``: This feature allows users to view dashboards for CloudTrail Lake event data stores.
* api-change:``drs``: Added APIs to support network replication and recovery using AWS Elastic Disaster Recovery.
* api-change:``dynamodb``: Documentation updates for DynamoDB


2.11.27
=======

* api-change:``iotdeviceadvisor``: AWS IoT Core Device Advisor now supports new Qualification Suite test case list. With this update, customers can more easily create new qualification test suite with an empty rootGroup input.
* api-change:``payment-cryptography``: Initial release of AWS Payment Cryptography Control Plane service for creating and managing cryptographic keys used during card payment processing.
* api-change:``customer-profiles``: This release introduces event stream related APIs.
* api-change:``timestream-write``: This release adds the capability for customers to define how their data should be partitioned, optimizing for certain access patterns. This definition will take place as a part of the table creation.
* api-change:``logs``: This change adds support for account level data protection policies using 3 new APIs, PutAccountPolicy, DeleteAccountPolicy and DescribeAccountPolicy. DescribeLogGroup API has been modified to indicate if account level policy is applied to the LogGroup via "inheritedProperties" list in the response.
* api-change:``directconnect``: This update corrects the jumbo frames mtu values from 9100 to 8500 for transit virtual interfaces.
* api-change:``athena``: You can now define custom spark properties at start of the session for use cases like cluster encryption, table formats, and general Spark tuning.
* api-change:``emr-containers``: EMR on EKS adds support for log rotation of Spark container logs with EMR-6.11.0 onwards, to the StartJobRun API.
* api-change:``cloudformation``: AWS CloudFormation StackSets is updating the deployment experience for all stackset operations to skip suspended AWS accounts during deployments. StackSets will skip target AWS accounts that are suspended and set the Detailed Status of the corresponding stack instances as SKIPPED_SUSPENDED_ACCOUNT
* api-change:``payment-cryptography-data``: Initial release of AWS Payment Cryptography DataPlane Plane service for performing cryptographic operations typically used during card payment processing.
* api-change:``servicecatalog``: New parameter added in ServiceCatalog DescribeProvisioningArtifact api - IncludeProvisioningArtifactParameters. This parameter can be used to return information about the parameters used to provision the product
* api-change:``comprehendmedical``: This release supports a new set of entities and traits.


2.11.26
=======

* api-change:``frauddetector``: Added new variable types, new DateTime data type, and new rules engine functions for interacting and working with DateTime data types.
* api-change:``iot-data``: Update thing shadow name regex to allow '$' character
* api-change:``cloudformation``: AWS CloudFormation StackSets provides customers with three new APIs to activate, deactivate, and describe AWS Organizations trusted access which is needed to get started with service-managed StackSets.
* api-change:``connect``: GetMetricDataV2 API is now available in AWS GovCloud(US) region.
* api-change:``cloudtrail``: This feature allows users to start and stop event ingestion on a CloudTrail Lake event data store.
* api-change:``athena``: This release introduces the DeleteCapacityReservation API and the ability to manage capacity reservations using CloudFormation
* api-change:``finspace``: Releasing new Managed kdb Insights APIs
* api-change:``inspector2``: Adds new response properties and request parameters for 'last scanned at' on the ListCoverage operation. This feature allows you to search and view the date of which your resources were last scanned by Inspector.
* api-change:``wafv2``: Added APIs to describe managed products. The APIs retrieve information about rule groups that are managed by AWS and by AWS Marketplace sellers.
* api-change:``sqs``: Amazon SQS adds three new APIs - StartMessageMoveTask, CancelMessageMoveTask, and ListMessageMoveTasks to automate redriving messages from dead-letter queues to source queues or a custom destination.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``signer``: AWS Signer is launching Container Image Signing, a new feature that enables you to sign and verify container images. This feature enables you to validate that only container images you approve are used in your enterprise.
* api-change:``keyspaces``: This release adds support for MRR GA launch, and includes multiregion support in create-keyspace, get-keyspace, and list-keyspace.
* api-change:``iam``: This release updates the AccountAlias regex pattern with the same length restrictions enforced by the length constraint.
* api-change:``mwaa``: This release adds ROLLING_BACK and CREATING_SNAPSHOT environment statuses for Amazon MWAA environments.
* api-change:``quicksight``: QuickSight support for pivot table field collapse state, radar chart range scale and multiple scope options in conditional formatting.
* api-change:``ec2``: Making InstanceTagAttribute as the required parameter for the DeregisterInstanceEventNotificationAttributes and RegisterInstanceEventNotificationAttributes APIs.
* api-change:``emr``: Update emr command to latest version
* api-change:``lambda``: Add Ruby 3.2 (ruby3.2) Runtime support to AWS Lambda.
* api-change:``iot``: Adding IoT Device Management Software Package Catalog APIs to register, store, and report system software packages, along with their versions and metadata in a centralized location.
* api-change:``sagemaker``: This release adds Selective Execution feature that allows SageMaker Pipelines users to run selected steps in a pipeline.
* api-change:``kms``: This release includes feature to import customer's asymmetric (RSA and ECC) and HMAC keys into KMS.  It also includes feature to allow customers to specify number of days to schedule a KMS key deletion as a policy condition key.


2.11.25
=======

* api-change:``alexaforbusiness``: Alexa for Business has been deprecated and is no longer supported.
* api-change:``ivs``: API Update for IVS Advanced Channel type
* api-change:``sagemaker``: Amazon Sagemaker Autopilot adds support for Parquet file input to NLP text classification jobs.
* api-change:``customer-profiles``: This release introduces calculated attribute related APIs.
* api-change:``workspaces-web``: WorkSpaces Web now allows you to control which IP addresses your WorkSpaces Web portal may be accessed from.
* api-change:``wafv2``: Corrected the information for the header order FieldToMatch setting
* api-change:``m2``: Adds an optional create-only 'roleArn' property to Application resources.  Enables PS and PO data set org types.
* api-change:``config``: Resource Types Exclusion feature launch by AWS Config
* api-change:``healthlake``: This release adds a new request parameter to the CreateFHIRDatastore API operation. IdentityProviderConfiguration specifies how you want to authenticate incoming requests to your Healthlake Data Store.
* api-change:``frauddetector``: This release enables publishing event predictions from Amazon Fraud Detector (AFD) to Amazon EventBridge. For example, after getting predictions from AFD, Amazon EventBridge rules can be configured to trigger notification through an SNS topic, send a message with SES, or trigger Lambda workflows.
* api-change:``servicecatalog``: Documentation updates for ServiceCatalog.
* api-change:``rds``: This release adds support for changing the engine for Oracle using the ModifyDbInstance API
* api-change:``appflow``: Added ability to select DataTransferApiType for DescribeConnector and CreateFlow requests when using Async supported connectors. Added supportedDataTransferType to DescribeConnector/DescribeConnectors/ListConnector response.


2.11.24
=======

* api-change:``connect``: Documentation update for a new Initiation Method value in DescribeContact API
* api-change:``personalize``: This release provides support for the exclusion of certain columns for training when creating a solution and creating or updating a recommender with Amazon Personalize.
* api-change:``securityhub``: Added new resource detail objects to ASFF, including resources for AwsGuardDutyDetector, AwsAmazonMqBroker, AwsEventSchemasRegistry, AwsAppSyncGraphQlApi and AwsStepFunctionStateMachine.
* api-change:``groundstation``: Updating description of GetMinuteUsage to be clearer.
* api-change:``memorydb``: Amazon MemoryDB for Redis now supports AWS Identity and Access Management authentication access to Redis clusters starting with redis-engine version 7.0
* api-change:``iotfleetwise``: Campaigns now support selecting Timestream or S3 as the data destination, Signal catalogs now support "Deprecation" keyword released in VSS v2.1 and "Comment" keyword released in VSS v3.0
* api-change:``location``: This release adds API support for political views for the maps service APIs: CreateMap, UpdateMap, DescribeMap.
* api-change:``polly``: Amazon Polly adds 2 new voices - Sofie (da-DK) and Niamh (en-IE)
* api-change:``wafv2``: This SDK release provides customers the ability to use Header Order as a field to match.
* api-change:``glue``: Added Runtime parameter to allow selection of Ray Runtime
* api-change:``iotwireless``: Add Multicast Group support in Network Analyzer Configuration.
* api-change:``sagemaker``: Added ml.p4d and ml.inf1 as supported instance type families for SageMaker Notebook Instances.
* api-change:``chime-sdk-voice``: Added optional CallLeg field to StartSpeakerSearchTask API request


2.11.23
=======

* api-change:``migration-hub-refactor-spaces``: This SDK update allows for path parameter syntax to be passed to the CreateRoute API. Path parameter syntax require parameters to be enclosed in {} characters. This update also includes a new AppendSourcePath field which lets users forward the source path to the Service URL endpoint.
* api-change:``application-autoscaling``: With this release, ElastiCache customers will be able to use predefined metricType "ElastiCacheDatabaseCapacityUsageCountedForEvictPercentage" for their ElastiCache instances.
* api-change:``gamelift``: GameLift FleetIQ users can now filter game server claim requests to exclude servers on instances that are draining.
* api-change:``sagemaker``: SageMaker now provides an instantaneous deployment recommendation through the DescribeModel API
* api-change:``cur``: Add support for split cost allocation data on a report.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports enabling Autotune for tuning jobs which can choose tuning job configurations.
* api-change:``appsync``: This release introduces AppSync Merged APIs, which provide the ability to compose multiple source APIs into a single federated/merged API.
* api-change:``codepipeline``: Add PollingDisabledAt time information in PipelineMetadata object of GetPipeline API.
* api-change:``connect``: Amazon Connect Evaluation Capabilities: validation improvements
* api-change:``glue``: Added ability to create data quality rulesets for shared, cross-account Glue Data Catalog tables. Added support for dataset comparison rules through a new parameter called AdditionalDataSources. Enhanced the data quality results with a map containing profiled metric values.


2.11.22
=======

* api-change:``pinpoint``: Amazon Pinpoint is deprecating the tags parameter in the UpdateSegment, UpdateCampaign, UpdateEmailTemplate, UpdateSmsTemplate, UpdatePushTemplate, UpdateInAppTemplate and UpdateVoiceTemplate. Amazon Pinpoint will end support tags parameter by May 22, 2023.
* api-change:``translate``: Added support for calling TranslateDocument API.
* api-change:``sagemaker``: Added ModelNameEquals, ModelPackageVersionArnEquals in request and ModelName, SamplePayloadUrl, ModelPackageVersionArn in response of ListInferenceRecommendationsJobs API. Added Invocation timestamps in response of DescribeInferenceRecommendationsJob API & ListInferenceRecommendationsJobSteps API.
* api-change:``quicksight``: Add support for Asset Bundle, Geospatial Heatmaps.
* api-change:``fms``: Fixes issue that could cause calls to GetAdminScope and ListAdminAccountsForOrganization to return a 500 Internal Server error.
* api-change:``backup``: Added support for tags on restore.


2.11.21
=======

* api-change:``wafv2``: My AWS Service (placeholder) - You can now rate limit web requests based on aggregation keys other than IP addresses, and you can aggregate using combinations of keys. You can also rate limit all requests that match a scope-down statement, without further aggregation.
* api-change:``rds``: RDS documentation update for the EngineVersion parameter of ModifyDBSnapshot
* api-change:``kafka``: Added a fix to make clusterarn a required field in ListClientVpcConnections and RejectClientVpcConnection APIs
* api-change:``rekognition``: This release adds a new EyeDirection attribute in Amazon Rekognition DetectFaces and IndexFaces APIs which predicts the yaw and pitch angles of a person's eye gaze direction for each face detected in the image.
* api-change:``transfer``: This release introduces the ability to require both password and SSH key when users authenticate to your Transfer Family servers that use the SFTP protocol.
* api-change:``detective``: Added and updated API operations in Detective to support the integration of ASFF Security Hub findings.
* api-change:``mediaconvert``: This release introduces a new MXF Profile for XDCAM which is strictly compliant with the SMPTE RDD 9 standard and improved handling of output name modifiers.
* api-change:``compute-optimizer``: In this launch, we add support for showing integration status with external metric providers such as Instana, Datadog ...etc in GetEC2InstanceRecommendations and ExportEC2InstanceRecommendations apis
* api-change:``glue``: Add Support for Tags for Custom Entity Types
* api-change:``codecatalyst``: With this release, the users can list the active sessions connected to their Dev Environment on AWS CodeCatalyst
* api-change:``directconnect``: This release includes an update to the mtu value for CreateTransitVirtualInterface from 9001 mtu to 8500 mtu.
* api-change:``ecs``: Documentation only release to address various tickets.
* api-change:``connect``: You can programmatically create and manage prompts using APIs, for example, to extract prompts stored within Amazon Connect and add them to your Amazon S3 bucket. AWS CloudTrail, AWS CloudFormation and tagging are supported.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``sesv2``: This release allows customers to update scaling mode property of dedicated IP pools with PutDedicatedIpPoolScalingAttributes call.
* api-change:``mediapackagev2``: Adds support for the MediaPackage Live v2 API
* api-change:``rolesanywhere``: Adds support for custom notification settings in a trust anchor. Introduces PutNotificationSettings and ResetNotificationSettings API's. Updates DurationSeconds max value to 3600.
* api-change:``ec2``: Add support for i4g.large, i4g.xlarge, i4g.2xlarge, i4g.4xlarge, i4g.8xlarge and i4g.16xlarge instances powered by AWS Graviton2 processors that deliver up to 15% better compute performance than our other storage-optimized instances.
* api-change:``sagemaker-geospatial``: This release makes ExecutionRoleArn a required field in the StartEarthObservationJob API.
* api-change:``cloudtrail``: Add ConflictException to PutEventSelectors, add (Channel/EDS)ARNInvalidException to Tag APIs. These exceptions provide customers with more specific error messages instead of internal errors.
* api-change:``connectcases``: This release adds the ability to create fields with type Url through the CreateField API. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``backup``: Add  ResourceArn, ResourceType, and BackupVaultName to ListRecoveryPointsByLegalHold API response.
* api-change:``sts``: API updates for the AWS Security Token Service


2.11.20
=======

* api-change:``elasticache``: Added support to modify the cluster mode configuration for the existing ElastiCache ReplicationGroups. Customers can now modify the configuration from cluster mode disabled to cluster mode enabled.
* api-change:``opensearch``: This release fixes DescribePackages API error with null filter value parameter.
* api-change:``health``: Add support for regional endpoints
* api-change:``support``: This release adds 2 new Support APIs, DescribeCreateCaseOptions and DescribeSupportedLanguages. You can use these new APIs to get available support languages.
* api-change:``swf``: This release adds a new API parameter to exclude old history events from decision tasks.
* api-change:``emr``: Update emr command to latest version
* api-change:``rds``: Amazon Relational Database Service (RDS) updates for the new Aurora I/O-Optimized storage type for Amazon Aurora DB clusters
* api-change:``connect``: This release updates GetMetricDataV2 API, to support metric data up-to last 35 days
* api-change:``route53resolver``: Update FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``es``: This release fixes DescribePackages API error with null filter value parameter.
* api-change:``omics``: This release provides support for Ready2Run and GPU workflows, an improved read set filter, the direct upload of read sets into Omics Storage, and annotation parsing for analytics stores.
* api-change:``ivs-realtime``: Add methods for inspecting and debugging stages: ListStageSessions, GetStageSession, ListParticipants, GetParticipant, and ListParticipantEvents.


2.11.19
=======

* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``ec2``: This release adds support the inf2 and trn1n instances. inf2 instances are purpose built for deep learning inference while trn1n instances are powered by AWS Trainium accelerators and they build on the capabilities of Trainium-powered trn1 instances.
* api-change:``mediatailor``: This release adds support for AFTER_LIVE_EDGE mode configuration for avail suppression, and adding a fill-policy setting that sets the avail suppression to PARTIAL_AVAIL or FULL_AVAIL_ONLY when AFTER_LIVE_EDGE is enabled.
* api-change:``sagemaker``: This release includes support for (1) Provisioned Concurrency for Amazon SageMaker Serverless Inference and (2) UpdateEndpointWeightsAndCapacities API for Serverless endpoints.
* api-change:``inspector2``: Amazon Inspector now allows customers to search its vulnerability intelligence database if any of the Inspector scanning types are activated.
* api-change:``glue``: Support large worker types G.4x and G.8x for Glue Spark
* api-change:``application-autoscaling``: With this release, Amazon SageMaker Serverless Inference customers can use Application Auto Scaling to auto scale the provisioned concurrency of their serverless endpoints.
* api-change:``iotsitewise``: Provide support for 20,000 max results for GetAssetPropertyValueHistory/BatchGetAssetPropertyValueHistory and 15 minute aggregate resolution for GetAssetPropertyAggregates/BatchGetAssetPropertyAggregates
* api-change:``glue``: This release adds AmazonRedshift Source and Target nodes in addition to DynamicTransform OutputSchemas
* api-change:``guardduty``: Add AccessDeniedException 403 Error message code to support 3 Tagging related APIs


2.11.18
=======

* api-change:``securityhub``: Add support for Finding History.
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``ec2``: Adds an SDK paginator for GetNetworkInsightsAccessScopeAnalysisFindings
* api-change:``sagemaker``: We added support for ml.inf2 and ml.trn1 family of instances on Amazon SageMaker for deploying machine learning (ML) models for Real-time and Asynchronous inference. You can use these instances to achieve high performance at a low cost for generative artificial intelligence (AI) models.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``iottwinmaker``: This release adds a field for GetScene API to return error code and message from dependency services.
* api-change:``wellarchitected``: This release deepens integration with AWS Service Catalog AppRegistry to improve workload resource discovery.
* api-change:``opensearch``: Amazon OpenSearch Service adds the option to deploy a domain across multiple Availability Zones, with each AZ containing a complete copy of data and with nodes in one AZ acting as a standby. This option provides 99.99% availability and consistent performance in the event of infrastructure failure.
* api-change:``ecs``: Documentation update for new error type NamespaceNotFoundException for CreateCluster and UpdateCluster
* api-change:``network-firewall``: AWS Network Firewall now supports policy level HOME_NET variable overrides.
* api-change:``opensearch``: DescribeDomainNodes: A new API that provides configuration information for nodes part of the domain
* api-change:``config``: Updated ResourceType enum with new resource types onboarded by AWS Config in April 2023.
* api-change:``appsync``: Private API support for AWS AppSync. With Private APIs, you can now create GraphQL APIs that can only be accessed from your Amazon Virtual Private Cloud ("VPC").
* api-change:``inspector2``: This feature provides deep inspection for linux based instance
* api-change:``connect``: Remove unused InvalidParameterException from CreateParticipant API
* api-change:``rekognition``: This release adds a new attribute FaceOccluded. Additionally, you can now select attributes individually (e.g. ["DEFAULT", "FACE_OCCLUDED", "AGE_RANGE"] instead of ["ALL"]), which can reduce response time.
* api-change:``quicksight``: Add support for Topic, Dataset parameters and VPC
* api-change:``network-firewall``: This release adds support for the Suricata REJECT option in midstream exception configurations.


2.11.17
=======

* api-change:``grafana``: This release adds support for the grafanaVersion parameter in CreateWorkspace.
* api-change:``connect``: Amazon Connect Service Rules API update: Added OnContactEvaluationSubmit event source to support user configuring evaluation form rules.
* api-change:``athena``: You can now use capacity reservations on Amazon Athena to run SQL queries on fully-managed compute capacity.
* api-change:``wafv2``: You can now associate a web ACL with a Verified Access instance.
* api-change:``efs``: Update efs command to latest version
* api-change:``appflow``: Adds Jwt Support for Salesforce Credentials.
* api-change:``workspaces``: Added Windows 11 to support Microsoft_Office_2019
* api-change:``resiliencehub``: This release will improve resource level transparency in applications by discovering previously hidden resources.
* api-change:``kendra``: AWS Kendra now supports configuring document fields/attributes via the GetQuerySuggestions API. You can now base query suggestions on the contents of document fields.
* api-change:``ecs``: Documentation only update to address Amazon ECS tickets.
* api-change:``kms``: This release makes the NitroEnclave request parameter Recipient and the response field for CiphertextForRecipient available in AWS SDKs. It also adds the regex pattern for CloudHsmClusterId validation.
* api-change:``compute-optimizer``: support for tag filtering within compute optimizer. ability to filter recommendation results by tag and tag key value pairs. ability to filter by inferred workload type added.
* api-change:``sagemaker``: Amazon Sagemaker Autopilot supports training models with sample weights and additional objective metrics.
* api-change:``appflow``: This release adds new API to cancel flow executions.
* api-change:``directconnect``: This release corrects the jumbo frames MTU from 9100 to 8500.
* api-change:``rekognition``: Added support for aggregating moderation labels by video segment timestamps for Stored Video Content Moderation APIs and added additional information about the job to all Stored Video Get API responses.
* api-change:``simspaceweaver``: Added a new CreateSnapshot API. For the StartSimulation API, SchemaS3Location is now optional, added a new SnapshotS3Location parameter. For the DescribeSimulation API, added SNAPSHOT_IN_PROGRESS simulation state, deprecated SchemaError, added new fields: StartError and SnapshotS3Location.
* api-change:``iot``: This release allows AWS IoT Core users to specify a TLS security policy when creating and updating AWS IoT Domain Configurations.


2.11.16
=======

* api-change:``rekognition``: Added new status result to Liveness session status.
* api-change:``qldb``: Documentation updates for Amazon QLDB
* api-change:``ec2``: This release adds support for AMD SEV-SNP on EC2 instances.
* api-change:``osis``: Initial release for OpenSearch Ingestion
* api-change:``appflow``: Increased the max length for RefreshToken and AuthCode from 2048 to 4096.
* api-change:``guardduty``: Added API support to initiate on-demand malware scan on specific resources.
* api-change:``xray``: Updated X-Ray documentation with Resource Policy API descriptions.
* api-change:``kafka``: Amazon MSK has added new APIs that allows multi-VPC private connectivity and cluster policy support for Amazon MSK clusters that simplify connectivity and access between your Apache Kafka clients hosted in different VPCs and AWS accounts and your Amazon MSK clusters.
* api-change:``connect``: This release adds a new API CreateParticipant. For Amazon Connect Chat, you can use this new API to customize chat flow experiences.
* api-change:``emr-containers``: This release adds GetManagedEndpointSessionCredentials, a new API that allows customers to generate an auth token to connect to a managed endpoint, enabling features such as self-hosted Jupyter notebooks for EMR on EKS.
* api-change:``pinpoint``: Adds support for journey runs and querying journey execution metrics based on journey runs. Adds execution metrics to campaign activities. Updates docs for Advanced Quiet Time.
* api-change:``mediaconvert``: This release introduces a noise reduction pre-filter, linear interpolation deinterlace mode, video pass-through, updated default job settings, and expanded LC-AAC Stereo audio bitrate ranges.
* api-change:``fms``: AWS Firewall Manager adds support for multiple administrators. You can now delegate more than one administrator per organization.
* api-change:``iotdeviceadvisor``: AWS IoT Core Device Advisor now supports MQTT over WebSocket. With this update, customers can run all three test suites of AWS IoT Core Device Advisor - qualification, custom, and long duration tests - using Signature Version 4 for MQTT over WebSocket.
* api-change:``ec2``: API changes to AWS Verified Access related to identity providers' information.
* api-change:``connect``: Amazon Connect, Contact Lens Evaluation API release including ability to manage forms and to submit contact evaluations.
* api-change:``ecs``: Documentation update to address various Amazon ECS tickets.
* enhancement:dependency: Bump pyinstaller from 5.8.0 to 5.10.1 
* api-change:``codecatalyst``: Documentation updates for Amazon CodeCatalyst.
* api-change:``lambda``: Add Java 17 (java17) support to AWS Lambda
* api-change:``sagemaker``: Added ml.p4d.24xlarge and ml.p4de.24xlarge as supported instances for SageMaker Studio
* api-change:``ds``: New field added in AWS Managed Microsoft AD DescribeSettings response and regex pattern update for UpdateSettings value.  Added length validation to RemoteDomainName.
* api-change:``marketplace-catalog``: Enabled Pagination for List Entities and List Change Sets operations
* api-change:``osis``: Documentation updates for OpenSearch Ingestion
* api-change:``datasync``: This release adds 13 new APIs to support AWS DataSync Discovery GA.
* api-change:``chime-sdk-messaging``: Remove non actionable field from UpdateChannelReadMarker and DeleteChannelRequest.  Add precise exceptions to DeleteChannel and DeleteStreamingConfigurations error cases.


2.11.15
=======

* api-change:``wafv2``: You can now create encrypted API keys to use in a client application integration of the JavaScript CAPTCHA API . You can also retrieve a list of your API keys and the JavaScript application integration URL.
* api-change:``chime-sdk-meetings``: Adds support for Hindi and Thai languages and additional Amazon Transcribe parameters to the StartMeetingTranscription API.
* api-change:``snowball``: Adds support for Amazon S3 compatible storage. AWS Snow Family customers can now use Amazon S3 compatible storage on Snowball Edge devices. Also adds support for V3_5S. This is a refreshed AWS Snowball Edge Storage Optimized device type with 210TB SSD (customer usable).
* bugfix:Output: Consistently remove ResponseMetadata field for all commands (`#7829 <https://github.com/aws/aws-cli/pull/7829>`__)
* api-change:``s3``: Provides support for "Snow" Storage class.
* api-change:``comprehend``: This release supports native document models for custom classification, in addition to plain-text models. You train native document models using documents (PDF, Word, images) in their native format.
* api-change:``gamelift``: Amazon GameLift supports creating Builds for Windows 2016 operating system.
* api-change:``chime``: Adds support for Hindi and Thai languages and additional Amazon Transcribe parameters to the StartMeetingTranscription API.
* api-change:``guardduty``: This release adds support for the new Lambda Protection feature.
* api-change:``sagemaker``: Amazon SageMaker Canvas adds ModelRegisterSettings support for CanvasAppSettings.
* api-change:``rds``: Adds support for the ImageId parameter of CreateCustomDBEngineVersion to RDS Custom for Oracle
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``s3control``: Provides support for overriding endpoint when region is "snow". This will enable bucket APIs for Amazon S3 Compatible storage on Snow Family devices.
* api-change:``ecs``: This release supports the Account Setting "TagResourceAuthorization" that allows for enhanced Tagging security controls.
* api-change:``iot``: Support additional OTA states in GetOTAUpdate API
* api-change:``ram``: This release adds support for customer managed permissions. Customer managed permissions enable customers to author and manage tailored permissions for resources shared using RAM.
* api-change:``chime-sdk-media-pipelines``: This release adds support for specifying the recording file format in an S3 recording sink configuration.


2.11.14
=======

* api-change:``dynamodb``: Documentation updates for DynamoDB API
* api-change:``lambda``: Add Python 3.10 (python3.10) support to AWS Lambda
* api-change:``appflow``: This release adds a Client Token parameter to the following AppFlow APIs: Create/Update Connector Profile, Create/Update Flow, Start Flow, Register Connector, Update Connector Registration. The Client Token parameter allows idempotent operations for these APIs.
* api-change:``migration-hub-refactor-spaces``: Doc only update for Refactor Spaces environments without network bridge feature.
* api-change:``emr-serverless``: The GetJobRun API has been updated to include the job's billed resource utilization. This utilization shows the aggregate vCPU, memory and storage that AWS has billed for the job run. The billed resources include a 1-minute minimum usage for workers, plus additional storage over 20 GB per worker.
* api-change:``drs``: Changed existing APIs and added new APIs to support using an account-level launch configuration template with AWS Elastic Disaster Recovery.
* api-change:``internetmonitor``: This release includes a new configurable value, TrafficPercentageToMonitor, which allows users to adjust the amount of traffic monitored by percentage
* api-change:``lambda``: This release adds SnapStart related exceptions to InvokeWithResponseStream API. IAM access related documentation is also added for this API.
* api-change:``ecs``: This release supports  ephemeral storage for AWS Fargate Windows containers.
* api-change:``rds``: This release adds support of modifying the engine mode of database clusters.
* enhancement:``cloudtrail``: Add ``verify-query-results`` command for verifying CloudTrail Lake queries
* api-change:``iotwireless``: Supports the new feature of LoRaWAN roaming, allows to configure MaxEirp for LoRaWAN gateway, and allows to configure PingSlotPeriod for LoRaWAN multicast group


2.11.13
=======

* api-change:``groundstation``: AWS Ground Station Wideband DigIF GA Release
* api-change:``mediaconnect``: Gateway is a new feature of AWS Elemental MediaConnect. Gateway allows the deployment of on-premises resources for the purpose of transporting live video to and from the AWS Cloud.
* api-change:``chime-sdk-voice``: This release adds tagging support for Voice Connectors and SIP Media Applications
* api-change:``managedblockchain``: Removal of the Ropsten network. The Ethereum foundation ceased support of Ropsten on December 31st, 2022..


2.11.12
=======

* api-change:``lambda``: This release adds a new Lambda InvokeWithResponseStream API to support streaming Lambda function responses. The release also adds a new InvokeMode parameter to Function Url APIs to control whether the response will be streamed or buffered.
* api-change:``events``: Update events command to latest version
* api-change:``servicecatalog``: Updates description for property
* api-change:``rekognition``: This release adds support for Face Liveness APIs in Amazon Rekognition. Updates UpdateStreamProcessor to return ResourceInUseException Exception. Minor updates to API documentation.
* api-change:``fsx``: Amazon FSx for Lustre now supports creating data repository associations on Persistent_1 and Scratch_2 file systems.
* api-change:``ecr-public``: This release will allow using registry alias as registryId in BatchDeleteImage request.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK now supports conversion of 608 paint-on captions to pop-on captions for SCC sources.
* api-change:``connect``: This release adds the ability to configure an agent's routing profile to receive contacts from multiple channels at the same time via extending the UpdateRoutingProfileConcurrency, CreateRoutingProfile and DescribeRoutingProfile APIs.
* api-change:``iot-data``: This release adds support for MQTT5 user properties when calling the AWS IoT GetRetainedMessage API
* api-change:``quicksight``: This release has two changes: adding the OR condition to tag-based RLS rules in CreateDataSet and UpdateDataSet; adding RefreshSchedule and Incremental RefreshProperties operations for users to programmatically configure SPICE dataset ingestions.
* api-change:``marketplace-catalog``: Added three new APIs to support resource sharing: GetResourcePolicy, PutResourcePolicy, and DeleteResourcePolicy. Added new OwnershipType field to ListEntities request to let users filter on entities that are shared with them. Increased max page size of ListEntities response from 20 to 50 results.
* api-change:``redshift-data``: Update documentation of API descriptions as needed in support of temporary credentials with IAM identity.
* api-change:``dlm``: Updated timestamp format for GetLifecyclePolicy API
* api-change:``emr-serverless``: This release extends GetJobRun API to return job run timeout (executionTimeoutMinutes) specified during StartJobRun call (or default timeout of 720 minutes if none was specified).
* api-change:``omics``: Remove unexpected API changes.
* api-change:``wafv2``: For web ACLs that protect CloudFront protections, the default request body inspection size is now 16 KB, and you can use the new association configuration to increase the inspection size further, up to 64 KB. Sizes over 16 KB can incur additional costs.
* api-change:``docdb``: This release adds a new parameter 'DBClusterParameterGroupName' to 'RestoreDBClusterFromSnapshot' API to associate the name of the DB cluster parameter group while performing restore.
* api-change:``ecs``: This release adds support for enabling FIPS compliance on Amazon ECS Fargate tasks


2.11.11
=======

* api-change:``greengrassv2``: Add support for SUCCEEDED value in coreDeviceExecutionStatus field. Documentation updates for Greengrass V2.
* api-change:``proton``: This release adds support for the AWS Proton service sync feature. Service sync enables managing an AWS Proton service (creating and updating instances) and all of it's corresponding service instances from a Git repository.
* api-change:``cloudformation``: Including UPDATE_COMPLETE as a failed status for DeleteStack waiter.
* api-change:``rds``: Adds and updates the SDK examples


2.11.10
=======

* api-change:``sagemaker``: Amazon SageMaker Asynchronous Inference now allows customer's to receive failure model responses in S3 and receive success/failure model responses in SNS notifications.
* api-change:``servicecatalog``: removed incorrect product type value
* bugfix:cloudformation: Reverts aws/aws-cli`#7787 <https://github.com/aws/aws-cli/issues/7787>`__ and the associated regression aws/aws-cli`#7805 <https://github.com/aws/aws-cli/issues/7805>`__
* api-change:``vpc-lattice``: This release removes the entities in the API doc model package for auth policies.
* api-change:``network-firewall``: AWS Network Firewall now supports IPv6-only subnets.
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling
* api-change:``apprunner``: App Runner adds support for seven new vCPU and memory configurations.
* api-change:``ivs-realtime``: Fix ParticipantToken ExpirationTime format
* api-change:``config``: This release adds resourceType enums for types released in March 2023.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``identitystore``: Documentation updates for Identity Store CLI command reference.
* api-change:``dataexchange``: This release updates the value of MaxResults.
* api-change:``ec2``: C6in, M6in, M6idn, R6in and R6idn bare metal instances are powered by 3rd Generation Intel Xeon Scalable processors and offer up to 200 Gbps of network bandwidth.
* api-change:``elastic-inference``: Updated public documentation for the Describe and Tagging APIs.
* bugfix:eks: Fix eks kubeconfig validations closes `#6564 <https://github.com/aws/aws-cli/issues/6564>`__, fixes `#4843 <https://github.com/aws/aws-cli/issues/4843>`__, fixes `#5532 <https://github.com/aws/aws-cli/issues/5532>`__
* api-change:``amplifyuibuilder``: Support StorageField and custom displays for data-bound options in form builder. Support non-string operands for predicates in collections. Support choosing client to get token from.
* api-change:``ecs``: This is a document only updated to add information about Amazon Elastic Inference (EI).
* api-change:``wafv2``: This release rolls back association config feature for webACLs that protect CloudFront protections.


2.11.9
======

* api-change:``sms``: Deprecating AWS Server Migration Service.
* api-change:``lakeformation``: Add support for database-level federation
* api-change:``internetmonitor``: This release adds a new feature for Amazon CloudWatch Internet Monitor that enables customers to deliver internet measurements to Amazon S3 buckets as well as CloudWatch Logs.
* api-change:``license-manager``: This release adds grant override options to the CreateGrantVersion API. These options can be used to specify grant replacement behavior during grant activation.
* api-change:``mwaa``: This Amazon MWAA release adds the ability to customize the Apache Airflow environment by launching a shell script at startup. This shell script is hosted in your environment's Amazon S3 bucket. Amazon MWAA runs the script before installing requirements and initializing the Apache Airflow process.
* api-change:``resiliencehub``: Adding EKS related documentation for appTemplateBody
* api-change:``sagemaker-featurestore-runtime``: In this release, you can now chose between soft delete and hard delete when calling the DeleteRecord API, so you have more flexibility when it comes to managing online store data.
* api-change:``ec2``: Documentation updates for EC2 On Demand Capacity Reservations
* api-change:``glue``: Add support for database-level federation
* api-change:``servicecatalog``: This release introduces Service Catalog support for Terraform open source. It enables 1. The notify* APIs to Service Catalog. These APIs are used by the terraform engine to notify the result of the provisioning engine execution. 2. Adds a new TERRAFORM_OPEN_SOURCE product type in CreateProduct API.
* api-change:``s3``: Documentation updates for Amazon S3


2.11.8
======

* api-change:``emr``: Update emr command to latest version
* api-change:``wellarchitected``: AWS Well-Architected SDK now supports getting consolidated report metrics and generating a consolidated report PDF.
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now supports Elastic Load Balancing traffic sources with the AttachTrafficSources, DetachTrafficSources, and DescribeTrafficSources APIs. This release also introduces a new activity status, "WaitingForConnectionDraining", for VPC Lattice to the DescribeScalingActivities API.
* api-change:``ivs``: Amazon Interactive Video Service (IVS) now offers customers the ability to configure IVS channels to allow insecure RTMP ingest.
* api-change:``opensearchserverless``: This release includes two new exception types "ServiceQuotaExceededException" and "OcuLimitExceededException".
* bugfix:cloudformation: Fixes `#3991 <https://github.com/aws/aws-cli/issues/3991>`__. Use YAML 1.1 spec in alignment with CloudFormation YAML support.
* api-change:``kendra``: AWS Kendra now supports featured results for a query.
* api-change:``guardduty``: Added EKS Runtime Monitoring feature support to existing detector, finding APIs and introducing new Coverage APIs
* api-change:``compute-optimizer``: This release adds support for HDD EBS volume types and io2 Block Express. We are also adding support for 61 new instance types and instances that have non consecutive runtime.
* bugfix:argument parsing: Fixes issue reported in `#303 <https://github.com/aws/aws-cli/issues/303>`__ involving -h/--help output
* api-change:``athena``: Make DefaultExecutorDpuSize and CoordinatorDpuSize  fields optional  in StartSession
* api-change:``imagebuilder``: Adds support for new image workflow details and image vulnerability detection.
* enhancement:dependency: Bump upper bound of prompt-toolkit to <3.0.39
* api-change:``glue``: This release adds support for AWS Glue Data Quality, which helps you evaluate and monitor the quality of your data and includes the API for creating, deleting, or updating data quality rulesets, runs and evaluations.
* api-change:``vpc-lattice``: General Availability (GA) release of Amazon VPC Lattice
* api-change:``sagemaker-geospatial``: Amazon SageMaker geospatial capabilities now supports server-side encryption with customer managed KMS key and SageMaker notebooks with a SageMaker geospatial image in a Amazon SageMaker Domain with VPC only mode.
* api-change:``batch``: This feature allows Batch on EKS to support configuration of Pod Labels through Metadata for Batch on EKS Jobs.
* api-change:``ec2``: This release adds support for Tunnel Endpoint Lifecycle control, a new feature that provides Site-to-Site VPN customers with better visibility and control of their VPN tunnel maintenance updates.
* api-change:``drs``: Adding a field to the replication configuration APIs to support the auto replicate new disks feature. We also deprecated RetryDataReplication.
* api-change:``network-firewall``: AWS Network Firewall added TLS inspection configurations to allow TLS traffic inspection.
* api-change:``rds``: Add support for creating a read replica DB instance from a Multi-AZ DB cluster.


2.11.7
======

* api-change:``voice-id``: Amazon Connect Voice ID now supports multiple fraudster watchlists. Every domain has a default watchlist where all existing fraudsters are placed by default. Custom watchlists may now be created, managed, and evaluated against for known fraudster detection.
* api-change:``comprehend``: This release adds a new field (FlywheelArn) to the EntitiesDetectionJobProperties object. The FlywheelArn field is returned in the DescribeEntitiesDetectionJob and ListEntitiesDetectionJobs responses when the EntitiesDetection job is started with a FlywheelArn instead of an EntityRecognizerArn .
* api-change:``iotwireless``: Introducing new APIs that enable Sidewalk devices to communicate with AWS IoT Core through Sidewalk gateways. This will empower AWS customers to connect Sidewalk devices with other AWS IoT Services, creating  possibilities for seamless integration and advanced device management.
* api-change:``connect``: This release introduces support for RelatedContactId in the StartChatContact API. Interactive message and interactive message response have been added to the list of supported message content types for this API as well.
* api-change:``sagemaker``: Fixed some improperly rendered links in SDK documentation.
* api-change:``athena``: Enforces a minimal level of encryption for the workgroup for query and calculation results that are written to Amazon S3. When enabled, workgroup users can set encryption only to the minimum level set by the administrator or higher when they submit queries.
* api-change:``servicecatalog-appregistry``: In this release, we started supporting ARN in applicationSpecifier and attributeGroupSpecifier. GetAttributeGroup, ListAttributeGroups and ListAttributeGroupsForApplication APIs will now have CreatedBy field in the response.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``ssm-incidents``: Increased maximum length of "TriggerDetails.rawData" to 10K characters and "IncidentSummary" to 8K characters.
* api-change:``rds``: Added error code CreateCustomDBEngineVersionFault for when the create custom engine version for Custom engines fails.
* enhancement:dependency: Update cryptography requirement from <39.0.3,>=3.3.2 to >=3.3.2,<40.0.2
* api-change:``chime-sdk-voice``: Documentation updates for Amazon Chime SDK Voice.
* api-change:``ssm-contacts``: This release adds 12 new APIs as part of Oncall Schedule feature release, adds support for a new contact type: ONCALL_SCHEDULE. Check public documentation for AWS ssm-contacts for more information
* api-change:``medialive``: AWS Elemental MediaLive now supports ID3 tag insertion for audio only HLS output groups. AWS Elemental Link devices now support tagging.
* api-change:``securityhub``: Added new resource detail objects to ASFF, including resources for AwsEksCluster, AWSS3Bucket, AwsEc2RouteTable and AwsEC2Instance.
* api-change:``connectparticipant``: This release provides an update to the SendMessage API to handle interactive message response content-types.
* api-change:``iot-data``: Add endpoint ruleset support for cn-north-1.


2.11.6
======

* api-change:``chime-sdk-messaging``: ExpirationSettings provides automatic resource deletion for Channels.
* api-change:``codeartifact``: Repository CreationTime is added to the CreateRepository and ListRepositories API responses.
* api-change:``chime-sdk-media-pipelines``: This release adds Amazon Chime SDK call analytics. Call analytics include voice analytics, which provides speaker search and voice tone analysis. These capabilities can be used with Amazon Transcribe and Transcribe Call Analytics to generate machine-learning-powered insights from real-time audio.
* api-change:``batch``: This feature allows Batch to support configuration of ephemeral storage size for jobs running on FARGATE
* api-change:``chime-sdk-voice``: This release adds Amazon Chime SDK call analytics. Call analytics include voice analytics, which provides speaker search and voice tone analysis. These capabilities can be used with Amazon Transcribe and Transcribe Call Analytics to generate machine-learning-powered insights from real-time audio.
* api-change:``pipes``: This release improves validation on the ARNs in the API model
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK now supports passthrough of ID3v2 tags for audio inputs to audio-only HLS outputs.
* api-change:``servicediscovery``: Reverted the throttling exception RequestLimitExceeded for AWS Cloud Map APIs introduced in SDK version 1.12.424 2023-03-09 to previous exception specified in the ErrorCode.
* api-change:``textract``: The AnalyzeDocument - Tables feature adds support for new elements in the API: table titles, footers, section titles, summary cells/tables, and table type.
* api-change:``networkmanager``: This release includes an update to create-transit-gateway-route-table-attachment, showing example usage for TransitGatewayRouteTableArn.
* api-change:``ivs-realtime``: Initial release of the Amazon Interactive Video Service RealTime API.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``ssm``: This Patch Manager release supports creating, updating, and deleting Patch Baselines for AmazonLinux2023, AlmaLinux.
* enhancement:dependency: Bump PyInstaller version to 5.8.
* api-change:``resiliencehub``: This release provides customers with the ability to import resources from within an EKS cluster and assess the resiliency of EKS cluster workloads.
* api-change:``chime-sdk-identity``: AppInstanceBots can be used to add a bot powered by Amazon Lex to chat channels.  ExpirationSettings provides automatic resource deletion for AppInstanceUsers.
* api-change:``iottwinmaker``: This release adds support of adding metadata when creating a new scene or updating an existing scene.
* enhancement:eks: Add user-alias argument to update-kubeconfig command. Implements `#5164 <https://github.com/aws/aws-cli/issues/5164>`__
* api-change:``guardduty``: Adds AutoEnableOrganizationMembers attribute to DescribeOrganizationConfiguration and UpdateOrganizationConfiguration APIs.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds two new APIs - CreateAutoMLJobV2 and DescribeAutoMLJobV2. Amazon SageMaker Notebook Instances now supports the ml.geospatial.interactive instance type.


2.11.5
======

* api-change:``workdocs``: This release adds a new API, SearchResources, which enable users to search through metadata and content of folders, documents, document versions and comments in a WorkDocs site.
* api-change:``iotsitewise``: Provide support for tagging of data streams and enabling tag based authorization for property alias
* api-change:``config``: This release adds resourceType enums for types released from October 2022 through February 2023.
* api-change:``mgn``: This release introduces the Import and export feature and expansion of the post-launch actions
* api-change:``ec2``: This release adds support for AWS Network Firewall, AWS PrivateLink, and Gateway Load Balancers to Amazon VPC Reachability Analyzer, and it makes the path destination optional as long as a destination address in the filter at source is provided.
* api-change:``billingconductor``: This release adds a new filter to ListAccountAssociations API and a new filter to ListBillingGroups API.
* api-change:``dms``: S3 setting to create AWS Glue Data Catalog. Oracle setting to control conversion of timestamp column. Support for Kafka SASL Plain authentication. Setting to map boolean from PostgreSQL to Redshift. SQL Server settings to force lob lookup on inline LOBs and to control access of database logs.
* api-change:``chime-sdk-messaging``: Amazon Chime SDK messaging customers can now manage streaming configuration for messaging data for archival and analysis.
* api-change:``neptune``: This release makes following few changes. db-cluster-identifier is now a required parameter of create-db-instance. describe-db-cluster will now return PendingModifiedValues and GlobalClusterIdentifier fields in the response.
* api-change:``s3outposts``: S3 On Outposts added support for endpoint status, and a failed endpoint reason, if any
* api-change:``cleanrooms``: GA Release of AWS Clean Rooms, Added Tagging Functionality
* api-change:``application-autoscaling``: With this release customers can now tag their Application Auto Scaling registered targets with key-value pairs and manage IAM permissions for all the tagged resources centrally.


2.11.4
======

* api-change:``migrationhubstrategy``: This release adds the binary analysis that analyzes IIS application DLLs on Windows and Java applications on Linux to provide anti-pattern report without configuring access to the source code.
* enhancement:configure: Add support for importing CSV credential files that have leading UTF-8 BOM. Fixes `#7721 <https://github.com/aws/aws-cli/issues/7721>`__.
* api-change:``securitylake``: Make Create/Get/ListSubscribers APIs return resource share ARN and name so they can be used to validate the RAM resource share to accept. GetDatalake can be used to track status of UpdateDatalake and DeleteDatalake requests.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``guardduty``: Updated 9 APIs for feature enablement to reflect expansion of GuardDuty to features. Added new APIs and updated existing APIs to support RDS Protection GA.
* api-change:``resource-explorer-2``: Documentation updates for APIs.
* api-change:``s3control``: Added support for S3 Object Lambda aliases.


2.11.3
======

* api-change:``secretsmanager``: The type definitions of SecretString and SecretBinary now have a minimum length of 1 in the model to match the exception thrown when you pass in empty values.
* api-change:``application-autoscaling``: Application Auto Scaling customers can now use mathematical functions to customize the metric used with Target Tracking policies within the policy configuration itself, saving the cost and effort of publishing the customizations as a separate metric.
* bugfix:``codeartifact login``: Prevent AWS CodeArtifact login command from hanging unexpectedly.
* api-change:``lakeformation``: This release updates the documentation regarding Get/Update DataCellsFilter
* api-change:``iam``: Documentation only updates to correct customer-reported issues
* api-change:``keyspaces``: Adding support for client-side timestamps
* api-change:``tnb``: This release adds tagging support to the following Network Instance APIs : Instantiate, Update, Terminate.
* api-change:``ivschat``: This release adds a new exception returned when calling AWS IVS chat UpdateLoggingConfiguration. Now UpdateLoggingConfiguration can return ConflictException when invalid updates are made in sequence to Logging Configurations.
* api-change:``appintegrations``: Adds FileConfiguration to Amazon AppIntegrations CreateDataIntegration supporting scheduled downloading of third party files into Amazon Connect from sources such as Microsoft SharePoint.
* api-change:``wisdom``: This release extends Wisdom CreateKnowledgeBase API to support SharePoint connector type by removing the @required trait for objectField
* api-change:``dataexchange``: This release enables data providers to license direct access to S3 objects encrypted with Customer Managed Keys (CMK) in AWS KMS through AWS Data Exchange. Subscribers can use these keys to decrypt, then use the encrypted S3 objects shared with them, without creating or managing copies.
* api-change:``directconnect``: describe-direct-connect-gateway-associations includes a new status, updating, indicating that the association is currently in-process of updating.
* api-change:``ec2``: This release adds a new DnsOptions key (PrivateDnsOnlyForInboundResolverEndpoint) to CreateVpcEndpoint and ModifyVpcEndpoint APIs.
* api-change:``s3control``: Added support for cross-account Multi-Region Access Points. Added support for S3 Replication for S3 on Outposts.


2.11.2
======

* api-change:``evidently``: Updated entity override documentation
* api-change:``quicksight``: This release has two changes: add state persistence feature for embedded dashboard and console in GenerateEmbedUrlForRegisteredUser API; add properties for hidden collapsed row dimensions in PivotTableOptions.
* api-change:``athena``: A new field SubstatementType is added to GetQueryExecution API, so customers have an error free way to detect the query type and interpret the result.
* api-change:``mediapackage-vod``: This release provides the date and time VOD resources were created.
* api-change:``connect``: This release adds a new API, GetMetricDataV2, which returns metric data for Amazon Connect.
* api-change:``route53resolver``: Add dual-stack and IPv6 support for Route 53 Resolver Endpoint,Add IPv6 target IP in Route 53 Resolver Forwarding Rule
* api-change:``sesv2``: This release introduces a new recommendation in Virtual Deliverability Manager Advisor, which detects missing or misconfigured Brand Indicator for Message Identification (BIMI) DNS records for customer sending identities.
* api-change:``redshift-data``: Added support for Redshift Serverless workgroup-arn wherever the WorkgroupName parameter is available.
* api-change:``networkmanager``: This update provides example usage for TransitGatewayRouteTableArn.
* api-change:``ec2``: Introducing Amazon EC2 C7g, M7g and R7g instances, powered by the latest generation AWS Graviton3 processors and deliver up to 25% better performance over Graviton2-based instances.
* api-change:``lakeformation``: This release adds two new API support "GetDataCellsFiler" and "UpdateDataCellsFilter", and also updates the corresponding documentation.
* api-change:``codeartifact``: This release introduces the generic package format, a mechanism for storing arbitrary binary assets. It also adds a new API, PublishPackageVersion, to allow for publishing generic packages.
* api-change:``dynamodb``: Adds deletion protection support to DynamoDB tables. Tables with deletion protection enabled cannot be deleted. Deletion protection is disabled by default, can be enabled via the CreateTable or UpdateTable APIs, and is visible in TableDescription. This setting is not replicated for Global Tables.
* api-change:``sagemaker``: Amazon SageMaker Inference now allows SSM access to customer's model container by setting the "EnableSSMAccess" parameter for a ProductionVariant in CreateEndpointConfig API.
* api-change:``mediapackage``: This release provides the date and time live resources were created.
* api-change:``sagemaker``: There needs to be a user identity to specify the SageMaker user who perform each action regarding the entity. However, these is a not a unified concept of user identity across SageMaker service that could be used today.
* api-change:``servicediscovery``: Updated all AWS Cloud Map APIs to provide consistent throttling exception (RequestLimitExceeded)


2.11.1
======

* enhancement:dependency: Update cryptography requirement from <38.0.5,>=3.3.2 to >=3.3.2,<39.0.3
* api-change:``medialive``: AWS Elemental MediaLive adds support for Nielsen watermark timezones.
* api-change:``account``: AWS Account alternate contact email addresses can now have a length of 254 characters and contain the character "|".
* api-change:``transcribe``: Amazon Transcribe now supports role access for these API operations: CreateVocabulary, UpdateVocabulary, CreateVocabularyFilter, and UpdateVocabularyFilter.
* api-change:``location``: Documentation update for the release of 3 additional map styles for use with Open Data Maps: Open Data Standard Dark, Open Data Visualization Light & Open Data Visualization Dark.
* api-change:``dynamodb``: Documentation updates for DynamoDB.
* bugfix:eks: Output JSON only for user entry in kubeconfig fixes `#7719 <https://github.com/aws/aws-cli/issues/7719>`__, fixes `#7723 <https://github.com/aws/aws-cli/issues/7723>`__, fixes `#7724 <https://github.com/aws/aws-cli/issues/7724>`__
* api-change:``macie2``: Documentation updates for Amazon Macie
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has improved handling for different input and output color space combinations.
* api-change:``dms``: This release adds DMS Fleet Advisor Target Recommendation APIs and exposes functionality for DMS Fleet Advisor. It adds functionality to start Target Recommendation calculation.
* api-change:``ec2``: This release adds support for a new boot mode for EC2 instances called 'UEFI Preferred'.
* api-change:``ivs``: Updated text description in DeleteChannel, Stream, and StreamSummary.


2.11.0
======

* api-change:``codecatalyst``: Published Dev Environments StopDevEnvironmentSession API
* api-change:``pipes``: This release fixes some input parameter range and patterns.
* api-change:``migrationhubstrategy``: This release updates the File Import API to allow importing servers already discovered by customers with reduced pre-requisites.
* api-change:``iot``: A recurring maintenance window is an optional configuration used for rolling out the job document to all devices in the target group observing a predetermined start time, duration, and frequency that the maintenance window occurs.
* api-change:``sagemaker``: Add a new field "EndpointMetrics" in SageMaker Inference Recommender "ListInferenceRecommendationsJobSteps" API response.
* enhancement:dependency: Add Python 3.11 support for source distribution
* api-change:``pricing``: This release adds 2 new APIs - ListPriceLists which returns a list of applicable price lists, and GetPriceListFileUrl which outputs a URL to retrieve your price lists from the generated file from ListPriceLists
* api-change:``pi``: This release adds a new field PeriodAlignment to allow the customer specifying the returned timestamp of time periods to be either the start or end time.
* feature:Python: Upgrade the embedded Python version to 3.11.
* api-change:``s3outposts``: S3 on Outposts introduces a new API ListOutpostsWithS3, with this API you can list all your Outposts with S3 capacity.
* api-change:``organizations``: This release introduces a new reason code, ACCOUNT_CREATION_NOT_COMPLETE, to ConstraintViolationException in CreateOrganization API.


2.10.4
======

* api-change:``devops-guru``: This release adds the description field on ListAnomaliesForInsight and DescribeAnomaly API responses for proactive anomalies.
* api-change:``lightsail``: This release adds Lightsail for Research feature support, such as GUI session access, cost estimates, stop instance on idle, and disk auto mount.
* api-change:``connectcases``: This release adds the ability to delete domains through the DeleteDomain API. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``servicecatalog``: Documentation updates for Service Catalog
* api-change:``kms``: AWS KMS is deprecating the RSAES_PKCS1_V1_5 wrapping algorithm option in the GetParametersForImport API that is used in the AWS KMS Import Key Material feature. AWS KMS will end support for this wrapping algorithm by October 1, 2023.
* api-change:``drs``: New fields were added to reflect availability zone data in source server and recovery instance description commands responses, as well as source server launch status.
* api-change:``securityhub``: New Security Hub APIs and updates to existing APIs that help you consolidate control findings and enable and disable controls across all supported standards
* api-change:``redshift``: Documentation updates for Redshift API bringing it in line with IAM best practices.
* api-change:``omics``: Minor model changes to accomodate batch imports feature
* api-change:``comprehend``: Amazon Comprehend now supports flywheels to help you train and manage new model versions for custom models.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for HDR10 to SDR tone mapping, and animated GIF video input sources.
* api-change:``managedblockchain``: This release adds support for tagging to the accessor resource in Amazon Managed Blockchain
* api-change:``ec2``: This release allows IMDS support to be set to v2-only on an existing AMI, so that all future instances launched from that AMI will use IMDSv2 by default.
* api-change:``internetmonitor``: CloudWatch Internet Monitor is a a new service within CloudWatch that will help application developers and network engineers continuously monitor internet performance metrics such as availability and performance between their AWS-hosted applications and end-users of these applications
* api-change:``connect``: StartTaskContact API now supports linked task creation with a new optional RelatedContactId parameter
* api-change:``lambda``: This release adds the ability to create ESMs with Document DB change streams as event source. For more information see  https://docs.aws.amazon.com/lambda/latest/dg/with-documentdb.html.
* api-change:``timestream-write``: This release adds the ability to ingest batched historical data or migrate data in bulk from S3 into Timestream using CSV files.


2.10.3
======

* api-change:``opensearch``: This release lets customers configure Off-peak window and software update related properties for a new/existing domain. It enhances the capabilities of StartServiceSoftwareUpdate API; adds 2 new APIs - ListScheduledActions & UpdateScheduledAction; and allows Auto-tune to make use of Off-peak window.
* api-change:``iotwireless``: In this release, we add additional capabilities for the FUOTA which allows user to configure the fragment size, the sending interval and the redundancy ratio of the FUOTA tasks
* api-change:``macie2``: This release adds support for a new finding type, Policy:IAMUser/S3BucketSharedWithCloudFront, and S3 bucket metadata that indicates if a bucket is shared with an Amazon CloudFront OAI or OAC.
* api-change:``appflow``: This release enables the customers to choose whether to use Private Link for Metadata and Authorization call when using a private Salesforce connections
* api-change:``location``: This release adds support for using Maps APIs with an API Key in addition to AWS Cognito. This includes support for adding, listing, updating and deleting API Keys.
* api-change:``ecs``: This release supports deleting Amazon ECS task definitions that are in the INACTIVE state.
* api-change:``rum``: CloudWatch RUM now supports CloudWatch Custom Metrics
* api-change:``chime-sdk-voice``: This release introduces support for Voice Connector media metrics in the Amazon Chime SDK Voice namespace
* api-change:``wafv2``: You can now associate an AWS WAF v2 web ACL with an AWS App Runner service.
* api-change:``ssm``: Document only update for Feb 2023
* api-change:``guardduty``: Updated API and data types descriptions for CreateFilter, UpdateFilter, and TriggerDetails.
* api-change:``datasync``: AWS DataSync has relaxed the minimum length constraint of AccessKey for Object Storage locations to 1.
* api-change:``cloudfront``: CloudFront now supports block lists in origin request policies so that you can forward all headers, cookies, or query string from viewer requests to the origin *except* for those specified in the block list.
* api-change:``grafana``: Doc-only update. Updated information on attached role policies for customer provided roles


2.10.2
======

* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``glue``: Release of Delta Lake Data Lake Format for Glue Studio Service
* api-change:``tnb``: This is the initial SDK release for AWS Telco Network Builder (TNB). AWS Telco Network Builder is a network automation service that helps you deploy and manage telecom networks.
* bugfix:SSO: Fixes aws/aws-cli`#7496 <https://github.com/aws/aws-cli/issues/7496>`__ by using the correct profile name rather than the one set in the session.
* api-change:``quicksight``: S3 data sources now accept a custom IAM role.
* api-change:``connect``: Reasons for failed diff has been approved by SDK Reviewer
* api-change:``resiliencehub``: In this release we improved resilience hub application creation and maintenance by introducing new resource and app component crud APIs, improving visibility and maintenance of application input sources and added support for additional information attributes to be provided by customers.
* api-change:``auditmanager``: This release introduces a ServiceQuotaExceededException to the UpdateAssessmentFrameworkShare API operation.
* api-change:``apprunner``: This release supports removing MaxSize limit for AutoScalingConfiguration.


2.10.1
======

* api-change:``grafana``: With this release Amazon Managed Grafana now supports inbound Network Access Control that helps you to restrict user access to your Grafana workspaces
* api-change:``glue``: Fix DirectJDBCSource not showing up in CLI code gen
* api-change:``cloudtrail``: This release adds an InsufficientEncryptionPolicyException type to the StartImport endpoint
* api-change:``frauddetector``: This release introduces Lists feature which allows customers to reference a set of values in Fraud Detector's rules. With Lists, customers can dynamically manage these attributes in real time. Lists can be created/deleted and its contents can be modified using the Fraud Detector API.
* api-change:``rds``: Database Activity Stream support for RDS for SQL Server.
* api-change:``ivs``: Doc-only update. Updated text description in DeleteChannel, Stream, and StreamSummary.
* api-change:``efs``: Update efs command to latest version
* api-change:``wafv2``: Added a notice for account takeover prevention (ATP). The interface incorrectly lets you to configure ATP response inspection in regional web ACLs in Region US East (N. Virginia), without returning an error. ATP response inspection is only available in web ACLs that protect CloudFront distributions.
* api-change:``wafv2``: For protected CloudFront distributions, you can now use the AWS WAF Fraud Control account takeover prevention (ATP) managed rule group to block new login attempts from clients that have recently submitted too many failed login attempts.
* api-change:``privatenetworks``: This release introduces a new StartNetworkResourceUpdate API, which enables return/replacement of hardware from a NetworkSite.
* api-change:``emr``: Update emr command to latest version


2.10.0
======

* api-change:``connect``: This update provides the Wisdom session ARN for contacts enabled for Wisdom in the chat channel.
* api-change:``appconfigdata``: AWS AppConfig now offers the option to set a version label on hosted configuration versions. If a labeled hosted configuration version is deployed, its version label is available in the GetLatestConfiguration response.
* api-change:``datasync``: With this launch, we are giving customers the ability to use older SMB protocol versions, enabling them to use DataSync to copy data to and from their legacy storage arrays.
* api-change:``ec2``: Adds support for waiters that automatically poll for an imported snapshot until it reaches the completed state.
* api-change:``autoscaling``: You can now either terminate/replace, ignore, or wait for EC2 Auto Scaling instances on standby or protected from scale in. Also, you can also roll back changes from a failed instance refresh.
* bugfix:``s3``: AWS CLI no longer overwrites user supplied `Content-Encoding` with `aws-chunked` when user also supplies `ChecksumAlgorithm`.
* feature:Source Distribution: Add supported autotools interface for building from source.
* api-change:``sns``: This release adds support for SNS X-Ray active tracing as well as other updates.
* api-change:``ec2``: With this release customers can turn host maintenance on or off when allocating or modifying a supported dedicated host. Host maintenance is turned on by default for supported hosts.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for selecting algorithms in CreateAutoMLJob API.
* api-change:``appconfig``: AWS AppConfig now offers the option to set a version label on hosted configuration versions. Version labels allow you to identify specific hosted configuration versions based on an alternate versioning scheme that you define.
* api-change:``account``: This release of the Account Management API enables customers to view and manage whether AWS Opt-In Regions are enabled or disabled for their Account. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html
* api-change:``polly``: Amazon Polly adds two new neural Japanese voices - Kazuha, Tomoko
* api-change:``snowball``: Adds support for EKS Anywhere on Snowball. AWS Snow Family customers can now install EKS Anywhere service on Snowball Edge Compute Optimized devices.


2.9.23
======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``backup``: This release added one attribute (resource name) in the output model of our 9 existing APIs in AWS backup so that customers will see the resource name at the output. No input required from Customers.
* api-change:``workspaces``: Removed Windows Server 2016 BYOL and made changes based on IAM campaign.
* api-change:``evidently``: Updated entity overrides parameter to accept up to 2500 overrides or a total of 40KB.
* api-change:``chime-sdk-meetings``: Documentation updates for Chime Meetings SDK
* api-change:``cloudfront``: CloudFront Origin Access Control extends support to AWS Elemental MediaStore origins.
* api-change:``lakeformation``: This release removes the LFTagpolicyResource expression limits.
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``emr-containers``: EMR on EKS allows configuring retry policies for job runs through the StartJobRun API. Using retry policies, a job cause a driver pod to be restarted automatically if it fails or is deleted. The job's status can be seen in the DescribeJobRun and ListJobRun APIs and monitored using CloudWatch events.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``workdocs``: Doc only update for the WorkDocs APIs.
* api-change:``migration-hub-refactor-spaces``: This release adds support for creating environments with a network fabric type of NONE
* api-change:``glue``: DirectJDBCSource + Glue 4.0 streaming options


2.9.22
======

* api-change:``proton``: Add new GetResourcesSummary API
* api-change:``customer-profiles``: This release deprecates the PartyType and Gender enum data types from the Profile model and replaces them with new PartyTypeString and GenderString attributes, which accept any string of length up to 255.
* api-change:``outposts``: Adds OrderType to Order structure. Adds PreviousOrderId and PreviousLineItemId to LineItem structure. Adds new line item status REPLACED. Increases maximum length of pagination token.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added improved scene change detection capabilities and a bandwidth reduction filter, along with video quality enhancements, to the AVC encoder.
* api-change:``compute-optimizer``: AWS Compute optimizer can now infer if Kafka is running on an instance.
* api-change:``frauddetector``: My AWS Service (Amazon Fraud Detector) - This release introduces Cold Start Model Training which optimizes training for small datasets and adds intelligent methods for treating unlabeled data. You can now train Online Fraud Insights or Transaction Fraud Insights models with minimal historical-data.
* api-change:``redshift``: Corrects descriptions of the parameters for the API operations RestoreFromClusterSnapshot, RestoreTableFromClusterSnapshot, and CreateCluster.
* api-change:``transfer``: Updated the documentation for the ImportCertificate API call, and added examples.


2.9.21
======

* api-change:``redshift``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``devops-guru``: This release adds filter support ListAnomalyForInsight API.
* api-change:``appconfig``: AWS AppConfig introduces KMS customer-managed key (CMK) encryption of configuration data, along with AWS Secrets Manager as a new configuration data source. S3 objects using SSE-KMS encryption and SSM Parameter Store SecureStrings are also now supported.
* api-change:``keyspaces``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``forecast``: This release will enable customer select INCREMENTAL as ImportModel in Forecast's CreateDatasetImportJob API. Verified latest SDK containing required attribute, following https://w.amazon.com/bin/view/AWS-Seer/Launch/Trebuchet/
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``sso-admin``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``sns``: Additional attributes added for set-topic-attributes.
* api-change:``quicksight``: QuickSight support for Radar Chart and Dashboard Publish Options
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``connect``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``mediatailor``: The AWS Elemental MediaTailor SDK for Channel Assembly has added support for program updates, and the ability to clip the end of VOD sources in programs.


2.9.20
======

* api-change:``glacier``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``imagebuilder``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``opensearch``: Amazon OpenSearch Service adds the option for a VPC endpoint connection between two domains when the local domain uses OpenSearch version 1.3 or 2.3. You can now use remote reindex to copy indices from one VPC domain to another without a reverse proxy.
* api-change:``securityhub``: New fields have been added to the AWS Security Finding Format. Compliance.SecurityControlId is a unique identifier for a security control across standards. Compliance.AssociatedStandards contains all enabled standards in which a security control is enabled.
* api-change:``elasticbeanstalk``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``fis``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``kafka``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``application-autoscaling``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``appstream``: Fixing the issue where Appstream waiters hang for fleet_started and fleet_stopped.
* api-change:``serverlessrepo``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``discovery``: Update ImportName validation to 255 from the current length of 100
* api-change:``connectparticipant``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``cloudformation``: This feature provides a method of obtaining which regions a stackset has stack instances deployed in.
* api-change:``kinesis``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``ec2``: This launch allows customers to associate up to 8 IP addresses to their NAT Gateways to increase the limit on concurrent connections to a single destination by eight times from 55K to 440K.
* api-change:``mediatailor``: This release introduces the As Run logging type, along with API and documentation updates.
* api-change:``polly``: Amazon Polly adds two new neural American English voices - Ruth, Stephen
* api-change:``cloudtrail-data``: Add CloudTrail Data Service to enable users to ingest activity events from non-AWS sources into CloudTrail Lake.
* api-change:``iot``: Added support for IoT Rules Engine Cloudwatch Logs action batch mode.
* api-change:``greengrass``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``dlm``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``swf``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``mediaconvert``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``groundstation``: DigIF Expansion changes to the Customer APIs.
* api-change:``appsync``: This release introduces the feature to support EventBridge as AppSync data source.
* api-change:``outposts``: Adding support for payment term in GetOrder, CreateOrder responses.
* api-change:``support``: This fixes incorrect endpoint construction when a customer is explicitly setting a region.
* api-change:``ec2``: We add Prefix Lists as a new route destination option for LocalGatewayRoutes. This will allow customers to create routes to Prefix Lists. Prefix List routes will allow customers to group individual CIDR routes with the same target into a single route.
* api-change:``codeartifact``: This release introduces a new DeletePackage API, which enables deletion of a package and all of its versions from a repository.
* api-change:``greengrassv2``: Enabled FIPS endpoints for GovCloud (US) in SDK.
* api-change:``cloudtrail``: Add new "Channel" APIs to enable users to manage channels used for CloudTrail Lake integrations, and "Resource Policy" APIs to enable users to manage the resource-based permissions policy attached to a channel.
* api-change:``accessanalyzer``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports more completion criteria for Hyperparameter Optimization.
* api-change:``outposts``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``sagemaker``: This release supports running SageMaker Training jobs with container images that are in a private Docker registry.
* api-change:``clouddirectory``: Enabled FIPS endpoints for GovCloud (US) regions in SDK.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version


2.9.19
======

* api-change:``iotfleetwise``: Add model validation to BatchCreateVehicle and BatchUpdateVehicle operations that invalidate requests with an empty vehicles list.
* api-change:``ec2``: This release adds new functionality that allows customers to provision IPv6 CIDR blocks through Amazon VPC IP Address Manager (IPAM) as well as allowing customers to utilize IPAM Resource Discovery APIs.
* api-change:``cloudformation``: Enabled FIPS aws-us-gov endpoints in SDK.
* api-change:``s3``: Allow FIPS to be used with path-style URLs.
* api-change:``m2``: Add returnCode, batchJobIdentifier in GetBatchJobExecution response, for user to view the batch job execution result & unique identifier from engine. Also removed unused headers from REST APIs
* enhancement:openssl: The bundled OpenSSL versions for the Linux installers have been upgraded from 1.0.2 to 1.1.1
* api-change:``sagemaker``: SageMaker Inference Recommender now decouples from Model Registry and could accept Model Name to invoke inference recommendations job; Inference Recommender now provides CPU/Memory Utilization metrics data in recommendation output.
* api-change:``polly``: Add 5 new neural voices - Sergio (es-ES), Andres (es-MX), Remi (fr-FR), Adriano (it-IT) and Thiago (pt-BR).
* api-change:``events``: Update events command to latest version
* api-change:``redshift-serverless``: Added query monitoring rules as possible parameters for create and update workgroup operations.
* api-change:``s3control``: Add additional endpoint tests for S3 Control. Fix missing endpoint parameters for PutBucketVersioning and GetBucketVersioning. Prior to this fix, those operations may have resulted in an invalid endpoint being resolved.
* enhancement:ec2 customization: Update --cidr parameter description to indicate the address range must be IPv4
* api-change:``sts``: Doc only change to update wording in a key topic


2.9.18
======

* api-change:``databrew``: Enabled FIPS us-gov-west-1 endpoints in SDK.
* api-change:``ivs``: API and Doc update. Update to arns field in BatchGetStreamKey. Also updates to operations and structures.
* api-change:``quicksight``: This release adds support for data bars in QuickSight table and increases pivot table field well limit.
* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Melbourne) Region (ap-southeast-4) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``sagemaker``: Amazon SageMaker Inference now supports P4de instance types.
* api-change:``lambda``: Release Lambda RuntimeManagementConfig, enabling customers to better manage runtime updates to their Lambda functions. This release adds two new APIs, GetRuntimeManagementConfig and PutRuntimeManagementConfig, as well as support on existing Create/Get/Update function APIs.
* api-change:``ec2``: C6in, M6in, M6idn, R6in and R6idn instances are powered by 3rd Generation Intel Xeon Scalable processors (code named Ice Lake) with an all-core turbo frequency of 3.5 GHz.
* enhancement:``gamelift upload-build``: Add ``--server-sdk-version`` parameter to the ``upload-build`` command
* api-change:``ssm-sap``: This release provides updates to documentation and support for listing operations performed by AWS Systems Manager for SAP.


2.9.17
======

* api-change:``sagemaker``: HyperParameterTuningJobs now allow passing environment variables into the corresponding TrainingJobs
* api-change:``appflow``: Adding support for Salesforce Pardot connector in Amazon AppFlow.
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``medialive``: AWS Elemental MediaLive adds support for SCTE 35 preRollMilliSeconds.
* api-change:``logs``: Bug fix - Removed the regex pattern validation from CoralModel to avoid potential security issue.
* api-change:``ec2``: Adds SSM Parameter Resource Aliasing support to EC2 Launch Templates. Launch Templates can now store parameter aliases in place of AMI Resource IDs. CreateLaunchTemplateVersion and DescribeLaunchTemplateVersions now support a convenience flag, ResolveAlias, to return the resolved parameter value.
* api-change:``panorama``: Added AllowMajorVersionUpdate option to OTAJobConfig to make appliance software major version updates opt-in.
* api-change:``efs``: Update efs command to latest version
* api-change:``connect``: Amazon Connect Chat introduces Persistent Chat, allowing customers to resume previous conversations with context and transcripts carried over from previous chats, eliminating the need to repeat themselves and allowing agents to provide personalized service with access to entire conversation history.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``wafv2``: Improved the visibility of the guidance for updating AWS WAF resources, such as web ACLs and rule groups.
* api-change:``ivschat``: Updates the range for a Chat Room's maximumMessageRatePerSecond field.
* enhancement:Python: Update Python interpreter version range support to 3.11
* api-change:``groundstation``: Add configurable prepass and postpass times for DataflowEndpointGroup. Add Waiter to allow customers to wait for a contact that was reserved through ReserveContact
* api-change:``glue``: Release Glue Studio Hudi Data Lake Format for SDK/CLI
* api-change:``connectparticipant``: This release updates Amazon Connect Participant's GetTranscript api to provide transcripts of past chats on a persistent chat session.
* api-change:``opensearch``: This release adds the enhanced dry run option, that checks for validation errors that might occur when deploying configuration changes and provides a summary of these errors, if any. The feature will also indicate whether a blue/green deployment will be required to apply a change.


2.9.16
======

* api-change:``cloud9``: Added minimum value to AutomaticStopTimeMinutes parameter.
* api-change:``imagebuilder``: Add support for AWS Marketplace product IDs as input during CreateImageRecipe for the parent-image parameter. Add support for listing third-party components.
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``outposts``: This release adds POWER_30_KVA as an option for PowerDrawKva. PowerDrawKva is part of the RackPhysicalProperties structure in the CreateSite request.
* api-change:``network-firewall``: Network Firewall now allows creation of dual stack endpoints, enabling inspection of IPv6 traffic.
* api-change:``billingconductor``: This release adds support for SKU Scope for pricing plans.
* api-change:``connect``: This release updates the responses of UpdateContactFlowContent, UpdateContactFlowMetadata, UpdateContactFlowName and DeleteContactFlow API with empty responses.
* enhancement:dependency: Update build dependency on PyInstaller to version 5.7.0
* api-change:``resource-groups``: AWS Resource Groups customers can now turn on Group Lifecycle Events in their AWS account. When you turn this on, Resource Groups monitors your groups for changes to group state or membership. Those changes are sent to Amazon EventBridge as events that you can respond to using rules you create.


2.9.15
======

* api-change:``kendra``: This release adds support to new document types - RTF, XML, XSLT, MS_EXCEL, CSV, JSON, MD
* api-change:``cleanrooms``: Initial release of AWS Clean Rooms
* api-change:``lambda``: Add support for MaximumConcurrency parameter for SQS event source. Customers can now limit the maximum concurrent invocations for their SQS Event Source Mapping.
* api-change:``logs``: Bug fix: logGroupName is now not a required field in GetLogEvents, FilterLogEvents, GetLogGroupFields, and DescribeLogStreams APIs as logGroupIdentifier can be provided instead
* enhancement:dependencies: Bumped colorama version range to >=0.2.5,<0.4.7
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for compact DASH manifest generation, audio normalization using TruePeak measurements, and the ability to clip the sample range in the color corrector.
* api-change:``secretsmanager``: Update documentation for new ListSecrets and DescribeSecret parameters


2.9.14
======

* api-change:``rds``: This release adds support for configuring allocated storage on the CreateDBInstanceReadReplica, RestoreDBInstanceFromDBSnapshot, and RestoreDBInstanceToPointInTime APIs.
* api-change:``workspaces-web``: This release adds support for a new portal authentication type: AWS IAM Identity Center (successor to AWS Single Sign-On).
* api-change:``auditmanager``: This release introduces a new data retention option in your Audit Manager settings. You can now use the DeregistrationPolicy parameter to specify if you want to delete your data when you deregister Audit Manager.
* api-change:``acm-pca``: Added revocation parameter validation: bucket names must match S3 bucket naming rules and CNAMEs conform to RFC2396 restrictions on the use of special characters in URIs.
* api-change:``kendra-ranking``: Introducing Amazon Kendra Intelligent Ranking, a new set of Kendra APIs that leverages Kendra semantic ranking capabilities to improve the quality of search results from other search services (i.e. OpenSearch, ElasticSearch, Solr).
* api-change:``ecr-public``: This release for Amazon ECR Public makes several change to bring the SDK into sync with the API.
* api-change:``ram``: Enabled FIPS aws-us-gov endpoints in SDK.
* api-change:``network-firewall``: Network Firewall now supports the Suricata rule action reject, in addition to the actions pass, drop, and alert.
* bugfix:``codeartifact login``: Fix parsing of dotnet output for aws codeartifact login command; fixes `#6197 <https://github.com/aws/aws-cli/issues/6197>`__
* api-change:``location``: This release adds support for two new route travel models, Bicycle and Motorcycle which can be used with Grab data source.


2.9.13
======

* api-change:``iotfleetwise``: Update documentation - correct the epoch constant value of default value for expiryTime field in CreateCampaign request.
* api-change:``rds``: This release adds support for specifying which certificate authority (CA) to use for a DB instance's server certificate during DB instance creation, as well as other CA enhancements.
* api-change:``emr-serverless``: Adds support for customized images. You can now provide runtime images when creating or updating EMR Serverless Applications.
* api-change:``apprunner``: This release adds support of securely referencing secrets and configuration data that are stored in Secrets Manager and SSM Parameter Store by adding them as environment secrets in your App Runner service.
* api-change:``logs``: Update to remove sequenceToken as a required field in PutLogEvents calls.
* api-change:``connect``: Documentation update for a new Initiation Method value in DescribeContact API
* api-change:``mwaa``: MWAA supports Apache Airflow version 2.4.3.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``securitylake``: Allow CreateSubscriber API to take string input that allows setting more descriptive SubscriberDescription field. Make souceTypes field required in model level for UpdateSubscriberRequest as it is required for every API call on the backend. Allow ListSubscribers take any String as nextToken param.
* api-change:``cloudfront``: Extend response headers policy to support removing headers from viewer responses
* api-change:``ssm``: Adding support for QuickSetup Document Type in Systems Manager
* api-change:``amplifybackend``: Updated GetBackendAPIModels response to include ModelIntrospectionSchema json string
* api-change:``application-autoscaling``: Customers can now use the existing DescribeScalingActivities API to also see the detailed and machine-readable reasons for Application Auto Scaling not scaling their resources and, if needed, take the necessary corrective actions.


2.9.12
======

* api-change:``wisdom``: This release extends Wisdom CreateContent and StartContentUpload APIs to support PDF and MicrosoftWord docx document uploading.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``secretsmanager``: Added owning service filter, include planned deletion flag, and next rotation date response parameter in ListSecrets.
* api-change:``route53-recovery-control-config``: Added support for Python paginators in the route53-recovery-control-config List* APIs.
* api-change:``elasticache``: This release allows you to modify the encryption in transit setting, for existing Redis clusters. You can now change the TLS configuration of your Redis clusters without the need to re-build or re-provision the clusters or impact application availability.
* api-change:``network-firewall``: AWS Network Firewall now provides status messages for firewalls to help you troubleshoot when your endpoint fails.
* api-change:``emr``: Update emr command to latest version
* api-change:``rds``: This release adds support for Custom Engine Version (CEV) on RDS Custom SQL Server.


2.9.11
======

* api-change:``memorydb``: This release adds support for MemoryDB Reserved nodes which provides a significant discount compared to on-demand node pricing. Reserved nodes are not physical nodes, but rather a billing discount applied to the use of on-demand nodes in your account.
* api-change:``detective``: This release adds a missed AccessDeniedException type to several endpoints.
* api-change:``connect``: Support for Routing Profile filter, SortCriteria, and grouping by Routing Profiles for GetCurrentMetricData API. Support for RoutingProfiles, UserHierarchyGroups, and Agents as filters, NextStatus and AgentStatusName for GetCurrentUserData. Adds ApproximateTotalCount to both APIs.
* api-change:``fsx``: Fix a bug where a recent release might break certain existing SDKs.
* api-change:``connectparticipant``: Amazon Connect Chat introduces the Message Receipts feature. This feature allows agents and customers to receive message delivered and read receipts after they send a chat message.
* api-change:``transfer``: Add additional operations to throw ThrottlingExceptions
* api-change:``inspector2``: Amazon Inspector adds support for scanning NodeJS 18.x and Go 1.x AWS Lambda function runtimes.


2.9.10
======

* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``ssm``: Doc-only updates for December 2022.
* api-change:``iotdeviceadvisor``: This release adds the following new features: 1) Documentation updates for IoT Device Advisor APIs. 2) Updated required request parameters for IoT Device Advisor APIs. 3) Added new service feature: ability to provide the test endpoint when customer executing the StartSuiteRun API.
* api-change:``connect``: Amazon Connect Chat now allows for JSON (application/json) message types to be sent as part of the initial message in the StartChatContact API.
* api-change:``license-manager-linux-subscriptions``: AWS License Manager now offers cross-region, cross-account tracking of commercial Linux subscriptions on AWS. This includes subscriptions purchased as part of EC2 subscription-included AMIs, on the AWS Marketplace, or brought to AWS via Red Hat Cloud Access Program.
* api-change:``macie2``: This release adds support for analyzing Amazon S3 objects that use the S3 Glacier Instant Retrieval (Glacier_IR) storage class.
* api-change:``rds``: Add support for managing master user password in AWS Secrets Manager for the DBInstance and DBCluster.
* api-change:``scheduler``: Updated the ListSchedules and ListScheduleGroups APIs to allow the NamePrefix field to start with a number. Updated the validation for executionRole field to support any role name.
* api-change:``support``: Documentation updates for the AWS Support API
* api-change:``compute-optimizer``: This release enables AWS Compute Optimizer to analyze and generate optimization recommendations for ecs services running on Fargate.
* api-change:``kinesis-video-webrtc-storage``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``connect``: Amazon Connect Chat introduces the Idle Participant/Autodisconnect feature, which allows users to set timeouts relating to the activity of chat participants, using the new UpdateParticipantRoleConfig API.
* api-change:``connectparticipant``: Amazon Connect Chat now allows for JSON (application/json) message types to be sent in the SendMessage API.
* api-change:``transfer``: This release adds support for Decrypt as a workflow step type.
* api-change:``sagemaker``: This release enables adding RStudio Workbench support to an existing Amazon SageMaker Studio domain. It allows setting your RStudio on SageMaker environment configuration parameters and also updating the RStudioConnectUrl and RStudioPackageManagerUrl parameters for existing domains


2.9.9
=====

* api-change:``cloudfront``: Updated documentation for CloudFront
* api-change:``glue``: This release adds support for AWS Glue Crawler with native DeltaLake tables, allowing Crawlers to classify Delta Lake format tables and catalog them for query engines to query against.
* api-change:``medialive``: This release adds support for two new features to AWS Elemental MediaLive. First, you can now burn-in timecodes to your MediaLive outputs. Second, we now now support the ability to decode Dolby E audio when it comes in on an input.
* api-change:``ecs``: This release adds support for container port ranges in ECS, a new capability that allows customers to provide container port ranges to simplify use cases where multiple ports are in use in a container. This release updates TaskDefinition mutation APIs and the Task description APIs.
* api-change:``lookoutequipment``: This release adds support for listing inference schedulers by status.
* api-change:``ec2``: Adds support for pagination in the EC2 DescribeImages API.
* api-change:``resource-explorer-2``: Documentation updates for AWS Resource Explorer.
* api-change:``efs``: Update efs command to latest version
* api-change:``datasync``: AWS DataSync now supports the use of tags with task executions. With this new feature, you can apply tags each time you execute a task, giving you greater control and management over your task executions.
* api-change:``backup-gateway``: This release adds support for VMware vSphere tags, enabling customer to protect VMware virtual machines using tag-based policies for AWS tags mapped from vSphere tags. This release also adds support for customer-accessible gateway-hypervisor interaction log and upload bandwidth rate limit schedule.
* api-change:``sagemaker``: AWS sagemaker - Features: This release adds support for random seed, it's an integer value used to initialize a pseudo-random number generator. Setting a random seed will allow the hyperparameter tuning search strategies to produce more consistent configurations for the same tuning job.
* api-change:``kinesisvideo``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``connect``: Added support for "English - New Zealand" and "English - South African" to be used with Amazon Connect Custom Vocabulary APIs.
* api-change:``rds``: Add support for --enable-customer-owned-ip to RDS create-db-instance-read-replica API for RDS on Outposts.
* api-change:``appflow``: This release updates the ListConnectorEntities API action so that it returns paginated responses that customers can retrieve with next tokens.
* api-change:``location``: This release adds support for a new style, "VectorOpenDataStandardLight" which can be used with the new data source, "Open Data Maps (Preview)".
* api-change:``kinesis-video-webrtc-storage``: Amazon Kinesis Video Streams offers capabilities to stream video and audio in real-time via WebRTC to the cloud for storage, playback, and analytical processing. Customers can use our enhanced WebRTC SDK and cloud APIs to enable real-time streaming, as well as media ingestion to the cloud.
* api-change:``m2``: Adds an optional create-only `KmsKeyId` property to Environment and Application resources.
* api-change:``batch``: Adds isCancelled and isTerminated to DescribeJobs response.
* api-change:``sagemaker``: SageMaker Inference Recommender now allows customers to load tests their models on various instance types using private VPC.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for new objective metrics in CreateAutoMLJob API.
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for AwsEc2LaunchTemplate, AwsSageMakerNotebookInstance, AwsWafv2WebAcl and AwsWafv2RuleGroup.
* api-change:``kinesis``: Added StreamARN parameter for Kinesis Data Streams APIs. Added a new opaque pagination token for ListStreams. SDKs will auto-generate Account Endpoint when accessing Kinesis Data Streams.
* api-change:``nimble``: Amazon Nimble Studio now supports configuring session storage volumes and persistence, as well as backup and restore sessions through launch profiles.
* api-change:``route53domains``: Use Route 53 domain APIs to change owner, create/delete DS record, modify IPS tag, resend authorization. New: AssociateDelegationSignerToDomain, DisassociateDelegationSignerFromDomain, PushDomain, ResendOperationAuthorization. Updated: UpdateDomainContact, ListOperations, CheckDomainTransferability.
* api-change:``ecs``: This release adds support for alarm-based rollbacks in ECS, a new feature that allows customers to add automated safeguards for Amazon ECS service rolling updates.
* api-change:``eks``: Add support for Windows managed nodes groups.
* api-change:``athena``: Add missed InvalidRequestException in GetCalculationExecutionCode,StopCalculationExecution APIs. Correct required parameters (Payload and Type) in UpdateNotebook API. Change Notebook size from 15 Mb to 10 Mb.
* api-change:``transcribe``: Enable our batch transcription jobs for Swedish and Vietnamese.
* api-change:``sagemaker``: AWS Sagemaker - Sagemaker Images now supports Aliases as secondary identifiers for ImageVersions. SageMaker Images now supports additional metadata for ImageVersions for better images management.
* api-change:``iotfleetwise``: Updated error handling for empty resource names in "UpdateSignalCatalog" and "GetModelManifest" operations.
* api-change:``guardduty``: This release provides the valid characters for the Description and Name field.
* api-change:``translate``: Raised the input byte size limit of the Text field in the TranslateText API to 10000 bytes.


2.9.8
=====

* api-change:``ce``: This release supports percentage-based thresholds on Cost Anomaly Detection alert subscriptions.
* api-change:``redshift-data``: This release adds a new --client-token field to ExecuteStatement and BatchExecuteStatement operations. Customers can now run queries with the additional client token parameter to ensures idempotency.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``networkmanager``: Appliance Mode support for AWS Cloud WAN.
* api-change:``sagemaker-metrics``: Update SageMaker Metrics documentation.


2.9.7
=====

* api-change:``logs``: Doc-only update for CloudWatch Logs, for Tagging Permissions clarifications
* api-change:``migration-hub-refactor-spaces``: This release adds support for Lambda alias service endpoints. Lambda alias ARNs can now be passed into CreateService.
* api-change:``sagemaker-metrics``: This release introduces support SageMaker Metrics APIs.
* api-change:``rekognition``: Adds support for "aliases" and "categories", inclusion and exclusion filters for labels and label categories, and aggregating labels by video segment timestamps for Stored Video Label Detection APIs.
* enhancement:Parsers: Support parsing query error codes for JSON protocol
* bugfix:Endpoint provider: Updates ARN parsing ``resourceId`` delimiters
* api-change:``kinesisvideo``: This release adds support for public preview of Kinesis Video Stream at Edge enabling customers to provide configuration for the Kinesis Video Stream EdgeAgent running on an on-premise IoT device. Customers can now locally record from cameras and stream videos to the cloud on configured schedule.
* api-change:``rds``: This deployment adds ClientPasswordAuthType field to the Auth structure of the DBProxy.
* api-change:``lookoutvision``: This documentation update adds kms:GenerateDataKey as a required permission to StartModelPackagingJob.
* api-change:``rds``: Update the RDS API model to support copying option groups during the CopyDBSnapshot operation
* api-change:``ec2``: This release updates DescribeFpgaImages to show supported instance types of AFIs in its response.
* api-change:``mediapackage-vod``: This release provides the approximate number of assets in a packaging group.
* api-change:``cloudtrail``: Merging mainline branch for service model into mainline release branch. There are no new APIs.
* api-change:``iotfleetwise``: Deprecated assignedValue property for actuators and attributes.  Added a message to invalid nodes and invalid decoder manifest exceptions.
* api-change:``customer-profiles``: This release allows custom strings in PartyType and Gender through 2 new attributes in the CreateProfile and UpdateProfile APIs: PartyTypeString and GenderString.
* api-change:``medialive``: Link devices now support buffer size (latency) configuration. A higher latency value means a longer delay in transmitting from the device to MediaLive, but improved resiliency. A lower latency value means a shorter delay, but less resiliency.
* api-change:``wafv2``: Documents the naming requirement for logging destinations that you use with web ACLs.


2.9.6
=====

* api-change:``cloudfront``: Introducing UpdateDistributionWithStagingConfig that can be used to promote the staging configuration to the production.
* api-change:``ce``: This release adds the LinkedAccountName field to the GetAnomalies API response under RootCause
* api-change:``autoscaling``: Adds support for metric math for target tracking scaling policies, saving you the cost and effort of publishing a custom metric to CloudWatch. Also adds support for VPC Lattice by adding the Attach/Detach/DescribeTrafficSources APIs and a new health check type to the CreateAutoScalingGroup API.
* api-change:``kms``: Updated examples and exceptions for External Key Store (XKS).
* api-change:``iottwinmaker``: This release adds the following new features: 1) New APIs for managing a continuous sync of assets and asset models from AWS IoT SiteWise. 2) Support user friendly names for component types (ComponentTypeName) and properties (DisplayName).
* api-change:``eks``: Adds support for EKS add-ons configurationValues fields and DescribeAddonConfiguration function
* api-change:``migrationhubstrategy``: This release adds known application filtering, server selection for assessments, support for potential recommendations, and indications for configuration and assessment status. For more information, see the AWS Migration Hub documentation at https://docs.aws.amazon.com/migrationhub/index.html


2.9.5
=====

* api-change:``polly``: Add language code for Finnish (fi-FI)
* api-change:``proton``: CreateEnvironmentAccountConnection RoleArn input is now optional
* api-change:``rds``: This release adds the BlueGreenDeploymentNotFoundFault to the AddTagsToResource, ListTagsForResource, and RemoveTagsFromResource operations.
* api-change:``connect``: This release provides APIs that enable you to programmatically manage rules for Contact Lens conversational analytics and third party applications. For more information, see   https://docs.aws.amazon.com/connect/latest/APIReference/rules-api.html
* api-change:``sagemaker-featurestore-runtime``: For online + offline Feature Groups, added ability to target PutRecord and DeleteRecord actions to only online store, or only offline store. If target store parameter is not specified, actions will apply to both stores.
* api-change:``medialive``: Updates to Event Signaling and Management (ESAM) API and documentation.
* bugfix:``codeartifact login``: Ignore always-auth errors for CodeArtifact login command; fixes `#7434 <https://github.com/aws/aws-cli/issues/7434>`__
* api-change:``sns``: This release adds the message payload-filtering feature to the SNS Subscribe, SetSubscriptionAttributes, and GetSubscriptionAttributes API actions
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for configurable ID3 eMSG box attributes and the ability to signal them with InbandEventStream tags in DASH and CMAF outputs.
* api-change:``appsync``: Fixes the URI for the evaluatecode endpoint to include the /v1 prefix (ie. "/v1/dataplane-evaluatecode").
* api-change:``ecs``: Documentation updates for Amazon ECS
* api-change:``rds``: This release adds the InvalidDBInstanceStateFault to the RestoreDBClusterFromSnapshot operation.
* api-change:``transcribe``: Amazon Transcribe now supports creating custom language models in the following languages: Japanese (ja-JP) and German (de-DE).
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``ce``: This release introduces two new APIs that offer a 1-click experience to refresh Savings Plans recommendations. The two APIs are StartSavingsPlansPurchaseRecommendationGeneration and ListSavingsPlansPurchaseRecommendationGeneration.
* api-change:``billingconductor``: This release adds the Tiering Pricing Rule feature.
* api-change:``dynamodb``: Endpoint Ruleset update: Use http instead of https for the "local" region.
* enhancement:dependencies: Remove dependency pin for wcwidth and update the pin for docutils.
* api-change:``fms``: AWS Firewall Manager now supports Fortigate Cloud Native Firewall as a Service as a third-party policy type.
* api-change:``redshift-serverless``: Add Table Level Restore operations for Amazon Redshift Serverless. Add multi-port support for Amazon Redshift Serverless endpoints. Add Tagging support to Snapshots and Recovery Points in Amazon Redshift Serverless.
* api-change:``ivschat``: Adds PendingVerification error type to messaging APIs to block the resource usage for accounts identified as being fraudulent.
* api-change:``ec2``: Documentation updates for EC2.


2.9.4
=====

* api-change:``pipes``: AWS introduces new Amazon EventBridge Pipes which allow you to connect sources (SQS, Kinesis, DDB, Kafka, MQ) to Targets (14+ EventBridge Targets) without any code, with filtering, batching, input transformation, and an optional Enrichment stage (Lambda, StepFunctions, ApiGateway, ApiDestinations)
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``comprehend``: Comprehend now supports semi-structured documents (such as PDF files or image files) as inputs for custom analysis using the synchronous APIs (ClassifyDocument and DetectEntities).
* api-change:``codecatalyst``: This release adds operations that support customers using the AWS Toolkits and Amazon CodeCatalyst, a unified software development service that helps developers develop, deploy, and maintain applications in the cloud. For more information, see the documentation.
* api-change:``gamelift``: GameLift introduces a new feature, GameLift Anywhere. GameLift Anywhere allows you to integrate your own compute resources with GameLift. You can also use GameLift Anywhere to iteratively test your game servers without uploading the build to GameLift for every iteration.


2.9.3
=====

* api-change:``dataexchange``: This release enables data providers to license direct access to data in their Amazon S3 buckets or AWS Lake Formation data lakes through AWS Data Exchange. Subscribers get read-only access to the data and can use it in downstream AWS services, like Amazon Athena, without creating or managing copies.
* api-change:``omics``: Amazon Omics is a new, purpose-built service that can be used by healthcare and life science organizations to store, query, and analyze omics data. The insights from that data can be used to accelerate scientific discoveries and improve healthcare.
* api-change:``athena``: This release includes support for using Apache Spark in Amazon Athena.
* api-change:``sagemaker-geospatial``: This release provides Amazon SageMaker geospatial APIs to build, train, deploy and visualize geospatial models.
* api-change:``securitylake``: Amazon Security Lake automatically centralizes security data from cloud, on-premises, and custom sources into a purpose-built data lake stored in your account. Security Lake makes it easier to analyze security data, so you can improve the protection of your workloads, applications, and data
* api-change:``simspaceweaver``: AWS SimSpace Weaver is a new service that helps customers build spatial simulations at new levels of scale - resulting in virtual worlds with millions of dynamic entities. See the AWS SimSpace Weaver developer guide for more details on how to get started. https://docs.aws.amazon.com/simspaceweaver
* api-change:``s3control``: Amazon S3 now supports cross-account access points. S3 bucket owners can now allow trusted AWS accounts to create access points associated with their bucket.
* api-change:``docdb-elastic``: Launched Amazon DocumentDB Elastic Clusters. You can now use the SDK to create, list, update and delete Amazon DocumentDB Elastic Cluster resources
* api-change:``accessanalyzer``: This release adds support for S3 cross account access points. IAM Access Analyzer will now produce public or cross account findings when it detects bucket delegation to external account access points.
* api-change:``kms``: AWS KMS introduces the External Key Store (XKS), a new feature for customers who want to protect their data with encryption keys stored in an external key management system under their control.
* api-change:``opensearchserverless``: Publish SDK for Amazon OpenSearch Serverless
* api-change:``ec2``: This release adds support for AWS Verified Access and the Hpc6id Amazon EC2 compute optimized instance type, which features 3rd generation Intel Xeon Scalable processors.
* api-change:``sagemaker``: Added Models as part of the Search API. Added Model shadow deployments in realtime inference, and shadow testing in managed inference. Added support for shared spaces, geospatial APIs, Model Cards, AutoMLJobStep in pipelines, Git repositories on user profiles and domains, Model sharing in Jumpstart.
* api-change:``glue``: This release adds support for AWS Glue Data Quality, which helps you evaluate and monitor the quality of your data and includes the API for creating, deleting, or updating data quality rulesets, runs and evaluations.
* api-change:``firehose``: Allow support for the Serverless offering for Amazon OpenSearch Service as a Kinesis Data Firehose delivery destination.


2.9.2
=====

* api-change:``kendra``: Amazon Kendra now supports preview of table information from HTML tables in the search results. The most relevant cells with their corresponding rows, columns are displayed as a preview in the search result. The most relevant table cell or cells are also highlighted in table preview.
* api-change:``iot-data``: This release adds support for MQTT5 properties to AWS IoT HTTP Publish API.
* api-change:``ec2``: Introduces ENA Express, which uses AWS SRD and dynamic routing to increase throughput and minimize latency, adds support for trust relationships between Reachability Analyzer and AWS Organizations to enable cross-account analysis, and adds support for Infrastructure Performance metric subscriptions.
* api-change:``eks``: Adds support for additional EKS add-ons metadata and filtering fields
* api-change:``ecs``: This release adds support for ECS Service Connect, a new capability that simplifies writing and operating resilient distributed applications. This release updates the TaskDefinition, Cluster, Service mutation APIs with Service connect constructs and also adds a new ListServicesByNamespace API.
* api-change:``quicksight``: This release adds new Describe APIs and updates Create and Update APIs to support the data model for Dashboards, Analyses, and Templates.
* api-change:``securityhub``: Adding StandardsManagedBy field to DescribeStandards API response
* api-change:``lambda``: Adds support for Lambda SnapStart, which helps improve the startup performance of functions. Customers can now manage SnapStart based functions via CreateFunction and UpdateFunctionConfiguration APIs
* api-change:``macie2``: Added support for configuring Macie to continually sample objects from S3 buckets and inspect them for sensitive data. Results appear in statistics, findings, and other data that Macie provides.
* api-change:``s3control``: Added two new APIs to support Amazon S3 Multi-Region Access Point failover controls: GetMultiRegionAccessPointRoutes and SubmitMultiRegionAccessPointRoutes. The failover control APIs are supported in the following Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2, and ap-northeast-1.
* api-change:``fsx``: This release adds support for 4GB/s / 160K PIOPS FSx for ONTAP file systems and 10GB/s / 350K PIOPS FSx for OpenZFS file systems (Single_AZ_2). For FSx for ONTAP, this also adds support for DP volumes, snapshot policy, copy tags to backups, and Multi-AZ route table updates.
* api-change:``backup``: AWS Backup introduces support for legal hold and application stack backups. AWS Backup Audit Manager introduces support for cross-Region, cross-account reports.
* api-change:``arc-zonal-shift``: Amazon Route 53 Application Recovery Controller Zonal Shift is a new service that makes it easy to shift traffic away from an Availability Zone in a Region. See the developer guide for more information: https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html
* api-change:``glue``: This release allows the creation of Custom Visual Transforms (Dynamic Transforms) to be created via AWS Glue CLI/SDK.
* api-change:``efs``: Update efs command to latest version
* api-change:``inspector2``: This release adds support for Inspector to scan AWS Lambda.
* api-change:``organizations``: This release introduces delegated administrator for AWS Organizations, a new feature to help you delegate the management of your Organizations policies, enabling you to govern your AWS organization in a decentralized way. You can now allow member accounts to manage Organizations policies.
* api-change:``iotwireless``: This release includes a new feature for customers to calculate the position of their devices by adding three new APIs: UpdateResourcePosition, GetResourcePosition, and GetPositionEstimate.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``license-manager-user-subscriptions``: AWS now offers fully-compliant, Amazon-provided licenses for Microsoft Office Professional Plus 2021 Amazon Machine Images (AMIs) on Amazon EC2. These AMIs are now available on the Amazon EC2 console and on AWS Marketplace to launch instances on-demand without any long-term licensing commitments.
* api-change:``iot``: Job scheduling enables the scheduled rollout of a Job with start and end times and a customizable end behavior when end time is reached. This is available for continuous and snapshot jobs. Added support for MQTT5 properties to AWS IoT TopicRule Republish Action.
* api-change:``rds``: This release enables new Aurora and RDS feature called Blue/Green Deployments that makes updates to databases safer, simpler and faster.
* api-change:``drs``: Non breaking changes to existing APIs, and additional APIs added to support in-AWS failing back using AWS Elastic Disaster Recovery.
* api-change:``mgn``: This release adds support for Application and Wave management. We also now support custom post-launch actions.
* api-change:``oam``: Amazon CloudWatch Observability Access Manager is a new service that allows configuration of the CloudWatch cross-account observability feature.
* api-change:``textract``: This release adds support for classifying and splitting lending documents by type, and extracting information by using the Analyze Lending APIs. This release also includes support for summarized information of the processed lending document package, in addition to per document results.
* api-change:``transcribe``: This release adds support for 'inputType' for post-call and real-time (streaming) Call Analytics within Amazon Transcribe.
* api-change:``compute-optimizer``: Adds support for a new recommendation preference that makes it possible for customers to optimize their EC2 recommendations by utilizing an external metrics ingestion service to provide metrics.
* api-change:``logs``: Updates to support CloudWatch Logs data protection and CloudWatch cross-account observability
* api-change:``config``: With this release, you can use AWS Config to evaluate your resources for compliance with Config rules before they are created or updated. Using Config rules in proactive mode enables you to test and build compliant resource templates or check resource configurations at the time they are provisioned.


2.9.1
=====

* api-change:``kinesisanalyticsv2``: Support for Apache Flink 1.15 in Kinesis Data Analytics.
* api-change:``iot-roborunner``: AWS IoT RoboRunner is a new service that makes it easy to build applications that help multi-vendor robots work together seamlessly. See the IoT RoboRunner developer guide for more details on getting started. https://docs.aws.amazon.com/iotroborunner/latest/dev/iotroborunner-welcome.html
* api-change:``rbin``: This release adds support for Rule Lock for Recycle Bin, which allows you to lock retention rules so that they can no longer be modified or deleted.
* api-change:``dynamodb``: Updated minor fixes for DynamoDB documentation.
* api-change:``quicksight``: This release adds the following: 1) Asset management for centralized assets governance 2) QuickSight Q now supports public embedding 3) New Termination protection flag to mitigate accidental deletes 4) Athena data sources now accept a custom IAM role 5) QuickSight supports connectivity to Databricks
* api-change:``sagemaker``: Added DisableProfiler flag as a new field in ProfilerConfig
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``route53``: Amazon Route 53 now supports the Asia Pacific (Hyderabad) Region (ap-south-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``ssm-sap``: AWS Systems Manager for SAP provides simplified operations and management of SAP applications such as SAP HANA. With this release, SAP customers and partners can automate and simplify their SAP system administration tasks such as backup/restore of SAP HANA.
* api-change:``servicecatalog``: This release 1. adds support for Principal Name Sharing with Service Catalog portfolio sharing. 2. Introduces repo sourced products which are created and managed with existing SC APIs. These products are synced to external repos and auto create new product versions based on changes in the repo.
* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Evidence finder. You can now use evidence finder to quickly query your evidence, and add the matching evidence results to an assessment report.
* api-change:``connect``: Added AllowedAccessControlTags and TagRestrictedResource for Tag Based Access Control on Amazon Connect Webpage
* api-change:``cloudfront``: CloudFront API support for staging distributions and associated traffic management policies.
* api-change:``grafana``: This release includes support for configuring a Grafana workspace to connect to a datasource within a VPC as well as new APIs for configuring Grafana settings.
* api-change:``appflow``: Adding support for Amazon AppFlow to transfer the data to Amazon Redshift databases through Amazon Redshift Data API service. This feature will support the Redshift destination connector on both public and private accessible Amazon Redshift Clusters and Amazon Redshift Serverless.
* bugfix:Endpoints: Resolve endpoint with default partition when no region is set
* api-change:``transfer``: Adds a NONE encryption algorithm type to AS2 connectors, providing support for skipping encryption of the AS2 message body when a HTTPS URL is also specified.
* bugfix:s3: fixes missing x-amz-content-sha256 header for s3 object lambda
* api-change:``appflow``: AppFlow provides a new API called UpdateConnectorRegistration to update a custom connector that customers have previously registered. With this API, customers no longer need to unregister and then register a connector to make an update.
* api-change:``glue``: AWSGlue Crawler - Adding support for Table and Column level Comments with database level datatypes for JDBC based crawler.
* api-change:``chime-sdk-voice``: Amazon Chime Voice Connector, Voice Connector Group and PSTN Audio Service APIs are now available in the Amazon Chime SDK Voice namespace. See https://docs.aws.amazon.com/chime-sdk/latest/dg/sdk-available-regions.html for more details.
* api-change:``ec2``: This release adds support for copying an Amazon Machine Image's tags when copying an AMI.


2.9.0
=====

* api-change:``eks``: Adds support for customer-provided placement groups for Kubernetes control plane instances when creating local EKS clusters on Outposts
* api-change:``secretsmanager``: Documentation updates for Secrets Manager.
* api-change:``textract``: This release adds support for specifying and extracting information from documents using the Signatures feature within Analyze Document API
* api-change:``comprehendmedical``: This release supports new set of entities and traits. It also adds new category (BEHAVIORAL_ENVIRONMENTAL_SOCIAL).
* api-change:``personalize``: This release provides support for creation and use of metric attributions in AWS Personalize
* api-change:``ssm-incidents``: Add support for PagerDuty integrations on ResponsePlan, IncidentRecord, and RelatedItem APIs
* api-change:``rds``: This release adds support for container databases (CDBs) to Amazon RDS Custom for Oracle. A CDB contains one PDB at creation. You can add more PDBs using Oracle SQL. You can also customize your database installation by setting the Oracle base, Oracle home, and the OS user name and group.
* enhancement:``sso login``: Add ``--sso-session`` argument to enable direct SSO login with a ``sso-session``
* api-change:``ssm``: This release adds support for cross account access in CreateOpsItem, UpdateOpsItem and GetOpsItem. It introduces new APIs to setup resource policies for SSM resources: PutResourcePolicy, GetResourcePolicies and DeleteResourcePolicy.
* api-change:``elasticache``: for Redis now supports AWS Identity and Access Management authentication access to Redis clusters starting with redis-engine version 7.0
* api-change:``dms``: Adds support for Internet Protocol Version 6 (IPv6) on DMS Replication Instances
* api-change:``appsync``: This release introduces the APPSYNC_JS runtime, and adds support for JavaScript in AppSync functions and AppSync pipeline resolvers.
* api-change:``personalize-events``: This release provides support for creation and use of metric attributions in AWS Personalize
* feature:alias: Add support for per-command aliases (`#7386 <https://github.com/aws/aws-cli/issues/7386>`__)
* api-change:``xray``: This release adds new APIs - PutResourcePolicy, DeleteResourcePolicy, ListResourcePolicies for supporting resource based policies for AWS X-Ray.
* api-change:``emr-serverless``: Adds support for AWS Graviton2 based applications. You can now select CPU architecture when creating new applications or updating existing ones.
* api-change:``workspaces``: The release introduces CreateStandbyWorkspaces, an API that allows you to create standby WorkSpaces associated with a primary WorkSpace in another Region. DescribeWorkspaces now includes related WorkSpaces properties. DescribeWorkspaceBundles and CreateWorkspaceBundle now return more bundle details.
* api-change:``cloudformation``: Added UnsupportedTarget HandlerErrorCode for use with CFN Resource Hooks
* api-change:``amplify``: Adds a new value (WEB_COMPUTE) to the Platform enum that allows customers to create Amplify Apps with Server-Side Rendering support.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``elbv2``: Update elbv2 command to latest version
* feature:``configure sso-session``: Add new ``configure sso-session`` command for creating and updating ``sso-session`` configurations
* api-change:``polly``: Add two new neural voices - Ola (pl-PL) and Hala (ar-AE).
* feature:``configure sso``: Add support for configuring ``sso-session`` as part of configuring SSO-enabled profile
* api-change:``connect``: This release adds a new MonitorContact API for initiating monitoring of ongoing Voice and Chat contacts.
* api-change:``appflow``: AppFlow simplifies the preparation and cataloging of SaaS data into the AWS Glue Data Catalog where your data can be discovered and accessed by AWS analytics and ML services. AppFlow now also supports data field partitioning and file size optimization to improve query performance and reduce cost.
* feature:credentials: Add ``aws configure export-credentials`` command (`issue 7388 <https://github.com/aws/aws-cli/issues/7388>`__)
* api-change:``s3control``: Added 34 new S3 Storage Lens metrics to support additional customer use cases.
* api-change:``securityhub``: Added SourceLayerArn and SourceLayerHash field for security findings.  Updated AwsLambdaFunction Resource detail
* enhancement:sso: Add support for loading sso-session profiles for SSO credential provider
* feature:endpoints 2.0: Update cli v2 to use endpoints 2.0.
* api-change:``lambda``: Add Node 18 (nodejs18.x) support to AWS Lambda.
* api-change:``proton``: Add support for sorting and filtering in ListServiceInstances
* api-change:``billingconductor``: This release adds a new feature BillingEntity pricing rule.
* api-change:``iottwinmaker``: This release adds the following: 1) ExecuteQuery API allows users to query their AWS IoT TwinMaker Knowledge Graph 2) Pricing plan APIs allow users to configure and manage their pricing mode 3) Support for property groups and tabular property values in existing AWS IoT TwinMaker APIs.
* api-change:``ec2``: This release adds a new optional parameter "privateIpAddress" for the CreateNatGateway API. PrivateIPAddress will allow customers to select a custom Private IPv4 address instead of having it be auto-assigned.
* api-change:``rum``: CloudWatch RUM now supports custom events. To use custom events, create an app monitor or update an app monitor with CustomEvent Status as ENABLED.
* api-change:``transfer``: Allow additional operations to throw ThrottlingException
* api-change:``servicecatalog-appregistry``: This release adds support for tagged resource associations, which allows you to associate a group of resources with a defined resource tag key and value to the application.
* api-change:``batch``: Documentation updates related to Batch on EKS
* api-change:``ivschat``: Adds LoggingConfiguration APIs for IVS Chat - a feature that allows customers to store and record sent messages in a chat room to S3 buckets, CloudWatch logs, or Kinesis firehose.


2.8.13
======

* api-change:``rds``: This release adds support for restoring an RDS Multi-AZ DB cluster snapshot to a Single-AZ deployment or a Multi-AZ DB instance deployment.
* api-change:``workdocs``: Added 2 new document related operations, DeleteDocumentVersion and RestoreDocumentVersions.
* api-change:``route53``: Amazon Route 53 now supports the Europe (Spain) Region (eu-south-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``securityhub``: Documentation updates for Security Hub
* api-change:``rekognition``: Adding support for ImageProperties feature to detect dominant colors and image brightness, sharpness, and contrast, inclusion and exclusion filters for labels and label categories, new fields to the API response, "aliases" and "categories"
* api-change:``proton``: Add support for CodeBuild Provisioning
* enhancement:Wizards: Update ``new-role`` wizard with additional prompts `issue 7397 <https://github.com/aws/aws-cli/pull/7397>__`
* api-change:``lakeformation``: This release adds a new parameter "Parameters" in the DataLakeSettings.
* api-change:``license-manager``: AWS License Manager now supports onboarded Management Accounts or Delegated Admins to view granted licenses aggregated from all accounts in the organization.
* api-change:``glue``: Added links related to enabling job bookmarks.
* api-change:``customer-profiles``: This release enhances the SearchProfiles API by providing functionality to search for profiles using multiple keys and logical operators.
* api-change:``iot``: This release add new api listRelatedResourcesForAuditFinding and new member type IssuerCertificates for Iot device device defender Audit.
* api-change:``connect``: This release updates the APIs: UpdateInstanceAttribute, DescribeInstanceAttribute, and ListInstanceAttributes. You can use it to programmatically enable/disable enhanced contact monitoring using attribute type ENHANCED_CONTACT_MONITORING on the specified Amazon Connect instance.
* api-change:``ssm-incidents``: RelatedItems now have an ID field which can be used for referencing them else where. Introducing event references in TimelineEvent API and increasing maximum length of "eventData" to 12K characters.
* api-change:``managedblockchain``: Updating the API docs data type: NetworkEthereumAttributes, and the operations DeleteNode, and CreateNode to also include the supported Goerli network.
* api-change:``ssmsap``: AWS Systems Manager for SAP provides simplified operations and management of SAP applications such as SAP HANA. With this release, SAP customers and partners can automate and simplify their SAP system administration tasks such as backup/restore of SAP HANA.
* api-change:``workspaces``: This release introduces ModifyCertificateBasedAuthProperties, a new API that allows control of certificate-based auth properties associated with a WorkSpaces directory. The DescribeWorkspaceDirectories API will now additionally return certificate-based auth properties in its responses.
* api-change:``marketplace-catalog``: Added three new APIs to support tagging and tag-based authorization: TagResource, UntagResource, and ListTagsForResource. Added optional parameters to the StartChangeSet API to support tagging a resource while making a request to create it.
* api-change:``xray``: This release enhances GetServiceGraph API to support new type of edge to represent links between SQS and Lambda in event-driven applications.
* api-change:``greengrassv2``: Adds new parent target ARN paramater to CreateDeployment, GetDeployment, and ListDeployments APIs for the new subdeployments feature.


2.8.12
======

* api-change:``ecs``: This release adds support for task scale-in protection with updateTaskProtection and getTaskProtection APIs. UpdateTaskProtection API can be used to protect a service managed task from being terminated by scale-in events and getTaskProtection API to get the scale-in protection status of a task.
* api-change:``autoscaling``: This release adds a new price capacity optimized allocation strategy for Spot Instances to help customers optimize provisioning of Spot Instances via EC2 Auto Scaling, EC2 Fleet, and Spot Fleet. It allocates Spot Instances based on both spare capacity availability and Spot Instance price.
* api-change:``scheduler``: AWS introduces the new Amazon EventBridge Scheduler. EventBridge Scheduler is a serverless scheduler that allows you to create, run, and manage tasks from one central, managed service.
* api-change:``ec2``: This release adds a new price capacity optimized allocation strategy for Spot Instances to help customers optimize provisioning of Spot Instances via EC2 Auto Scaling, EC2 Fleet, and Spot Fleet. It allocates Spot Instances based on both spare capacity availability and Spot Instance price.
* api-change:``resource-explorer-2``: Text only updates to some Resource Explorer descriptions.
* api-change:``es``: Amazon OpenSearch Service now offers managed VPC endpoints to connect to your Amazon OpenSearch Service VPC-enabled domain in a Virtual Private Cloud (VPC). This feature allows you to privately access OpenSearch Service domain without using public IPs or requiring traffic to traverse the Internet.


2.8.11
======

* api-change:``ec2``: Amazon EC2 Trn1 instances, powered by AWS Trainium chips, are purpose built for high-performance deep learning training. u-24tb1.112xlarge and u-18tb1.112xlarge High Memory instances are purpose-built to run large in-memory databases.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``connect``: This release adds new fields SignInUrl, UserArn, and UserId to GetFederationToken response payload.
* enhancement:docs: Fixes `#6918 <https://github.com/aws/aws-cli/issues/6918>`__ and `#7400 <https://github.com/aws/aws-cli/issues/7400>`__. The CLI falls back on mandoc if groff isn't available.
* api-change:``connectcases``: This release adds the ability to disable templates through the UpdateTemplate API. Disabling templates prevents customers from creating cases using the template. For more information see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``groundstation``: This release adds the preview of customer-provided ephemeris support for AWS Ground Station, allowing space vehicle owners to provide their own position and trajectory information for a satellite.
* api-change:``mediapackage-vod``: This release adds "IncludeIframeOnlyStream" for Dash endpoints.


2.8.10
======

* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``emr-containers``: Adding support for Job templates. Job templates allow you to create and store templates to configure Spark applications parameters. This helps you ensure consistent settings across applications by reusing and enforcing configuration overrides in data pipelines.
* api-change:``mediaconvert``: The AWS Elemental MediaConvert SDK has added support for setting the SDR reference white point for HDR conversions and conversion of HDR10 to DolbyVision without mastering metadata.
* api-change:``lightsail``: This release adds support for Amazon Lightsail to automate the delegation of domains registered through Amazon Route 53 to Lightsail DNS management and to automate record creation for DNS validation of Lightsail SSL/TLS certificates.
* api-change:``elasticache``: Added support for IPv6 and dual stack for Memcached and Redis clusters. Customers can now launch new Redis and Memcached clusters with IPv6 and dual stack networking support.
* api-change:``workspaces``: This release adds protocols attribute to workspaces properties data type. This enables customers to migrate workspaces from PC over IP (PCoIP) to WorkSpaces Streaming Protocol (WSP) using create and modify workspaces public APIs.
* api-change:``opensearch``: Amazon OpenSearch Service now offers managed VPC endpoints to connect to your Amazon OpenSearch Service VPC-enabled domain in a Virtual Private Cloud (VPC). This feature allows you to privately access OpenSearch Service domain without using public IPs or requiring traffic to traverse the Internet.
* api-change:``polly``: Amazon Polly adds new voices: Elin (sv-SE), Ida (nb-NO), Laura (nl-NL) and Suvi (fi-FI). They are available as neural voices only.
* api-change:``ec2``: This release adds support for two new attributes for attribute-based instance type selection - NetworkBandwidthGbps and AllowedInstanceTypes.
* api-change:``wafv2``: The geo match statement now adds labels for country and region. You can match requests at the region level by combining a geo match statement with label match statements.
* api-change:``autoscaling``: This release adds support for two new attributes for attribute-based instance type selection - NetworkBandwidthGbps and AllowedInstanceTypes.
* api-change:``resource-explorer-2``: This is the initial SDK release for AWS Resource Explorer. AWS Resource Explorer lets your users search for and discover your AWS resources across the AWS Regions in your account.
* api-change:``ec2``: This release adds API support for the recipient of an AMI account share to remove shared AMI launch permissions.
* api-change:``fms``: AWS Firewall Manager now supports importing existing AWS Network Firewall firewalls into Firewall Manager policies.
* api-change:``cloudtrail``: This release includes support for configuring a delegated administrator to manage an AWS Organizations organization CloudTrail trails and event data stores, and AWS Key Management Service encryption of CloudTrail Lake event data stores.
* api-change:``route53``: Amazon Route 53 now supports the Europe (Zurich) Region (eu-central-2) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``billingconductor``: This release adds the Recurring Custom Line Item feature along with a new API ListCustomLineItemVersions.
* api-change:``ssm``: This release includes support for applying a CloudWatch alarm to multi account multi region Systems Manager Automation
* api-change:``wellarchitected``: This release adds support for integrations with AWS Trusted Advisor and AWS Service Catalog AppRegistry to improve workload discovery and speed up your workload reviews.
* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``athena``: Adds support for using Query Result Reuse
* api-change:``logs``: Doc-only update for bug fixes and support of export to buckets encrypted with SSE-KMS
* api-change:``acm``: Support added for requesting elliptic curve certificate key algorithm types P-256 (EC_prime256v1) and P-384 (EC_secp384r1).
* api-change:``ec2``: This release enables sharing of EC2 Placement Groups across accounts and within AWS Organizations using Resource Access Manager
* api-change:``lexv2-models``: Update lexv2-models command to latest version


2.8.9
=====

* api-change:``endpoint-rules``: Update endpoint-rules command to latest version
* api-change:``sagemaker``: Amazon SageMaker now supports running training jobs on ml.trn1 instance types.
* api-change:``ssm-incidents``: Adds support for tagging replication-set on creation.
* api-change:``textract``: Add ocr results in AnalyzeIDResponse as blocks
* api-change:``iotsitewise``: This release adds the ListAssetModelProperties and ListAssetProperties APIs. You can list all properties that belong to a single asset model or asset using these two new APIs.
* api-change:``rds``: Relational Database Service - This release adds support for configuring Storage Throughput on RDS database instances.
* api-change:``s3control``: S3 on Outposts launches support for Lifecycle configuration for Outposts buckets. With S3 Lifecycle configuration, you can mange objects so they are stored cost effectively. You can manage objects using size-based rules and specify how many noncurrent versions bucket will retain.
* api-change:``sagemaker``: This release updates Framework model regex for ModelPackage to support new Framework version xgboost, sklearn.
* api-change:``memorydb``: Adding support for r6gd instances for MemoryDB Redis with data tiering. In a cluster with data tiering enabled, when available memory capacity is exhausted, the least recently used data is automatically tiered to solid state drives for cost-effective capacity scaling with minimal performance impact.


2.8.8
=====

* api-change:``cloud9``: Update to the documentation section of the Cloud9 API Reference guide.
* api-change:``connect``: Amazon connect now support a new API DismissUserContact to dismiss or remove terminated contacts in Agent CCP
* api-change:``appstream``: This release includes CertificateBasedAuthProperties in CreateDirectoryConfig and UpdateDirectoryConfig.
* api-change:``cloudformation``: This release adds more fields to improves visibility of AWS CloudFormation StackSets information in following APIs: ListStackInstances, DescribeStackInstance, ListStackSetOperationResults, ListStackSetOperations, DescribeStackSetOperation.
* api-change:``mediatailor``: This release introduces support for SCTE-35 segmentation descriptor messages which can be sent within time signal messages.
* api-change:``iot``: This release adds the Amazon Location action to IoT Rules Engine.
* api-change:``sesv2``: This release includes support for interacting with the Virtual Deliverability Manager, allowing you to opt in/out of the feature and to retrieve recommendations and metric data.
* api-change:``apprunner``: AWS App Runner adds .NET 6, Go 1, PHP 8.1 and Ruby 3.1 runtimes.
* api-change:``apprunner``: This release adds support for private App Runner services. Services may now be configured to be made private and only accessible from a VPC. The changes include a new VpcIngressConnection resource and several new and modified APIs.
* api-change:``logs``: SDK release to support tagging for destinations and log groups with TagResource. Also supports tag on create with PutDestination.
* api-change:``gamesparks``: Add LATEST as a possible GameSDK Version on snapshot
* api-change:``textract``: This release introduces additional support for 30+ normalized fields such as vendor address and currency. It also includes OCR output in the response and accuracy improvements for the already supported fields in previous version
* api-change:``ec2``: Elastic IP transfer is a new Amazon VPC feature that allows you to transfer your Elastic IP addresses from one AWS Account to another.


2.8.7
=====

* api-change:``ec2``: Feature supports the replacement of instance root volume using an updated AMI without requiring customers to stop their instance.
* api-change:``redshift``: This release clarifies use for the ElasticIp parameter of the CreateCluster and RestoreFromClusterSnapshot APIs.
* api-change:``iam``: Doc only update that corrects instances of CLI not using an entity.
* api-change:``neptune``: Added a new cluster-level attribute to set the capacity range for Neptune Serverless instances.
* api-change:``fms``: Add support NetworkFirewall Managed Rule Group Override flag in GetViolationDetails API
* api-change:``wafv2``: This release adds the following: Challenge rule action, to silently verify client browsers; rule group rule action override to any valid rule action, not just Count; token sharing between protected applications for challenge/CAPTCHA token; targeted rules option for Bot Control managed rule group.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying Grid Search strategy for tuning jobs, which evaluates all hyperparameter combinations exhaustively based on the categorical hyperparameters provided.
* api-change:``sagemaker``: This change allows customers to provide a custom entrypoint script for the docker container to be run while executing training jobs, and provide custom arguments to the entrypoint script.
* api-change:``glue``: Added support for custom datatypes when using custom csv classifier.
* api-change:``kafka``: This release adds support for Tiered Storage. UpdateStorage allows you to control the Storage Mode for supported storage tiers.


2.8.6
=====

* api-change:``location``: Added new map styles with satellite imagery for map resources using HERE as a data provider.
* api-change:``rds``: Relational Database Service - This release adds support for exporting DB cluster data to Amazon S3.
* api-change:``datasync``: Added support for self-signed certificates when using object storage locations; added BytesCompressed to the TaskExecution response.
* api-change:``cognito-idp``: This release adds a new "DeletionProtection" field to the UserPool in Cognito. Application admins can configure this value with either ACTIVE or INACTIVE value. Setting this field to ACTIVE will prevent a user pool from accidental deletion.
* api-change:``accessanalyzer``: This release adds support for six new resource types in IAM Access Analyzer to help you easily identify public and cross-account access to your AWS resources. Updated service API, documentation, and paginators.
* api-change:``mediatailor``: This release is a documentation update
* api-change:``sagemaker``: CreateInferenceRecommenderjob API now supports passing endpoint details directly, that will help customers to identify the max invocation and max latency they can achieve for their model and the associated endpoint along with getting recommendations on other instances.
* api-change:``batch``: This release adds support for AWS Batch on Amazon EKS.
* api-change:``sagemaker``: SageMaker Inference Recommender now supports a new API ListInferenceRecommendationJobSteps to return the details of all the benchmark we create for an inference recommendation job.
* api-change:``workspaces``: This release adds new enums for supporting Workspaces Core features, including creating Manual running mode workspaces, importing regular Workspaces Core images and importing g4dn Workspaces Core images.
* api-change:``acm-pca``: AWS Private Certificate Authority (AWS Private CA) now offers usage modes which are combination of features to address specific use cases.


2.8.5
=====

* api-change:``events``: Update events command to latest version
* api-change:``workspaces-web``: WorkSpaces Web now supports user access logging for recording session start, stop, and URL navigation.
* api-change:``connect``: This release adds API support for managing phone numbers that can be used across multiple AWS regions through telephony traffic distribution.
* api-change:``config``: This release adds resourceType enums for AppConfig, AppSync, DataSync, EC2, EKS, Glue, GuardDuty, SageMaker, ServiceDiscovery, SES, Route53 types.
* api-change:``cloudtrail``: This release includes support for exporting CloudTrail Lake query results to an Amazon S3 bucket.
* api-change:``s3``: Updates internal logic for constructing API endpoints. We have added rule-based endpoints and internal model parameters.
* api-change:``resiliencehub``: In this release, we are introducing support for regional optimization for AWS Resilience Hub applications. It also includes a few documentation updates to improve clarity.
* api-change:``globalaccelerator``: Global Accelerator now supports AddEndpoints and RemoveEndpoints operations for standard endpoint groups.
* api-change:``rum``: CloudWatch RUM now supports Extended CloudWatch Metrics with Additional Dimensions
* api-change:``devops-guru``: This release adds information about the resources DevOps Guru is analyzing.
* api-change:``support-app``: This release adds the RegisterSlackWorkspaceForOrganization API. You can use the API to register a Slack workspace for an AWS account that is part of an organization.
* api-change:``s3control``: Updates internal logic for constructing API endpoints. We have added rule-based endpoints and internal model parameters.
* api-change:``managedblockchain``: Adding new Accessor APIs for Amazon Managed Blockchain
* api-change:``chime-sdk-messaging``: Documentation updates for Chime Messaging SDK


2.8.4
=====

* api-change:``sagemaker``: This release adds support for C7g, C6g, C6gd, C6gn, M6g, M6gd, R6g, and R6gn Graviton instance types in Amazon SageMaker Inference.
* api-change:``frauddetector``: Documentation Updates for Amazon Fraud Detector
* api-change:``greengrass``: This change allows customers to specify FunctionRuntimeOverride in FunctionDefinitionVersion. This configuration can be used if the runtime on the device is different from the AWS Lambda runtime specified for that function.
* api-change:``servicediscovery``: Updated the ListNamespaces API to support the NAME and HTTP_NAME filters, and the BEGINS_WITH filter condition.
* api-change:``sesv2``: This release allows subscribers to enable Dedicated IPs (managed) to send email via a fully managed dedicated IP experience. It also adds identities' VerificationStatus in the response of GetEmailIdentity and ListEmailIdentities APIs, and ImportJobs counts in the response of ListImportJobs API.
* api-change:``mediaconvert``: MediaConvert now supports specifying the minimum percentage of the HRD buffer available at the end of each encoded video segment.
* api-change:``sagemaker``: This change allows customers to enable data capturing while running a batch transform job, and configure monitoring schedule to monitoring the captured data.
* bugfix:docs: Fixes `#7338 <https://github.com/aws/aws-cli/issues/7338>`__. Remove global options from topic tags.


2.8.3
=====

* api-change:``rds-data``: Doc update to reflect no support for schema parameter on BatchExecuteStatement API
* api-change:``ds``: This release adds support for describing and updating AWS Managed Microsoft AD set up.
* api-change:``greengrassv2``: This release adds error status details for deployments and components that failed on a device and adds features to improve visibility into component installation.
* api-change:``codeguru-reviewer``: Documentation update to replace broken link.
* api-change:``wisdom``: This release updates the GetRecommendations API to include a trigger event list for classifying and grouping recommendations.
* api-change:``connect``: This release adds support for a secondary email and a mobile number for Amazon Connect instance users.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``ssm``: Support of AmazonLinux2022 by Patch Manager
* api-change:``ecs``: Documentation update to address tickets.
* api-change:``guardduty``: Add UnprocessedDataSources to CreateDetectorResponse which specifies the data sources that couldn't be enabled during the CreateDetector request. In addition, update documentations.
* api-change:``amplifyuibuilder``: We are releasing the ability for fields to be configured as arrays.
* api-change:``appflow``: With this update, you can choose which Salesforce API is used by Amazon AppFlow to transfer data to or from your Salesforce account. You can choose the Salesforce REST API or Bulk API 2.0. You can also choose for Amazon AppFlow to pick the API automatically.
* api-change:``mediapackage-vod``: This release adds SPEKE v2 support for MediaPackage VOD. Speke v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, based on an encryption contract selected by the customer.
* api-change:``quicksight``: Amazon QuickSight now supports SecretsManager Secret ARN in place of CredentialPair for DataSource creation and update. This release also has some minor documentation updates and removes CountryCode as a required parameter in GeoSpatialColumnGroup
* api-change:``iotfleetwise``: Documentation update for AWS IoT FleetWise
* api-change:``ssm-incidents``: Update RelatedItem enum to support Tasks
* api-change:``translate``: This release enables customers to specify multiple target languages in asynchronous batch translation requests.
* api-change:``panorama``: Pause and resume camera stream processing with SignalApplicationInstanceNodeInstances. Reboot an appliance with CreateJobForDevices. More application state information in DescribeApplicationInstance response.
* api-change:``medialive``: AWS Elemental MediaLive now supports forwarding SCTE-35 messages through the Event Signaling and Management (ESAM) API, and can read those SCTE-35 messages from an inactive source.
* api-change:``transfer``: This release adds an option for customers to configure workflows that are triggered when files are only partially received from a client due to premature session disconnect.
* api-change:``iam``: Documentation updates for the AWS Identity and Access Management API Reference.


2.8.2
=====

* api-change:``network-firewall``: StreamExceptionPolicy configures how AWS Network Firewall processes traffic when a network connection breaks midstream
* api-change:``outposts``: This release adds the Asset state information to the ListAssets response. The ListAssets request supports filtering on Asset state.
* api-change:``glue``: This SDK release adds support to sync glue jobs with source control provider. Additionally, a new parameter called SourceControlDetails will be added to Job model.
* api-change:``resiliencehub``: Documentation change for AWS Resilience Hub. Doc-only update to fix Documentation layout
* enhancement:dependency: Update dependency on cryptography to 38.0.1


2.8.1
=====

* api-change:``connectcases``: This release adds APIs for Amazon Connect Cases. Cases allows your agents to quickly track and manage customer issues that require multiple interactions, follow-up tasks, and teams in your contact center.  For more information, see https://docs.aws.amazon.com/cases/latest/APIReference/Welcome.html
* api-change:``ec2``: Added EnableNetworkAddressUsageMetrics flag for ModifyVpcAttribute, DescribeVpcAttribute APIs.
* api-change:``workmail``: This release adds support for impersonation roles in Amazon WorkMail.
* api-change:``codedeploy``: This release allows you to override the alarm configurations when creating a deployment.
* api-change:``connect``: Updated the CreateIntegrationAssociation API to support the CASES_DOMAIN IntegrationType.
* api-change:``dlm``: This release adds support for archival of single-volume snapshots created by Amazon Data Lifecycle Manager policies
* api-change:``sagemaker``: A new parameter called ExplainerConfig is added to CreateEndpointConfig API to enable SageMaker Clarify online explainability feature.
* api-change:``ecs``: Documentation updates to address various Amazon ECS tickets.
* api-change:``s3control``: S3 Object Lambda adds support to allow customers to intercept HeadObject and ListObjects requests and introduce their own compute. These requests were previously proxied to S3.
* api-change:``ec2``: Adding an imdsSupport attribute to EC2 AMIs
* bugfix:``s3``: Obey source region when retrieving metadata and tags for cross-region multipart copies (`#7316 <https://github.com/aws/aws-cli/issues/7316>`__).
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``devops-guru``: This release adds filter feature on AddNotificationChannel API, enable customer to configure the SNS notification messages by Severity or MessageTypes
* api-change:``accessanalyzer``: AWS IAM Access Analyzer policy validation introduces new checks for role trust policies. As customers author a policy, IAM Access Analyzer policy validation evaluates the policy for any issues to make it easier for customers to author secure policies.
* api-change:``sso-oidc``: Documentation updates for the IAM Identity Center OIDC CLI Reference.
* api-change:``snowball``: Adds support for V3_5C. This is a refreshed AWS Snowball Edge Compute Optimized device type with 28TB SSD, 104 vCPU and 416GB memory (customer usable).


2.8.0
=====

* feature:packaging: Removed setup.cfg and setup.py in favor of pyproject.toml. Build backend changed from setuptools/wheel to flit_core (`#7287 <https://github.com/aws/aws-cli/issues/7287>`__).
* api-change:``location``: This release adds place IDs, which are unique identifiers of places, along with a new GetPlace operation, which can be used with place IDs to find a place again later. UnitNumber and UnitType are also added as new properties of places.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``acm``: This update returns additional certificate details such as certificate SANs and allows sorting in the ListCertificates API.
* api-change:``proton``: This release adds an option to delete pipeline provisioning repositories using the UpdateAccountSettings API
* api-change:``ec2``: Letting external AWS customers provide ImageId as a Launch Template override in FleetLaunchTemplateOverridesRequest
* api-change:``wafv2``: Add the default specification for ResourceType in ListResourcesForWebACL.
* api-change:``nimble``: Amazon Nimble Studio adds support for on-demand Amazon Elastic Compute Cloud (EC2) G3 and G5 instances, allowing customers to utilize additional GPU instance types for their creative projects.
* api-change:``migrationhuborchestrator``: Introducing AWS MigrationHubOrchestrator. This is the first public release of AWS MigrationHubOrchestrator.
* api-change:``apprunner``: AWS App Runner adds a Node.js 16 runtime.
* api-change:``workspaces``: This release includes diagnostic log uploading feature. If it is enabled, the log files of WorkSpaces Windows client will be sent to Amazon WorkSpaces automatically for troubleshooting. You can use modifyClientProperty api to enable/disable this feature.
* api-change:``fsx``: This release adds support for Amazon File Cache.
* api-change:``lightsail``: This release adds Instance Metadata Service (IMDS) support for Lightsail instances.
* api-change:``sagemaker``: SageMaker Training Managed Warm Pools let you retain provisioned infrastructure to reduce latency for repetitive training workloads.
* api-change:``translate``: This release enables customers to access control rights on Translate resources like Parallel Data and Custom Terminology using Tag Based Authorization.
* api-change:``cur``: This release adds two new support regions(me-central-1/eu-south-2) for OSG.
* api-change:``ssm``: This release adds new SSM document types ConformancePackTemplate and CloudFormation
* api-change:``ec2``: u-3tb1 instances are powered by Intel Xeon Platinum 8176M (Skylake) processors and are purpose-built to run large in-memory databases.
* api-change:``ssm``: This release includes support for applying a CloudWatch alarm to Systems Manager capabilities like Automation, Run Command, State Manager, and Maintenance Windows.
* api-change:``polly``: Added support for the new Cantonese voice - Hiujin. Hiujin is available as a Neural voice only.
* api-change:``kendra``: My AWS Service (placeholder) - Amazon Kendra now provides a data source connector for DropBox. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-dropbox.html
* api-change:``ce``: This release is to support retroactive Cost Categories. The new field will enable you to retroactively apply new and existing cost category rules to previous months.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``iotfleetwise``: General availability (GA) for AWS IoT Fleetwise. It adds AWS IoT Fleetwise to AWS SDK. For more information, see https://docs.aws.amazon.com/iot-fleetwise/latest/APIReference/Welcome.html.
* api-change:``emr-serverless``: This release adds API support to debug Amazon EMR Serverless jobs in real-time with live application UIs


2.7.35
======

* api-change:``sagemaker``: SageMaker now allows customization on Canvas Application settings, including enabling/disabling time-series forecasting and specifying an Amazon Forecast execution role at both the Domain and UserProfile levels.
* api-change:``backup-gateway``: Changes include: new GetVirtualMachineApi to fetch a single user's VM, improving ListVirtualMachines to fetch filtered VMs as well as all VMs, and improving GetGatewayApi to now also return the gateway's MaintenanceStartTime.
* api-change:``devicefarm``: This release adds the support for VPC-ENI based connectivity for private devices on AWS Device Farm.
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``comprehend``: Amazon Comprehend now supports synchronous mode for targeted sentiment API operations.
* api-change:``glue``: Added support for S3 Event Notifications for Catalog Target Crawlers.
* api-change:``s3control``: S3 on Outposts launches support for object versioning for Outposts buckets. With S3 Versioning, you can preserve, retrieve, and restore every version of every object stored in your buckets. You can recover from both unintended user actions and application failures.
* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.


2.7.34
======

* api-change:``rds``: This release adds support for Amazon RDS Proxy with SQL Server compatibility.
* api-change:``codestar-notifications``: This release adds tag based access control for the UntagResource API.
* api-change:``ec2``: This release adds support for blocked paths to Amazon VPC Reachability Analyzer.
* enhancement:Dockerfile: This update pulls the base Amazon Linux image from ECR Public rather than Docker Hub.
* api-change:``cloudtrail``: This release includes support for importing existing trails into CloudTrail Lake.
* api-change:``mediaconnect``: This change allows the customer to use the SRT Caller protocol as part of their flows
* api-change:``ec2``: This release adds CapacityAllocations field to DescribeCapacityReservations
* api-change:``ecs``: This release supports new task definition sizes.


2.7.33
======

* api-change:``ec2``: This feature allows customers to create tags for vpc-endpoint-connections and vpc-endpoint-service-permissions.
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying Hyperband strategy for tuning jobs, which uses a multi-fidelity based tuning strategy to stop underperforming hyperparameter configurations early.
* api-change:``amplifyuibuilder``: Amplify Studio UIBuilder is introducing forms functionality. Forms can be configured from Data Store models, JSON, or from scratch. These forms can then be generated in your project and used like any other React components.
* api-change:``dynamodb``: Increased DynamoDB transaction limit from 25 to 100.
* api-change:``ec2``: This update introduces API operations to manage and create local gateway route tables, CoIP pools, and VIF group associations.


2.7.32
======

* api-change:``eks``: Adding support for local Amazon EKS clusters on Outposts
* api-change:``drs``: Fixed the data type of lagDuration that is returned in Describe Source Server API
* api-change:``pi``: Increases the maximum values of two RDS Performance Insights APIs. The maximum value of the Limit parameter of DimensionGroup is 25. The MaxResult maximum is now 25 for the following APIs: DescribeDimensionKeys, GetResourceMetrics, ListAvailableResourceDimensions, and ListAvailableResourceMetrics.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``kendra``: This release enables our customer to choose the option of Sharepoint 2019 for the on-premise Sharepoint connector.
* api-change:``redshift``: This release updates documentation for AQUA features and other description updates.
* enhancement:Identity: Add support for bearer authentication.
* api-change:``cloudtrail``: This release adds CloudTrail getChannel and listChannels APIs to allow customer to view the ServiceLinkedChannel configurations.
* api-change:``customer-profiles``: Added isUnstructured in response for Customer Profiles Integration APIs
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``ec2``: Two new features for local gateway route tables: support for static routes targeting Elastic Network Interfaces and direct VPC routing.
* api-change:``evidently``: This release adds support for the client-side evaluation - powered by AWS AppConfig feature.
* api-change:``transfer``: This release introduces the ability to have multiple server host keys for any of your Transfer Family servers that use the SFTP protocol.


2.7.31
======

* api-change:``route53``: Amazon Route 53 now supports the Middle East (UAE) Region (me-central-1) for latency records, geoproximity records, and private DNS for Amazon VPCs in that region.
* api-change:``lookoutmetrics``: Release dimension value filtering feature to allow customers to define dimension filters for including only a subset of their dataset to be used by LookoutMetrics.
* api-change:``sagemaker``: This release adds Mode to AutoMLJobConfig.
* api-change:``ec2``: This release adds support to send VPC Flow Logs to kinesis-data-firehose as new destination type
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``inspector2``: This release adds new fields like fixAvailable, fixedInVersion and remediation to the finding model. The requirement to have vulnerablePackages in the finding model has also been removed. The documentation has been updated to reflect these changes.
* api-change:``sns``: Amazon SNS introduces the Data Protection Policy APIs, which enable customers to attach a data protection policy to an SNS topic. This allows topic owners to enable the new message data protection feature to audit and block sensitive data that is exchanged through their topics.
* api-change:``emr-containers``: EMR on EKS now allows running Spark SQL using the newly introduced Spark SQL Job Driver in the Start Job Run API
* api-change:``sagemaker``: SageMaker Hosting now allows customization on ML instance storage volume size, model data download timeout and inference container startup ping health check timeout for each ProductionVariant in CreateEndpointConfig API.
* api-change:``iotsitewise``: Allow specifying units in Asset Properties
* api-change:``dataexchange``: Documentation updates for AWS Data Exchange.
* api-change:``fsx``: Documentation update for Amazon FSx.
* api-change:``eks``: Adds support for EKS Addons ResolveConflicts "preserve" flag. Also adds new update failed status for EKS Addons.
* api-change:``ssm``: This release adds support for Systems Manager State Manager Association tagging.
* api-change:``medialive``: This change exposes API settings which allow Dolby Atmos and Dolby Vision to be used when running a channel using Elemental Media Live


2.7.30
======

* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.
* api-change:``sagemaker``: This release enables administrators to attribute user activity and API calls from Studio notebooks, Data Wrangler and Canvas to specific users even when users share the same execution IAM role.  ExecutionRoleIdentityConfig at Sagemaker domain level enables this feature.
* api-change:``mediapackage``: Added support for AES_CTR encryption to CMAF origin endpoints
* api-change:``cognito-idp``: This release adds a new "AuthSessionValidity" field to the UserPoolClient in Cognito. Application admins can configure this value for their users' authentication duration, which is currently fixed at 3 minutes, up to 15 minutes. Setting this field will also apply to the SMS MFA authentication flow.
* api-change:``sagemaker``: This release adds HyperParameterTuningJob type in Search API.
* api-change:``connect``: This release adds search APIs for Routing Profiles and Queues, which can be used to search for those resources within a Connect Instance.
* enhancement:dependency: Update build dependency on PyInstaller to version 5.3


2.7.29
======

* api-change:``sagemaker``: SageMaker Inference Recommender now accepts Inference Recommender fields: Domain, Task, Framework, SamplePayloadUrl, SupportedContentTypes, SupportedInstanceTypes, directly in our CreateInferenceRecommendationsJob API through ContainerConfig
* api-change:``rds-data``: Documentation updates for RDS Data API
* api-change:``route53``: Documentation updates for Amazon Route 53.
* api-change:``controltower``: This release contains the first SDK for AWS Control Tower. It introduces  a new set of APIs: EnableControl, DisableControl, GetControlOperation, and ListEnabledControls.
* api-change:``ivs``: IVS Merge Fragmented Streams. This release adds support for recordingReconnectWindow field in IVS recordingConfigurations. For more information see https://docs.aws.amazon.com/ivs/latest/APIReference/Welcome.html
* api-change:``codeguru-reviewer``: Documentation updates to fix formatting issues in CLI and SDK documentation.
* api-change:``cloudfront``: Update API documentation for CloudFront origin access control (OAC)
* api-change:``iotthingsgraph``: This release deprecates all APIs of the ThingsGraph service
* api-change:``identitystore``: Expand IdentityStore API to support Create, Read, Update, Delete and Get operations for User, Group and GroupMembership resources.


2.7.28
======

* enhancement:docs: Generate a usage note for Tagged Union structures.
* api-change:``rds``: Removes support for RDS Custom from DBInstanceClass in ModifyDBInstance
* api-change:``greengrassv2``: Adds topologyFilter to ListInstalledComponentsRequest which allows filtration of components by ROOT or ALL (including root and dependency components). Adds lastStatusChangeTimestamp to ListInstalledComponents response to show the last time a component changed state on a device.
* api-change:``macie2``: This release of the Amazon Macie API adds support for using allow lists to define specific text and text patterns to ignore when inspecting data sources for sensitive data.
* api-change:``voice-id``: Amazon Connect Voice ID now detects voice spoofing.  When a prospective fraudster tries to spoof caller audio using audio playback or synthesized speech, Voice ID will return a risk score and outcome to indicate the how likely it is that the voice is spoofed.
* api-change:``sso-admin``: Documentation updates for the AWS IAM Identity Center CLI Reference.
* api-change:``sso``: Documentation updates for the AWS IAM Identity Center Portal CLI Reference.
* api-change:``identitystore``: Documentation updates for the Identity Store CLI Reference.
* api-change:``fsx``: Documentation updates for Amazon FSx for NetApp ONTAP.
* api-change:``lookoutequipment``: This release adds new apis for providing labels.
* api-change:``mediapackage``: This release adds Ads AdTriggers and AdsOnDeliveryRestrictions to describe calls for CMAF endpoints on MediaPackage.


2.7.27
======

* api-change:``transfer``: Documentation updates for AWS Transfer Family
* api-change:``iotwireless``: This release includes a new feature for the customers to enable the LoRa gateways to send out beacons for Class B devices and an option to select one or more gateways for Class C devices when sending the LoRaWAN downlink messages.
* api-change:``sso-oidc``: Updated required request parameters on IAM Identity Center's OIDC CreateToken action.
* api-change:``cloudfront``: Adds support for CloudFront origin access control (OAC), making it possible to restrict public access to S3 bucket origins in all AWS Regions, those with SSE-KMS, and more.
* api-change:``ivschat``: Documentation change for IVS Chat API Reference. Doc-only update to add a paragraph on ARNs to the Welcome section.
* api-change:``config``: AWS Config now supports ConformancePackTemplate documents in SSM Docs for the deployment and update of conformance packs.
* api-change:``panorama``: Support sorting and filtering in ListDevices API, and add more fields to device listings and single device detail
* api-change:``ivs``: Documentation Change for IVS API Reference - Doc-only update to type field description for CreateChannel and UpdateChannel actions and for Channel data type. Also added Amazon Resource Names (ARNs) paragraph to Welcome section.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``gamelift``: This release adds support for eight EC2 local zones as fleet locations; Atlanta, Chicago, Dallas, Denver, Houston, Kansas City (us-east-1-mci-1a), Los Angeles, and Phoenix. It also adds support for C5d, C6a, C6i, and R5d EC2 instance families.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``quicksight``: Added a new optional property DashboardVisual under ExperienceConfiguration parameter of GenerateEmbedUrlForAnonymousUser and GenerateEmbedUrlForRegisteredUser API operations. This supports embedding of specific visuals in QuickSight dashboards.


2.7.26
======

* api-change:``sso-admin``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``ec2``: R6a instances are powered by 3rd generation AMD EPYC (Milan) processors delivering all-core turbo frequency of 3.6 GHz. C6id, M6id, and R6id instances are powered by 3rd generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz.
* api-change:``forecastquery``: releasing What-If Analysis APIs
* api-change:``rds``: RDS for Oracle supports Oracle Data Guard switchover and read replica backups.
* api-change:``connect``: This release adds SearchSecurityProfiles API which can be used to search for Security Profile resources within a Connect Instance.
* api-change:``kendra``: This release adds support for a new authentication type - Personal Access Token (PAT) for confluence server.
* api-change:``forecast``: releasing What-If Analysis APIs and update ARN regex pattern to be more strict in accordance with security recommendation
* api-change:``lookoutmetrics``: This release is to make GetDataQualityMetrics API publicly available.
* api-change:``support-app``: This is the initial SDK release for the AWS Support App in Slack.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* enhancement:docs: Improve AWS CLI docs to include global options available to service commands.
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for AwsBackupBackupVault, AwsBackupBackupPlan and AwsBackupRecoveryPoint. Added FixAvailable, FixedInVersion and Remediation  to Vulnerability.
* api-change:``docdb``: Update document for volume clone
* api-change:``iotsitewise``: Enable non-unique asset names under different hierarchies
* api-change:``ivschat``: Documentation Change for IVS Chat API Reference - Doc-only update to change text/description for tags field.
* enhancement:docs: Differentiate between regular and streaming blobs and generate a usage note when a parameter is of streaming blob type.


2.7.25
======

* api-change:``lambda``: Added support for customization of Consumer Group ID for MSK and Kafka Event Source Mappings.
* api-change:``lakeformation``: This release adds a new API support "AssumeDecoratedRoleWithSAML" and also release updates the corresponding documentation.
* enhancement:docs: Differentiate between regular and streaming blobs and generate a usage note when a parameter is of streaming blob type.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager.
* api-change:``dynamodb``: This release adds support for importing data from S3 into a new DynamoDB table
* api-change:``kendra``: This release adds Zendesk connector (which allows you to specify Zendesk SAAS platform as data source), Proxy Support for Sharepoint and Confluence Server (which allows you to specify the proxy configuration if proxy is required to connect to your Sharepoint/Confluence Server as data source).
* enhancement:``--generate-cli-skeleton``: Argument populates enums in JSON skeleton with stable enum value, fixes (`#6695 <https://github.com/aws/aws-cli/issues/6695>`__).
* api-change:``rds``: Adds support for Internet Protocol Version 6 (IPv6) for RDS Aurora database clusters.
* api-change:``appmesh``: AWS App Mesh release to support Multiple Listener and Access Log Format feature
* api-change:``ec2``: This release adds support for VPN log options , a new feature allowing S2S VPN connections to send IKE activity logs to CloudWatch Logs
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``cognito-idp``: This change is being made simply to fix the public documentation based on the models. We have included the PasswordChange and ResendCode events, along with the Pass, Fail and InProgress status. We have removed the Success and Failure status which are never returned by our APIs.
* api-change:``chime-sdk-media-pipelines``: The Amazon Chime SDK now supports live streaming of real-time video from the Amazon Chime SDK sessions to streaming platforms such as Amazon IVS and Amazon Elemental MediaLive. We have also added support for concatenation to create a single media capture file.
* api-change:``networkmanager``: Add TransitGatewayPeeringAttachmentId property to TransitGatewayPeering Model
* api-change:``connectcampaigns``: Updated exceptions for Amazon Connect Outbound Campaign api's.


2.7.24
======

* api-change:``cloudfront``: Adds Http 3 support to distributions
* api-change:``servicecatalog``: Documentation updates for Service Catalog
* api-change:``personalize-runtime``: This release provides support for promotions in AWS Personalize runtime.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports channels with up to one million participants with elastic channels.
* api-change:``sso``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``rds``: Adds support for RDS Custom to DBInstanceClass in ModifyDBInstance
* api-change:``amp``: This release adds log APIs that allow customers to manage logging for their Amazon Managed Service for Prometheus workspaces.
* api-change:``rekognition``: This release adds APIs which support copying an Amazon Rekognition Custom Labels model and managing project policies across AWS account.
* api-change:``ivs``: Updates various list api MaxResults ranges
* api-change:``identitystore``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``wisdom``: This release introduces a new API PutFeedback that allows submitting feedback to Wisdom on content relevance.


2.7.23
======

* enhancement:``awscrt``: Update awscrt version range ceiling to 0.14.0


2.7.22
======

* api-change:``sso-oidc``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``sagemaker``: Amazon SageMaker Automatic Model Tuning now supports specifying multiple alternate EC2 instance types to make tuning jobs more robust when the preferred instance type is not available due to insufficient capacity.
* api-change:``ec2``: This release adds support for excluding specific data (non-root) volumes from multi-volume snapshot sets created from instances.
* api-change:``backupstorage``: This is the first public release of AWS Backup Storage. We are exposing some previously-internal APIs for use by external services. These APIs are not meant to be used directly by customers.
* api-change:``privatenetworks``: This is the initial SDK release for AWS Private 5G. AWS Private 5G is a managed service that makes it easy to deploy, operate, and scale your own private mobile network at your on-premises location.
* api-change:``dlm``: This release adds support for excluding specific data (non-boot) volumes from multi-volume snapshot sets created by snapshot lifecycle policies
* api-change:``sagemaker-a2i-runtime``: Fix bug with parsing ISO-8601 CreationTime in Java SDK in DescribeHumanLoop
* api-change:``cognito-idp``: Add a new exception type, ForbiddenException, that is returned when request is not allowed
* api-change:``glue``: Add an option to run non-urgent or non-time sensitive Glue Jobs on spare capacity
* api-change:``pinpoint``: Adds support for Advance Quiet Time in Journeys. Adds RefreshOnSegmentUpdate and WaitForQuietTime to JourneyResponse.
* api-change:``identitystore``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``chime-sdk-meetings``: Adds support for Tags on Amazon Chime SDK WebRTC sessions
* api-change:``iotwireless``: AWS IoT Wireless release support for sidewalk data reliability.
* api-change:``iot``: The release is to support attach a provisioning template to CACert for JITP function,  Customer now doesn't have to hardcode a roleArn and templateBody during register a CACert to enable JITP.
* api-change:``config``: Add resourceType enums for Athena, GlobalAccelerator, Detective and EC2 types
* api-change:``sso-admin``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``quicksight``: A series of documentation updates to the QuickSight API reference.
* api-change:``glue``: Add support for Python 3.9 AWS Glue Python Shell jobs
* api-change:``dms``: Documentation updates for Database Migration Service (DMS).
* api-change:``sso``: Documentation updates to reflect service rename - AWS IAM Identity Center (successor to AWS Single Sign-On)
* api-change:``location``: Amazon Location Service now allows circular geofences in BatchPutGeofence, PutGeofence, and GetGeofence  APIs.
* api-change:``wafv2``: You can now associate an AWS WAF web ACL with an Amazon Cognito user pool.


2.7.21
======

* api-change:``shield``: AWS Shield Advanced now supports filtering for ListProtections and ListProtectionGroups.
* api-change:``personalize``: This release adds support for incremental bulk ingestion for the Personalize CreateDatasetImportJob API.
* api-change:``fsx``: Documentation updates for Amazon FSx
* api-change:``license-manager-user-subscriptions``: This release supports user based subscription for Microsoft Visual Studio Professional and Enterprise on EC2.
* api-change:``config``: Documentation update for PutConfigRule and PutOrganizationConfigRule
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``workspaces``: This release introduces ModifySamlProperties, a new API that allows control of SAML properties associated with a WorkSpaces directory. The DescribeWorkspaceDirectories API will now additionally return SAML properties in its responses.


2.7.20
======

* api-change:``polly``: Amazon Polly adds new English and Hindi voice - Kajal. Kajal is available as Neural voice only.
* api-change:``opensearch``: This release adds support for gp3 EBS (Elastic Block Store) storage.
* api-change:``lookoutvision``: This release introduces support for image segmentation models and updates CPU accelerator options for models hosted on edge devices.
* api-change:``ec2``: Documentation updates for VM Import/Export.
* api-change:``ssm``: Adding doc updates for OpsCenter support in Service Setting actions.
* api-change:``config``: This release adds ListConformancePackComplianceScores API to support the new compliance score feature, which provides a percentage of the number of compliant rule-resource combinations in a conformance pack compared to the number of total possible rule-resource combinations in the conformance pack.
* api-change:``globalaccelerator``: Global Accelerator now supports dual-stack accelerators, enabling support for IPv4 and IPv6 traffic.
* api-change:``workspaces``: Added CreateWorkspaceImage API to create a new WorkSpace image from an existing WorkSpace.
* api-change:``chime``: Chime VoiceConnector will now support ValidateE911Address which will allow customers to prevalidate their addresses included in their SIP invites for emergency calling
* api-change:``marketplace-catalog``: The SDK for the StartChangeSet API will now automatically set and use an idempotency token in the ClientRequestToken request parameter if the customer does not provide it.
* api-change:``auditmanager``: This release adds an exceeded quota exception to several APIs. We added a ServiceQuotaExceededException for the following operations: CreateAssessment, CreateControl, CreateAssessmentFramework, and UpdateAssessmentStatus.
* api-change:``es``: This release adds support for gp3 EBS (Elastic Block Store) storage.


2.7.19
======

* api-change:``rekognition``: This release introduces support for the automatic scaling of inference units used by Amazon Rekognition Custom Labels models.
* api-change:``autoscaling``: Documentation update for Amazon EC2 Auto Scaling.
* api-change:``macie2``: This release adds support for retrieving (revealing) sample occurrences of sensitive data that Amazon Macie detects and reports in findings.
* api-change:``account``: This release enables customers to manage the primary contact information for their AWS accounts. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/API_Operations.html
* api-change:``securityhub``: Documentation updates for AWS Security Hub
* api-change:``appsync``: Adds support for a new API to evaluate mapping templates with mock data, allowing you to remotely unit test your AppSync resolvers and functions.
* api-change:``transfer``: AWS Transfer Family now supports Applicability Statement 2 (AS2), a network protocol used for the secure and reliable transfer of critical Business-to-Business (B2B) data over the public internet using HTTP/HTTPS as the transport mechanism.
* api-change:``rds``: This release adds the "ModifyActivityStream" API with support for audit policy state locking and unlocking.
* api-change:``detective``: Added the ability to get data source package information for the behavior graph. Graph administrators can now start (or stop) optional datasources on the behavior graph.
* api-change:``medialive``: Link devices now support remote rebooting. Link devices now support maintenance windows. Maintenance windows allow a Link device to install software updates without stopping the MediaLive channel. The channel will experience a brief loss of input from the device while updates are installed.
* api-change:``iotdeviceadvisor``: Added new service feature (Early access only) - Long Duration Test, where customers can test the IoT device to observe how it behaves when the device is in operation for longer period.
* api-change:``lookoutvision``: This release introduces support for the automatic scaling of inference units used by Amazon Lookout for Vision models.
* api-change:``transcribe``: Remove unsupported language codes for StartTranscriptionJob and update VocabularyFileUri for UpdateMedicalVocabulary
* api-change:``guardduty``: Amazon GuardDuty introduces a new Malware Protection feature that triggers malware scan on selected EC2 instance resources, after the service detects a potentially malicious activity.
* api-change:``rds``: Adds support for using RDS Proxies with RDS for MariaDB databases.
* api-change:``ec2``: Added support for EC2 M1 Mac instances. For more information, please visit aws.amazon.com/mac.


2.7.18
======

* api-change:``athena``: This feature allows customers to retrieve runtime statistics for completed queries
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``kendra``: Amazon Kendra now provides Oauth2 support for SharePoint Online. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-sharepoint.html
* api-change:``network-firewall``: Network Firewall now supports referencing dynamic IP sets from stateful rule groups, for IP sets stored in Amazon VPC prefix lists.
* api-change:``iotsitewise``: Added asynchronous API to ingest bulk historical and current data into IoT SiteWise.
* api-change:``frauddetector``: The release introduces Account Takeover Insights (ATI) model. The ATI model detects fraud relating to account takeover. This release also adds support for new variable types: ARE_CREDENTIALS_VALID and SESSION_ID and adds new structures to Model Version APIs.
* api-change:``rds``: Adds support for creating an RDS Proxy for an RDS for MariaDB database.
* api-change:``dms``: Documentation updates for Database Migration Service (DMS).
* api-change:``iot``: GA release the ability to enable/disable IoT Fleet Indexing for Device Defender and Named Shadow information, and search them through IoT Fleet Indexing APIs. This includes Named Shadow Selection as a part of the UpdateIndexingConfiguration API.
* api-change:``acm-pca``: AWS Certificate Manager (ACM) Private Certificate Authority (PCA) documentation updates
* api-change:``docdb``: Enable copy-on-write restore type
* api-change:``ec2-instance-connect``: This release includes a new exception type "EC2InstanceUnavailableException" for SendSSHPublicKey and SendSerialConsoleSSHPublicKey APIs.


2.7.17
======

* api-change:``mediapackage``: This release adds "IncludeIframeOnlyStream" for Dash endpoints and increases the number of supported video and audio encryption presets for Speke v2
* api-change:``datasync``: Documentation updates for AWS DataSync regarding configuring Amazon FSx for ONTAP location security groups and SMB user permissions.
* api-change:``kms``: Added support for the SM2 KeySpec in China Partition Regions
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``sagemaker``: Amazon SageMaker Edge Manager provides lightweight model deployment feature to deploy machine learning models on requested devices.
* api-change:``wafv2``: This SDK release provide customers ability to add sensitivity level for WAF SQLI Match Statements.
* api-change:``glue``: Documentation updates for AWS Glue Job Timeout and Autoscaling
* api-change:``sagemaker-edge``: Amazon SageMaker Edge Manager provides lightweight model deployment feature to deploy machine learning models on requested devices.
* api-change:``sso-admin``: AWS SSO now supports attaching customer managed policies and a permissions boundary to your permission sets. This release adds new API operations to manage and view the customer managed policies and the permissions boundary for a given permission set.
* api-change:``workspaces``: Increased the character limit of the login message from 850 to 2000 characters.
* api-change:``sagemaker``: Fixed an issue with cross account QueryLineage
* api-change:``elasticache``: Adding AutoMinorVersionUpgrade in the DescribeReplicationGroups API
* api-change:``drs``: Changed existing APIs to allow choosing a dynamic volume type for replicating volumes, to reduce costs for customers.
* api-change:``evidently``: This release adds support for the new segmentation feature.
* api-change:``discovery``: Add AWS Agentless Collector details to the GetDiscoverySummary API response
* api-change:``devops-guru``: Added new APIs for log anomaly detection feature.


2.7.16
======

* api-change:``glue``: This release adds an additional worker type for Glue Streaming jobs.
* api-change:``config``: Update ResourceType enum with values for Route53Resolver, Batch, DMS, Workspaces, Stepfunctions, SageMaker, ElasticLoadBalancingV2, MSK types
* api-change:``kendra``: This release adds AccessControlConfigurations which allow you to redefine your document level access control without the need for content re-indexing.
* api-change:``appconfig``: Adding Create, Get, Update, Delete, and List APIs for new two new resources: Extensions and ExtensionAssociations.
* api-change:``ec2``: This release adds flow logs for Transit Gateway to  allow customers to gain deeper visibility and insights into network traffic through their Transit Gateways.
* enhancement:dependency: Update dependency on ``jmespath`` to include versions 1.0.x
* enhancement:HTTP: Update HTTP session configurations to match v1 configurations (`#7107 <https://github.com/aws/aws-cli/issues/7107>`__)
* api-change:``nimble``: Amazon Nimble Studio adds support for IAM-based access to AWS resources for Nimble Studio components and custom studio components. Studio Component scripts use these roles on Nimble Studio workstation to mount filesystems, access S3 buckets, or other configured resources in the Studio's AWS account
* api-change:``athena``: This release updates data types that contain either QueryExecutionId, NamedQueryId or ExpectedBucketOwner. Ids must be between 1 and 128 characters and contain only non-whitespace characters. ExpectedBucketOwner must be 12-digit string.
* api-change:``sagemaker``: This release adds support for G5, P4d, and C6i instance types in Amazon SageMaker Inference and increases the number of hyperparameters that can be searched from 20 to 30 in Amazon SageMaker Automatic Model Tuning
* api-change:``fms``: Adds support for strict ordering in stateful rule groups in Network Firewall policies.
* api-change:``outposts``: This release adds the ShipmentInformation and AssetInformationList fields to the GetOrder API response.
* api-change:``codeartifact``: This release introduces Package Origin Controls, a mechanism used to counteract Dependency Confusion attacks. Adds two new APIs, PutPackageOriginConfiguration and DescribePackage, and updates the ListPackage, DescribePackageVersion and ListPackageVersion APIs in support of the feature.
* api-change:``inspector2``: This release adds support for Inspector V2 scan configurations through the get and update configuration APIs. Currently this allows configuring ECR automated re-scan duration to lifetime or 180 days or 30 days.


2.7.15
======

* api-change:``redshift``: This release adds a new --snapshot-arn field for describe-cluster-snapshots, describe-node-configuration-options, restore-from-cluster-snapshot, authorize-snapshot-acsess, and revoke-snapshot-acsess APIs. It allows customers to give a Redshift snapshot ARN or a Redshift Serverless ARN as input.
* api-change:``backup``: This release adds support for authentication using IAM user identity instead of passed IAM role, identified by excluding the IamRoleArn field in the StartRestoreJob API. This feature applies to only resource clients with a destructive restore nature (e.g. SAP HANA).
* api-change:``redshift-serverless``: Removed prerelease language for GA launch.
* api-change:``ec2``: Build, manage, and monitor a unified global network that connects resources running across your cloud and on-premises environments using the AWS Cloud WAN APIs.
* api-change:``networkmanager``: This release adds general availability API support for AWS Cloud WAN.


2.7.14
======

* api-change:``sagemaker``: Heterogeneous clusters: the ability to launch training jobs with multiple instance types. This enables running component of the training job on the instance type that is most suitable for it. e.g. doing data processing and augmentation on CPU instances and neural network training on GPU instances
* api-change:``dms``: New api to migrate event subscriptions to event bridge rules
* api-change:``synthetics``: This release introduces Group feature, which enables users to group cross-region canaries.
* api-change:``chime-sdk-meetings``: Adds support for AppKeys and TenantIds in Amazon Chime SDK WebRTC sessions
* api-change:``cloudformation``: My AWS Service (placeholder) - Add a new feature Account-level Targeting for StackSet operation
* api-change:``iotwireless``: Adds 5 APIs: PutPositionConfiguration, GetPositionConfiguration, ListPositionConfigurations, UpdatePosition, GetPosition for the new Positioning Service feature which enables customers to configure solvers to calculate position of LoRaWAN devices, or specify position of LoRaWAN devices & gateways.
* api-change:``iot``: This release adds support to register a CA certificate without having to provide a verification certificate. This also allows multiple AWS accounts to register the same CA in the same region.


2.7.13
======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``appstream``: Includes support for StreamingExperienceSettings in CreateStack and UpdateStack APIs
* api-change:``workmail``: This release adds support for managing user availability configurations in Amazon WorkMail.
* api-change:``dms``: Added new features for AWS DMS version 3.4.7 that includes new endpoint settings for S3, OpenSearch, Postgres, SQLServer and Oracle.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for alfresco
* api-change:``ssm-incidents``: Adds support for tagging incident-record on creation by providing incident tags in the template within a response-plan.
* api-change:``customer-profiles``: This release adds the optional MinAllowedConfidenceScoreForMerging parameter to the CreateDomain, UpdateDomain, and GetAutoMergingPreview APIs in Customer Profiles. This parameter is used as a threshold to influence the profile auto-merging step of the Identity Resolution process.
* api-change:``rolesanywhere``: IAM Roles Anywhere allows your workloads such as servers, containers, and applications to obtain temporary AWS credentials and use the same IAM roles and policies that you have configured for your AWS workloads to access AWS resources.
* api-change:``rds``: Adds waiters support for DBCluster.
* api-change:``athena``: This feature introduces the API support for Athena's parameterized query and BatchGetPreparedStatement API.
* api-change:``medialive``: This release adds support for automatic renewal of MediaLive reservations at the end of each reservation term. Automatic renewal is optional. This release also adds support for labelling accessibility-focused audio and caption tracks in HLS outputs.
* api-change:``mwaa``: Documentation updates for Amazon Managed Workflows for Apache Airflow.
* api-change:``quicksight``: This release allows customers to programmatically create QuickSight accounts with Enterprise and Enterprise + Q editions. It also releases allowlisting domains for embedding QuickSight dashboards at runtime through the embedding APIs.
* api-change:``redshift-serverless``: Add new API operations for Amazon Redshift Serverless, a new way of using Amazon Redshift without needing to manually manage provisioned clusters. The new operations let you interact with Redshift Serverless resources, such as create snapshots, list VPC endpoints, delete resource policies, and more.
* api-change:``translate``: Added ListLanguages API which can be used to list the languages supported by Translate.
* api-change:``emr``: Update emr command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``glue``: This release adds tag as an input of CreateDatabase
* api-change:``config``: Updating documentation service limits
* api-change:``wellarchitected``: Added support for UpdateGlobalSettings API. Added status filter to ListWorkloadShares and ListLensShares.
* api-change:``emr``: Update emr command to latest version
* api-change:``rds``: Adds support for additional retention periods to Performance Insights.
* api-change:``pricing``: Documentation update for GetProducts Response.
* api-change:``sagemaker``: This release adds: UpdateFeatureGroup, UpdateFeatureMetadata, DescribeFeatureMetadata APIs; FeatureMetadata type in Search API; LastModifiedTime, LastUpdateStatus, OnlineStoreTotalSizeBytes in DescribeFeatureGroup API.


2.7.12
======

* api-change:``ec2``: This release adds a new spread placement group to EC2 Placement Groups: host level spread, which spread instances between physical hosts, available to Outpost customers only. CreatePlacementGroup and DescribePlacementGroups APIs were updated with a new parameter: SpreadLevel to support this feature.
* enhancement:Python: Update Python interpreter version range support to 3.10
* api-change:``finspace-data``: Release new API GetExternalDataViewAccessDetails
* api-change:``rds-data``: Documentation updates for RDS Data API
* api-change:``polly``: Add 4 new neural voices - Pedro (es-US), Liam (fr-CA), Daniel (de-DE) and Arthur (en-GB).
* api-change:``glue``: This release enables the new ListCrawls API for viewing the AWS Glue Crawler run history.
* api-change:``iot``: This release ease the restriction for the input of tag value to align with AWS standard, now instead of min length 1, we change it to min length 0.
* api-change:``datasync``: AWS DataSync now supports Amazon FSx for NetApp ONTAP locations.


2.7.11
======

* api-change:``lookoutequipment``: This release adds visualizations to the scheduled inference results. Users will be able to see interference results, including diagnostic results from their running inference schedulers.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has released support for automatic DolbyVision metadata generation when converting HDR10 to DolbyVision.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* enhancement:dependency: Bump upper bound of ruamel.yaml to <=0.17.21; fixes `#6756 <https://github.com/aws/aws-cli/issues/6756>`__
* api-change:``pricing``: This release introduces 1 update to the GetProducts API. The serviceCode attribute is now required when you use the GetProductsRequest.
* api-change:``mgn``: New and modified APIs for the Post-Migration Framework
* api-change:``sagemaker``: SageMaker Ground Truth now supports Virtual Private Cloud. Customers can launch labeling jobs and access to their private workforce in VPC mode.
* api-change:``transfer``: Until today, the service supported only RSA host keys and user keys. Now with this launch, Transfer Family has expanded the support for ECDSA and ED25519 host keys and user keys, enabling customers to support a broader set of clients by choosing RSA, ECDSA, and ED25519 host and user keys.
* api-change:``migration-hub-refactor-spaces``: This release adds the new API UpdateRoute that allows route to be updated to ACTIVE/INACTIVE state. In addition, CreateRoute API will now allow users to create route in ACTIVE/INACTIVE state.


2.7.10
======

* api-change:``ecs``: Amazon ECS UpdateService now supports the following parameters: PlacementStrategies, PlacementConstraints and CapacityProviderStrategy.
* api-change:``ds``: This release adds support for describing and updating AWS Managed Microsoft AD settings
* api-change:``connect``: This release updates these APIs: UpdateInstanceAttribute, DescribeInstanceAttribute and ListInstanceAttributes. You can use it to programmatically enable/disable High volume outbound communications using attribute type HIGH_VOLUME_OUTBOUND on the specified Amazon Connect instance.
* api-change:``outposts``: This release adds the AssetLocation structure to the ListAssets response. AssetLocation includes the RackElevation for an Asset.
* api-change:``connectcampaigns``: Added Amazon Connect high volume outbound communications SDK.
* api-change:``ec2``: This release adds support for Private IP VPNs, a new feature allowing S2S VPN connections to use private ip addresses as the tunnel outside ip address over Direct Connect as transport.
* api-change:``kafka``: Documentation updates to use Az Id during cluster creation.
* api-change:``wellarchitected``: Adds support for lens tagging, Adds support for multiple helpful-resource urls and multiple improvement-plan urls.
* api-change:``dynamodb``: Doc only update for DynamoDB service
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version


2.7.9
=====

* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``securityhub``: Added Threats field for security findings. Added new resource details for ECS Container, ECS Task, RDS SecurityGroup, Kinesis Stream, EC2 TransitGateway, EFS AccessPoint, CloudFormation Stack, CloudWatch Alarm, VPC Peering Connection and WAF Rules
* api-change:``redshift-data``: This release adds a new --workgroup-name field to operations that connect to an endpoint. Customers can now execute queries against their serverless workgroups.
* api-change:``finspace-data``: This release adds a new set of APIs, GetPermissionGroup, DisassociateUserFromPermissionGroup, AssociateUserToPermissionGroup, ListPermissionGroupsByUser, ListUsersByPermissionGroup.
* api-change:``workspaces``: Added new field "reason" to OperationNotSupportedException. Receiving this exception in the DeregisterWorkspaceDirectory API will now return a reason giving more context on the failure.
* api-change:``servicecatalog-appregistry``: This release adds a new API ListAttributeGroupsForApplication that returns associated attribute groups of an application. In addition, the UpdateApplication and UpdateAttributeGroup APIs will not allow users to update the 'Name' attribute.
* api-change:``guardduty``: Adds finding fields available from GuardDuty Console. Adds FreeTrial related operations. Deprecates the use of various APIs related to Master Accounts and Replace them with Administrator Accounts.


2.7.8
=====

* api-change:``frauddetector``: Documentation updates for Amazon Fraud Detector (AWSHawksNest)
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for rules that constrain Automatic-ABR rendition selection when generating ABR package ladders.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``m2``: AWS Mainframe Modernization service is a managed mainframe service and set of tools for planning, migrating, modernizing, and running mainframe workloads on AWS
* api-change:``chime-sdk-meetings``: Adds support for live transcription in AWS GovCloud (US) Regions.
* api-change:``redshift-serverless``: Add new API operations for Amazon Redshift Serverless, a new way of using Amazon Redshift without needing to manually manage provisioned clusters. The new operations let you interact with Redshift Serverless resources, such as create snapshots, list VPC endpoints, delete resource policies, and more.
* api-change:``budgets``: Add a budgets ThrottlingException. Update the CostFilters value pattern.
* api-change:``redshift``: Adds new API GetClusterCredentialsWithIAM to return temporary credentials.
* api-change:``neptune``: This release adds support for Neptune to be configured as a global database, with a primary DB cluster in one region, and up to five secondary DB clusters in other regions.
* api-change:``lookoutmetrics``: Adding filters to Alert and adding new UpdateAlert API.
* enhancement:``awscrt``: Update awscrt version range ceiling to 0.13.11
* api-change:``outposts``: This release adds API operations AWS uses to install Outpost servers.
* api-change:``dms``: This release adds DMS Fleet Advisor APIs and exposes functionality for DMS Fleet Advisor. It adds functionality to create and modify fleet advisor instances, and to collect and analyze information about the local data infrastructure.


2.7.7
=====

* api-change:``connect``: This release adds a new API, GetCurrentUserData, which returns real-time details about users' current activity.
* api-change:``ce``: Added two new APIs to support cost allocation tags operations: ListCostAllocationTags, UpdateCostAllocationTagsStatus.
* api-change:``auditmanager``: This release introduces 2 updates to the Audit Manager API. The roleType and roleArn attributes are now required when you use the CreateAssessment or UpdateAssessment operation. We also added a throttling exception to the RegisterAccount API operation.
* api-change:``chime-sdk-messaging``: This release adds support for searching channels by members via the SearchChannels API, removes required restrictions for Name and Mode in UpdateChannel API and enhances CreateChannel API by exposing member and moderator list as well as channel id as optional parameters.


2.7.6
=====

* api-change:``voice-id``: Added a new attribute ServerSideEncryptionUpdateDetails to Domain and DomainSummary.
* api-change:``application-insights``: Provide Account Level onboarding support through CFN/CLI
* api-change:``chime-sdk-meetings``: Adds support for centrally controlling each participant's ability to send and receive audio, video and screen share within a WebRTC session.  Attendee capabilities can be specified when the attendee is created and updated during the session with the new BatchUpdateAttendeeCapabilitiesExcept API.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for GitHub. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-github.html
* api-change:``connect``: This release adds the following features: 1) New APIs to manage (create, list, update) task template resources, 2) Updates to startTaskContact API to support task templates, and 3) new TransferContact API to programmatically transfer in-progress tasks via a contact flow.
* api-change:``forecast``: Added Format field to Import and Export APIs in Amazon Forecast. Added TimeSeriesSelector to Create Forecast API.
* api-change:``backup-gateway``: Adds GetGateway and UpdateGatewaySoftwareNow API and adds hypervisor name to UpdateHypervisor API
* api-change:``route53``: Add new APIs to support Route 53 IP Based Routing
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``proton``: Add new "Components" API to enable users to Create, Delete and Update AWS Proton components.


2.7.5
=====

* api-change:``sagemaker``: Amazon SageMaker Notebook Instances now allows configuration of Instance Metadata Service version and Amazon SageMaker Studio now supports G5 instance types.
* api-change:``sagemaker``: Amazon SageMaker Notebook Instances now support Jupyter Lab 3.
* api-change:``appflow``: Adding the following features/changes: Parquet output that preserves typing from the source connector, Failed executions threshold before deactivation for scheduled flows, increasing max size of access and refresh token from 2048 to 4096
* api-change:``datasync``: AWS DataSync now supports TLS encryption in transit, file system policies and access points for EFS locations.
* api-change:``iotsitewise``: This release adds the following new optional field to the IoT SiteWise asset resource: assetDescription.
* api-change:``drs``: Changed existing APIs and added new APIs to accommodate using multiple AWS accounts with AWS Elastic Disaster Recovery.
* api-change:``emr-serverless``: This release adds support for Amazon EMR Serverless, a serverless runtime environment that simplifies running analytics applications using the latest open source frameworks such as Apache Spark and Apache Hive.
* api-change:``cognito-idp``: Amazon Cognito now supports IP Address propagation for all unauthenticated APIs (e.g. SignUp, ForgotPassword).
* api-change:``lookoutmetrics``: Adding backtest mode to detectors using the Cloudwatch data source.
* api-change:``transcribe``: Amazon Transcribe now supports automatic language identification for multi-lingual audio in batch mode.


2.7.4
=====

* api-change:``cloudformation``: Add a new parameter statusReason to DescribeStackSetOperation output for additional details
* api-change:``lookoutmetrics``: Adding AthenaSourceConfig for MetricSet APIs to support Athena as a data source.
* api-change:``fsx``: This release adds root squash support to FSx for Lustre to restrict root level access from clients by mapping root users to a less-privileged user/group with limited permissions.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for manually selecting features from the input dataset using the CreateAutoMLJob API.
* api-change:``ec2``: C7g instances, powered by the latest generation AWS Graviton3 processors, provide the best price performance in Amazon EC2 for compute-intensive workloads.
* api-change:``forecast``: Introduced a new field in Auto Predictor as Time Alignment Boundary. It helps in aligning the timestamps generated during Forecast exports
* api-change:``emr-serverless``: This release adds support for Amazon EMR Serverless, a serverless runtime environment that simplifies running analytics applications using the latest open source frameworks such as Apache Spark and Apache Hive.
* api-change:``lightsail``: Amazon Lightsail now supports the ability to configure a Lightsail Container Service to pull images from Amazon ECR private repositories in your account.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``voice-id``: VoiceID will now automatically expire Speakers if they haven't been accessed for Enrollment, Re-enrollment or Successful Auth for three years. The Speaker APIs now return a "LastAccessedAt" time for Speakers, and the EvaluateSession API returns "SPEAKER_EXPIRED" Auth Decision for EXPIRED Speakers.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``apprunner``: Documentation-only update added for CodeConfiguration.


2.7.3
=====

* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for rules that constrain Automatic-ABR rendition selection when generating ABR package ladders.
* api-change:``elasticache``: Added support for encryption in transit for Memcached clusters. Customers can now launch Memcached cluster with encryption in transit enabled when using Memcached version 1.6.12 or later.
* api-change:``logs``: Doc-only update to publish the new valid values for log retention
* api-change:``comprehend``: Comprehend releases 14 new entity types for DetectPiiEntities and ContainsPiiEntities APIs.
* api-change:``networkmanager``: This release adds Multi Account API support for a TGW Global Network, to enable and disable AWSServiceAccess with AwsOrganizations for Network Manager service and dependency CloudFormation StackSets service.
* api-change:``ec2``: Stop Protection feature enables customers to protect their instances from accidental stop actions.
* api-change:``ivschat``: Doc-only update. For MessageReviewHandler structure, added timeout period in the description of the fallbackResult field
* api-change:``forecast``: New APIs for Monitor that help you understand how your predictors perform over time.
* api-change:``cognito-idp``: Amazon Cognito now supports requiring attribute verification (ex. email and phone number) before update.
* api-change:``personalize``: Adding modelMetrics as part of DescribeRecommender API response for Personalize.


2.7.2
=====

* api-change:``appmesh``: This release updates the existing Create and Update APIs for meshes and virtual nodes by adding a new IP preference field. This new IP preference field can be used to control the IP versions being used with the mesh and allows for IPv6 support within App Mesh.
* api-change:``greengrassv2``: This release adds the new DeleteDeployment API operation that you can use to delete deployment resources. This release also adds support for discontinued AWS-provided components, so AWS can communicate when a component has any issues that you should consider before you deploy it.
* api-change:``quicksight``: API UpdatePublicSharingSettings enables IAM admins to enable/disable account level setting for public access of dashboards. When enabled, owners/co-owners for dashboards can enable public access on their dashboards. These dashboards can only be accessed through share link or embedding.
* api-change:``iotevents-data``: Introducing new API for deleting detectors: BatchDeleteDetector.
* api-change:``batch``: Documentation updates for AWS Batch.
* api-change:``gamesparks``: This release adds an optional DeploymentResult field in the responses of GetStageDeploymentIntegrationTests and ListStageDeploymentIntegrationTests APIs.
* api-change:``transfer``: AWS Transfer Family now supports SetStat server configuration option, which provides the ability to ignore SetStat command issued by file transfer clients, enabling customers to upload files without any errors.
* api-change:``lookoutmetrics``: In this release we added SnsFormat to SNSConfiguration to support human readable alert.


2.7.1
=====

* bugfix:``events``: Fixed a bug causing signing to fail for put-events
* api-change:``resiliencehub``: In this release, we are introducing support for Amazon Elastic Container Service, Amazon Route 53, AWS Elastic Disaster Recovery, AWS Backup in addition to the existing supported Services.  This release also supports Terraform file input from S3 and scheduling daily assessments
* api-change:``rekognition``: Documentation updates for Amazon Rekognition.
* api-change:``cloudfront``: Introduced a new error (TooLongCSPInResponseHeadersPolicy) that is returned when the value of the Content-Security-Policy header in a response headers policy exceeds the maximum allowed length.
* api-change:``grafana``: This release adds APIs for creating and deleting API keys in an Amazon Managed Grafana workspace.
* api-change:``kms``: Add HMAC best practice tip, annual rotation of AWS managed keys.
* api-change:``discovery``: Add Migration Evaluator Collector details to the GetDiscoverySummary API response
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``servicecatalog``: Updated the descriptions for the ListAcceptedPortfolioShares API description and the PortfolioShareType parameters.
* api-change:``workspaces-web``: Amazon WorkSpaces Web now supports Administrator timeout control
* api-change:``glue``: This release adds a new optional parameter called codeGenNodeConfiguration to CRUD job APIs that allows users to manage visual jobs via APIs. The updated CreateJob and UpdateJob will create jobs that can be viewed in Glue Studio as a visual graph. GetJob can be used to get codeGenNodeConfiguration.


2.7.0
=====

* api-change:``secretsmanager``: Doc only update for Secrets Manager that fixes several customer-reported issues.
* api-change:``ec2``: This release updates AWS PrivateLink APIs to support IPv6 for PrivateLink Services and Endpoints of type 'Interface'.
* api-change:``transfer``: AWS Transfer Family now accepts ECDSA keys for server host keys
* api-change:``workspaces``: Increased the character limit of the login message from 600 to 850 characters.
* api-change:``ssm-incidents``: Adding support for dynamic SSM Runbook parameter values. Updating validation pattern for engagements. Adding ConflictException to UpdateReplicationSet API contract.
* api-change:``ivschat``: Documentation-only updates for IVS Chat API Reference.
* api-change:``ec2``: This release introduces a target type Gateway Load Balancer Endpoint for mirrored traffic. Customers can now specify GatewayLoadBalancerEndpoint option during the creation of a traffic mirror target.
* api-change:``finspace-data``: We've now deprecated CreateSnapshot permission for creating a data view, instead use CreateDataView permission.
* api-change:``outposts``: Documentation updates for AWS Outposts.
* api-change:``lightsail``: This release adds support to include inactive database bundles in the response of the GetRelationalDatabaseBundles request.
* feature:``eks get-token``: All eks get-token commands default to api version v1beta1.
* api-change:``iot``: Documentation update for China region ListMetricValues for IoT
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Jira. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-jira.html
* api-change:``lambda``: Lambda releases NodeJs 16 managed runtime to be available in all commercial regions.
* bugfix:``eks get-token``: Correctly fallback to client.authentication.k8s.io/v1beta1 API if KUBERNETES_EXEC_INFO is undefined


2.6.4
=====

* api-change:``mediapackage``: This release adds Dvb Dash 2014 as an available profile option for Dash Origin Endpoints.
* api-change:``evidently``: Add detail message inside GetExperimentResults API response to indicate experiment result availability
* api-change:``securityhub``: Documentation updates for Security Hub API reference
* api-change:``migration-hub-refactor-spaces``: AWS Migration Hub Refactor Spaces documentation only update to fix a formatting issue.
* api-change:``ec2``: Added support for using NitroTPM and UEFI Secure Boot on EC2 instances.
* api-change:``ssm-contacts``: Fixed an error in the DescribeEngagement example for AWS Incident Manager.
* api-change:``emr``: Update emr command to latest version
* api-change:``cloudcontrol``: SDK release for Cloud Control API to include paginators for Python SDK.
* api-change:``ec2``: Add new state values for IPAMs, IPAM Scopes, and IPAM Pools.
* api-change:``eks``: Adds BOTTLEROCKET_ARM_64_NVIDIA and BOTTLEROCKET_x86_64_NVIDIA AMI types to EKS managed nodegroups
* api-change:``redshift``: Introduces new field 'LoadSampleData' in CreateCluster operation. Customers can now specify 'LoadSampleData' option during creation of a cluster, which results in loading of sample data in the cluster that is created.
* api-change:``location``: Amazon Location Service now includes a MaxResults parameter for ListGeofences requests.
* api-change:``rds``: Various documentation improvements.
* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer


2.6.3
=====

* api-change:``kendra``: AWS Kendra now supports hierarchical facets for a query. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/filtering.html
* api-change:``iot``: AWS IoT Jobs now allows you to create up to 100,000 active continuous and snapshot jobs by using concurrency control.
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``datasync``: AWS DataSync now supports a new ObjectTags Task API option that can be used to control whether Object Tags are transferred.
* enhancement:eks get-token: Add support for respecting API version found in KUBERNETES_EXEC_INFO environment variable
* api-change:``ec2``: Amazon EC2 I4i instances are powered by 3rd generation Intel Xeon Scalable processors and feature up to 30 TB of local AWS Nitro SSD storage
* api-change:``backup``: Adds support to 2 new filters about job complete time for 3 list jobs APIs in AWS Backup
* api-change:``ssm``: This release adds the TargetMaps parameter in SSM State Manager API.
* api-change:``iotsecuretunneling``: This release introduces a new API RotateTunnelAccessToken that allow revoking the existing tokens and generate new tokens
* enhancement:eks update-kubeconfig: Update default API version to v1beta1


2.6.2
=====

* api-change:``codeguru-reviewer``: Amazon CodeGuru Reviewer now supports suppressing recommendations from being generated on specific files and directories.
* api-change:``kinesis-video-archived-media``: Add support for GetImages API  for retrieving images from a video stream
* api-change:``ec2``: Adds support for allocating Dedicated Hosts on AWS  Outposts. The AllocateHosts API now accepts an OutpostArn request  parameter, and the DescribeHosts API now includes an OutpostArn response parameter.
* api-change:``sagemaker``: SageMaker Autopilot adds new metrics for all candidate models generated by Autopilot experiments; RStudio on SageMaker now allows users to bring your own development environment in a custom image.
* api-change:``kinesisvideo``: Add support for multiple image feature related APIs for configuring image generation and notification of a video stream. Add "GET_IMAGES" to the list of supported API names for the GetDataEndpoint API.
* api-change:``wafv2``: You can now inspect all request headers and all cookies. You can now specify how to handle oversize body contents in your rules that inspect the body.
* api-change:``s3``: Documentation only update for doc bug fixes for the S3 API docs.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK nows supports creation of Dolby Vision profile 8.1, the ability to generate black frames of video, and introduces audio-only DASH and CMAF support.
* api-change:``rds``: Feature - Adds support for Internet Protocol Version 6 (IPv6) on RDS database instances.
* api-change:``synthetics``: CloudWatch Synthetics has introduced a new feature to provide customers with an option to delete the underlying resources that Synthetics canary creates when the user chooses to delete the canary.
* api-change:``organizations``: This release adds the INVALID_PAYMENT_INSTRUMENT as a fail reason and an error message.
* api-change:``ssm``: Update the StartChangeRequestExecution, adding TargetMaps to the Runbook parameter
* api-change:``outposts``: This release adds a new API called ListAssets to the Outposts SDK, which lists the hardware assets in an Outpost.


2.6.1
=====

* api-change:``connect``: This release introduces an API for changing the current agent status of a user in Connect.
* api-change:``network-firewall``: AWS Network Firewall adds support for stateful threat signature AWS managed rule groups.
* api-change:``chime-sdk-media-pipelines``: For Amazon Chime SDK meetings, the Amazon Chime Media Pipelines SDK allows builders to capture audio, video, and content share streams. You can also capture meeting events, live transcripts, and data messages. The pipelines save the artifacts to an Amazon S3 bucket that you designate.
* api-change:``ec2``: This release adds support to query the public key and creation date of EC2 Key Pairs. Additionally, the format (pem or ppk) of a key pair can be specified when creating a new key pair.
* api-change:``iotwireless``: Add list support for event configurations, allow to get and update event configurations by resource type, support LoRaWAN events; Make NetworkAnalyzerConfiguration as a resource, add List, Create, Delete API support; Add FCntStart attribute support for ABP WirelessDevice.
* api-change:``braket``: This release enables Braket Hybrid Jobs with Embedded Simulators to have multiple instances.
* api-change:``rekognition``: This release adds support to configure stream-processor resources for label detections on streaming-videos. UpateStreamProcessor API is also launched with this release, which could be used to update an existing stream-processor.
* api-change:``auditmanager``: This release adds documentation updates for Audit Manager. We provided examples of how to use the Custom_ prefix for the keywordValue attribute. We also provided more details about the DeleteAssessmentReport operation.
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds support for custom validation dataset and validation ratio through the CreateAutoMLJob and DescribeAutoMLJob APIs.
* api-change:``guardduty``: Documentation update for API description.
* api-change:``lookoutequipment``: This release adds the following new features: 1) Introduces an option for automatic schema creation 2) Now allows for Ingestion of data containing most common errors and allows automatic data cleaning 3) Introduces new API ListSensorStatistics that gives further information about the ingested data
* api-change:``cloudtrail``: Increases the retention period maximum to 2557 days. Deprecates unused fields of the ListEventDataStores API response. Updates documentation.
* api-change:``amplify``: Documentation only update to support the Amplify GitHub App feature launch


2.6.0
=====

* bugfix:``logs``: Fix bug when `logs tail` truncates microseconds in output if they equals 0. `#5912 <https://github.com/aws/aws-cli/issues/5912>`__
* api-change:``gamelift``: Documentation updates for Amazon GameLift.
* feature:IMDS: Added resiliency mechanisms to IMDS Credential Fetcher
* bugfix:ddb: fixes `#6387 <https://github.com/aws/aws-cli/issues/6387>`__
* api-change:``securityhub``: Security Hub now lets you opt-out of auto-enabling the defaults standards (CIS and FSBP) in accounts that are auto-enabled with Security Hub via Security Hub's integration with AWS Organizations.
* api-change:``sagemaker``: SageMaker Inference Recommender now accepts customer KMS key ID for encryption of endpoints and compilation outputs created during inference recommendation.
* api-change:``connect``: This release adds SearchUsers API which can be used to search for users with a Connect Instance
* api-change:``mq``: This release adds the CRITICAL_ACTION_REQUIRED broker state and the ActionRequired API property. CRITICAL_ACTION_REQUIRED informs you when your broker is degraded. ActionRequired provides you with a code which you can use to find instructions in the Developer Guide on how to resolve the issue.
* api-change:``pricing``: Documentation updates for Price List API
* api-change:``rds-data``: Support to receive SQL query results in the form of a simplified JSON string. This enables developers using the new JSON string format to more easily convert it to an object using popular JSON string parsing libraries.
* api-change:``ec2``: Adds support for waiters that automatically poll for a deleted NAT Gateway until it reaches the deleted state.
* api-change:``glue``: This release adds documentation for the APIs to create, read, delete, list, and batch read of AWS Glue custom patterns, and for Lake Formation configuration settings in the AWS Glue crawler.
* api-change:``network-firewall``: AWS Network Firewall now enables customers to use a customer managed AWS KMS key for the encryption of their firewall resources.
* api-change:``cloudfront``: CloudFront now supports the Server-Timing header in HTTP responses sent from CloudFront. You can use this header to view metrics that help you gain insights about the behavior and performance of CloudFront. To use this header, enable it in a response headers policy.
* api-change:``chime-sdk-meetings``: Include additional exceptions types.
* api-change:``ivschat``: Adds new APIs for IVS Chat, a feature for building interactive chat experiences alongside an IVS broadcast.
* api-change:``lightsail``: This release adds support for Lightsail load balancer HTTP to HTTPS redirect and TLS policy configuration.


2.5.8
=====

* api-change:``rds``: Added a new cluster-level attribute to set the capacity range for Aurora Serverless v2 instances.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``wisdom``: This release updates the GetRecommendations API to include a trigger event list for classifying and grouping recommendations.
* api-change:``mgn``: Removed required annotation from input fields in Describe operations requests. Added quotaValue to ServiceQuotaExceededException
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``lookoutmetrics``: Added DetectMetricSetConfig API for detecting configuration required for creating metric set from provided S3 data source.
* api-change:``macie2``: Sensitive data findings in Amazon Macie now indicate how Macie found the sensitive data that produced a finding (originType).
* api-change:``storagegateway``: This release adds support for minimum of 5 character length virtual tape barcodes.
* api-change:``iotsitewise``: This release adds 3 new batch data query APIs : BatchGetAssetPropertyValue, BatchGetAssetPropertyValueHistory and BatchGetAssetPropertyAggregates
* api-change:``glue``: This release adds APIs to create, read, delete, list, and batch read of Glue custom entity types
* api-change:``mediatailor``: This release introduces tiered channels and adds support for live sources. Customers using a STANDARD channel can now create programs using live sources.
* api-change:``iottwinmaker``: General availability (GA) for AWS IoT TwinMaker. For more information, see https://docs.aws.amazon.com/iot-twinmaker/latest/apireference/Welcome.html
* api-change:``connect``: This release adds APIs to search, claim, release, list, update, and describe phone numbers. You can also use them to associate and disassociate contact flows to phone numbers.


2.5.7
=====

* api-change:``worklink``: Amazon WorkLink is no longer supported. This will be removed in a future version of the SDK.
* api-change:``athena``: This release adds subfields, ErrorMessage, Retryable, to the AthenaError response object in the GetQueryExecution API when a query fails.
* api-change:``rds``: Removes Amazon RDS on VMware with the deletion of APIs related to Custom Availability Zones and Media installation
* api-change:``redshift``: Introduces new fields for LogDestinationType and LogExports on EnableLogging requests and Enable/Disable/DescribeLogging responses. Customers can now select CloudWatch Logs as a destination for their Audit Logs.
* api-change:``autoscaling``: EC2 Auto Scaling now adds default instance warm-up times for all scaling activities, health check replacements, and other replacement events in the Auto Scaling instance lifecycle.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Quip. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-quip.html
* api-change:``transfer``: This release contains corrected HomeDirectoryMappings examples for several API functions: CreateAccess, UpdateAccess, CreateUser, and UpdateUser,.
* api-change:``kms``: Adds support for KMS keys and APIs that generate and verify HMAC codes
* api-change:``textract``: This release adds support for specifying and extracting information from documents using the Queries feature within Analyze Document API
* api-change:``lightsail``: This release adds support to describe the synchronization status of the account-level block public access feature for your Amazon Lightsail buckets.
* api-change:``ssm``: Added offset support for specifying the number of days to wait after the date and time specified by a CRON expression when creating SSM association.
* api-change:``polly``: Amazon Polly adds new Austrian German voice - Hannah. Hannah is available as Neural voice only.
* api-change:``personalize``: Adding StartRecommender and StopRecommender APIs for Personalize.


2.5.6
=====

* api-change:``batch``: Enables configuration updates for compute environments with BEST_FIT_PROGRESSIVE and SPOT_CAPACITY_OPTIMIZED allocation strategies.
* bugfix:Configuration: Fixes `#2996 <https://github.com/aws/aws-cli/issues/2996>`__. Fixed a bug where config file updates would sometimes append new sections to the previous section without adding a newline.
* api-change:``appflow``: Enables users to pass custom token URL parameters for Oauth2 authentication during create connector profile
* api-change:``appstream``: Includes updates for create and update fleet APIs to manage the session scripts locations for Elastic fleets.
* api-change:``fsx``: This release adds support for deploying FSx for ONTAP file systems in a single Availability Zone.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``glue``: Auto Scaling for Glue version 3.0 and later jobs to dynamically scale compute resources. This SDK change provides customers with the auto-scaled DPU usage


2.5.5
=====

* api-change:``iottwinmaker``: This release adds the following new features: 1) ListEntities API now supports search using ExternalId. 2) BatchPutPropertyValue and GetPropertyValueHistory API now allows users to represent time in sub-second level precisions.
* api-change:``wafv2``: Add a new CurrentDefaultVersion field to ListAvailableManagedRuleGroupVersions API response; add a new VersioningSupported boolean to each ManagedRuleGroup returned from ListAvailableManagedRuleGroups API response.
* api-change:``mediapackage-vod``: This release adds ScteMarkersSource as an available field for Dash Packaging Configurations. When set to MANIFEST, MediaPackage will source the SCTE-35 markers from the manifest. When set to SEGMENTS, MediaPackage will source the SCTE-35 markers from the segments.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for the pass-through of WebVTT styling to WebVTT outputs, pass-through of KLV metadata to supported formats, and improved filter support for processing 444/RGB content.
* api-change:``apprunner``: This release adds tracing for App Runner services with X-Ray using AWS Distro for OpenTelemetry. New APIs: CreateObservabilityConfiguration, DescribeObservabilityConfiguration, ListObservabilityConfigurations, and DeleteObservabilityConfiguration. Updated APIs: CreateService and UpdateService.
* api-change:``devops-guru``: This release adds new APIs DeleteInsight to deletes the insight along with the associated anomalies, events and recommendations.
* api-change:``efs``: Update efs command to latest version
* api-change:``workspaces``: Added API support that allows customers to create GPU-enabled WorkSpaces using EC2 G4dn instances.
* api-change:``amplifyuibuilder``: In this release, we have added the ability to bind events to component level actions.
* api-change:``ec2``: X2idn and X2iedn instances are powered by 3rd generation Intel Xeon Scalable processors with an all-core turbo frequency up to 3.5 GHzAmazon EC2. C6a instances are powered by 3rd generation AMD EPYC processors.


2.5.4
=====

* api-change:``sagemaker``: Amazon Sagemaker Notebook Instances now supports G5 instance types
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Box. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-box.html
* api-change:``docdb``: Added support to enable/disable performance insights when creating or modifying db instances
* api-change:``personalize``: This release provides tagging support in AWS Personalize.
* api-change:``lambda``: This release adds new APIs for creating and managing Lambda Function URLs and adds a new FunctionUrlAuthType parameter to the AddPermission API. Customers can use Function URLs to create built-in HTTPS endpoints on their functions.
* api-change:``apigateway``: ApiGateway CLI command get-usage now includes usagePlanId, startDate, and endDate fields in the output to match documentation.
* api-change:``events``: Update events command to latest version
* api-change:``panorama``: Added Brand field to device listings.
* api-change:``pi``: Adds support for DocumentDB to the Performance Insights API.
* api-change:``config``: Add resourceType enums for AWS::EMR::SecurityConfiguration and AWS::SageMaker::CodeRepository


2.5.3
=====

* api-change:``iot``: AWS IoT - AWS IoT Device Defender adds support to list metric datapoints collected for IoT devices through the ListMetricValues API
* api-change:``securityhub``: Added additional ASFF details for RdsSecurityGroup AutoScalingGroup, ElbLoadBalancer, CodeBuildProject and RedshiftCluster.
* api-change:``fsx``: Provide customers more visibility into file system status by adding new "Misconfigured Unavailable" status for Amazon FSx for Windows File Server.
* api-change:``sms``: Revised product update notice for SMS console deprecation.
* api-change:``connect``: This release updates these APIs: UpdateInstanceAttribute, DescribeInstanceAttribute and ListInstanceAttributes. You can use it to programmatically enable/disable multi-party conferencing using attribute type MULTI_PARTY_CONFERENCING on the specified Amazon Connect instance.
* api-change:``proton``: SDK release to support tagging for AWS Proton Repository resource
* api-change:``servicecatalog``: This release adds ProvisioningArtifictOutputKeys to DescribeProvisioningParameters to reference the outputs of a Provisioned Product and deprecates ProvisioningArtifactOutputs.
* api-change:``s3control``: Documentation-only update for doc bug fixes for the S3 Control API docs.
* api-change:``datasync``: AWS DataSync now supports Amazon FSx for OpenZFS locations.


2.5.2
=====

* api-change:``iot-data``: Update the default AWS IoT Core Data Plane endpoint from VeriSign signed to ATS signed. If you have firewalls with strict egress rules, configure the rules to grant you access to data-ats.iot.[region].amazonaws.com or data-ats.iot.[region].amazonaws.com.cn.
* api-change:``cloudcontrol``: SDK release for Cloud Control API in Amazon Web Services China (Beijing) Region, operated by Sinnet, and Amazon Web Services China (Ningxia) Region, operated by NWCD
* api-change:``ec2``: This release simplifies the auto-recovery configuration process enabling customers to set the recovery behavior to disabled or default
* api-change:``grafana``: This release adds tagging support to the Managed Grafana service. New APIs: TagResource, UntagResource and ListTagsForResource. Updates: add optional field tags to support tagging while calling CreateWorkspace.
* api-change:``workspaces``: Added APIs that allow you to customize the logo, login message, and help links in the WorkSpaces client login page. To learn more, visit https://docs.aws.amazon.com/workspaces/latest/adminguide/customize-branding.html
* api-change:``fsx``: This release adds support for modifying throughput capacity for FSx for ONTAP file systems.
* api-change:``pinpoint-sms-voice-v2``: Amazon Pinpoint now offers a version 2.0 suite of SMS and voice APIs, providing increased control over sending and configuration. This release is a new SDK for sending SMS and voice messages called PinpointSMSVoiceV2.
* api-change:``fms``: AWS Firewall Manager now supports the configuration of third-party policies that can use either the centralized or distributed deployment models.
* api-change:``route53-recovery-cluster``: This release adds a new API "ListRoutingControls" to list routing control states using the highly reliable Route 53 ARC data plane endpoints.
* api-change:``databrew``: This AWS Glue Databrew release adds feature to support ORC as an input format.
* api-change:``auditmanager``: This release adds documentation updates for Audit Manager. The updates provide data deletion guidance when a customer deregisters Audit Manager or deregisters a delegated administrator.
* api-change:``iot``: Doc only update for IoT that fixes customer-reported issues.


2.5.1
=====

* api-change:``organizations``: This release provides the new CloseAccount API that enables principals in the management account to close any member account within an organization.
* api-change:``acm-pca``: Updating service name entities
* api-change:``medialive``: This release adds support for selecting a maintenance window.


2.5.0
=====

* feature:Python: Upgrade embedded Python version from Python 3.8 to Python 3.9. All standalone artifacts now run on Python 3.9.11.


2.4.29
======

* api-change:``ssm``: This Patch Manager release supports creating, updating, and deleting Patch Baselines for Rocky Linux OS.
* api-change:``gamesparks``: Released the preview of Amazon GameSparks, a fully managed AWS service that provides a multi-service backend for game developers.
* api-change:``lambda``: Adds support for increased ephemeral storage (/tmp) up to 10GB for Lambda functions. Customers can now provision up to 10 GB of ephemeral storage per function instance, a 20x increase over the previous limit of 512 MB.
* api-change:``batch``: Bug Fix: Fixed a bug where shapes were marked as unboxed and were not serialized and sent over the wire, causing an API error from the service.
* api-change:``ec2``: This is release adds support for Amazon VPC Reachability Analyzer to analyze path through a Transit Gateway.
* api-change:``auditmanager``: This release updates 1 API parameter, the SnsArn attribute. The character length and regex pattern for the SnsArn attribute have been updated, which enables you to deselect an SNS topic when using the UpdateSettings operation.
* api-change:``ssm``: Update AddTagsToResource, ListTagsForResource, and RemoveTagsFromResource APIs to reflect the support for tagging Automation resources. Includes other minor documentation updates.
* api-change:``transfer``: Documentation updates for AWS Transfer Family to describe how to remove an associated workflow from a server.
* api-change:``ebs``: Increased the maximum supported value for the Timeout parameter of the StartSnapshot API from 60 minutes to 4320 minutes.  Changed the HTTP error code for ConflictException from 503 to 409.
* api-change:``transcribe``: This release adds an additional parameter for subtitling with Amazon Transcribe batch jobs: outputStartIndex.
* api-change:``redshift``: This release adds a new [--encrypted | --no-encrypted] field in restore-from-cluster-snapshot API. Customers can now restore an unencrypted snapshot to a cluster encrypted with AWS Managed Key or their own KMS key.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``config``: Added new APIs GetCustomRulePolicy and GetOrganizationCustomRulePolicy, and updated existing APIs PutConfigRule, DescribeConfigRule, DescribeConfigRuleEvaluationStatus, PutOrganizationConfigRule, DescribeConfigRule to support a new feature for building AWS Config rules with AWS CloudFormation Guard


2.4.28
======

* api-change:``ecr``: This release includes a fix in the DescribeImageScanFindings paginated output.
* api-change:``glue``: Added 9 new APIs for AWS Glue Interactive Sessions: ListSessions, StopSession, CreateSession, GetSession, DeleteSession, RunStatement, GetStatement, ListStatements, CancelStatement
* api-change:``quicksight``: AWS QuickSight Service Features - Expand public API support for group management.
* enhancement:Python: Update Python interpreter version range support to 3.8 to 3.9
* api-change:``ecs``: Documentation only update to address tickets
* api-change:``lakeformation``: The release fixes the incorrect permissions called out in the documentation - DESCRIBE_TAG, ASSOCIATE_TAG, DELETE_TAG, ALTER_TAG. This trebuchet release fixes the corresponding SDK and documentation.
* api-change:``ssm-incidents``: Removed incorrect validation pattern for IncidentRecordSource.invokedBy
* api-change:``ram``: Document improvements to the RAM API operations and parameter descriptions.
* api-change:``mediaconnect``: This release adds support for selecting a maintenance window.
* api-change:``acm-pca``: AWS Certificate Manager (ACM) Private Certificate Authority (CA) now supports customizable certificate subject names and extensions.
* api-change:``s3outposts``: S3 on Outposts is releasing a new API, ListSharedEndpoints, that lists all endpoints associated with S3 on Outpost, that has been shared by Resource Access Manager (RAM).
* api-change:``ce``: Added three new APIs to support tagging and resource-level authorization on Cost Explorer resources: TagResource, UntagResource, ListTagsForResource.  Added optional parameters to CreateCostCategoryDefinition, CreateAnomalySubscription and CreateAnomalyMonitor APIs to support Tag On Create.
* api-change:``polly``: Amazon Polly adds new Catalan voice - Arlet. Arlet is available as Neural voice only.
* api-change:``billingconductor``: This is the initial SDK release for AWS Billing Conductor. The AWS Billing Conductor is a customizable billing service, allowing you to customize your billing data to match your desired business structure.
* api-change:``location``: Amazon Location Service now includes a MaxResults parameter for GetDevicePositionHistory requests.
* api-change:``amplifybackend``: Adding the ability to customize Cognito verification messages for email and SMS in CreateBackendAuth and UpdateBackendAuth. Adding deprecation documentation for ForgotPassword in CreateBackendAuth and UpdateBackendAuth
* api-change:``chime-sdk-meetings``: Add support for media replication to link multiple WebRTC media sessions together to reach larger and global audiences. Participants connected to a replica session can be granted access to join the primary session and can switch sessions with their existing WebRTC connection


2.4.27
======

* api-change:``keyspaces``: Fixing formatting issues in CLI and SDK documentation
* api-change:``ec2``: Adds the Cascade parameter to the DeleteIpam API. Customers can use this parameter to automatically delete their IPAM, including non-default scopes, pools, cidrs, and allocations. There mustn't be any pools provisioned in the default public scope to use this parameter.
* api-change:``location``: New HERE style "VectorHereExplore" and "VectorHereExploreTruck".
* enhancement:Dependency: Update ``awscrt`` version range to include 0.13.5
* api-change:``dataexchange``: This feature enables data providers to use the RevokeRevision operation to revoke subscriber access to a given revision. Subscribers are unable to interact with assets within a revoked revision.
* api-change:``cognito-idp``: Updated EmailConfigurationType and SmsConfigurationType to reflect that you can now choose Amazon SES and Amazon SNS resources in the same Region.
* api-change:``rds``: Various documentation improvements
* api-change:``robomaker``: This release deprecates ROS, Ubuntu and Gazbeo from RoboMaker Simulation Service Software Suites in favor of user-supplied containers and Relaxed Software Suites.
* api-change:``ecs``: Documentation only update to address tickets


2.4.26
======

* api-change:``timestream-query``: Amazon Timestream Scheduled Queries now support Timestamp datatype in a multi-measure record.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``config``: Add resourceType enums for AWS::ECR::PublicRepository and AWS::EC2::LaunchTemplate
* api-change:``lambda``: Adds PrincipalOrgID support to AddPermission API. Customers can use it to manage permissions to lambda functions at AWS Organizations level.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager.
* api-change:``connect``: This release adds support for enabling Rich Messaging when starting a new chat session via the StartChatContact API. Rich Messaging enables the following formatting options: bold, italics, hyperlinks, bulleted lists, and numbered lists.
* api-change:``outposts``: This release adds address filters for listSites
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Slack. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-slack.html
* api-change:``chime``: Chime VoiceConnector Logging APIs will now support MediaMetricLogs. Also CreateMeetingDialOut now returns AccessDeniedException.


2.4.25
======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``transfer``: Adding more descriptive error types for managed workflows
* enhancement:``sso``: Implements `#5301 <https://github.com/aws/aws-cli/issues/5301>`__. Added support for the ``--no-browser`` flag to the ``aws sso login`` and ``aws configure sso`` commands.
* api-change:``transcribe``: Documentation fix for API `StartMedicalTranscriptionJobRequest`, now showing min sample rate as 16khz
* api-change:``comprehend``: Amazon Comprehend now supports extracting the sentiment associated with entities such as brands, products and services from text documents.


2.4.24
======

* api-change:``keyspaces``: Adding link to CloudTrail section in Amazon Keyspaces Developer Guide
* api-change:``ec2``: Documentation updates for Amazon EC2.
* api-change:``macie``: Amazon Macie Classic (macie) has been discontinued and is no longer available. A new Amazon Macie (macie2) is now available with significant design improvements and additional features.
* api-change:``synthetics``: Allow custom handler function.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``eks``: Introducing a new enum for NodeGroup error code: Ec2SubnetMissingIpv6Assignment
* api-change:``devops-guru``: Amazon DevOps Guru now integrates with Amazon CodeGuru Profiler. You can view CodeGuru Profiler recommendations for your AWS Lambda function in DevOps Guru. This feature is enabled by default for new customers as of 3/4/2022. Existing customers can enable this feature with UpdateEventSourcesConfig.
* api-change:``ecs``: Amazon ECS UpdateService API now supports additional parameters: loadBalancers, propagateTags, enableECSManagedTags, and serviceRegistries
* api-change:``chime-sdk-meetings``: Adds support for Transcribe language identification feature to the StartMeetingTranscription API.
* api-change:``connect``: This release updates the *InstanceStorageConfig APIs so they support a new ResourceType: REAL_TIME_CONTACT_ANALYSIS_SEGMENTS. Use this resource type to enable streaming for real-time contact analysis and to associate the Kinesis stream where real-time contact analysis segments will be published.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for reading timecode from AVCHD sources and now provides the ability to segment WebVTT at the same interval as the video and audio in HLS packages.
* api-change:``migration-hub-refactor-spaces``: AWS Migration Hub Refactor Spaces documentation update.
* api-change:``transfer``: Add waiters for server online and offline.
* bugfix:endpoints: Fix FIPS endpoint resolution for non-default partitions


2.4.23
======

* api-change:``appflow``: Launching Amazon AppFlow Marketo as a destination connector SDK.
* api-change:``keyspaces``: This release adds support for data definition language (DDL) operations
* api-change:``greengrassv2``: Doc only update that clarifies Create Deployment section.
* api-change:``cloudtrail``: Add bytesScanned field into responses of DescribeQuery and GetQueryResults.
* api-change:``timestream-query``: Documentation only update for SDK and CLI
* api-change:``kendra``: Amazon Kendra now suggests spell corrections for a query. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/query-spell-check.html
* api-change:``ecr``: This release adds support for tracking images lastRecordedPullTime.
* api-change:``gamelift``: Minor updates to address errors.
* api-change:``fsx``: This release adds support for data repository associations to use root ("/") as the file system path
* api-change:``athena``: This release adds support for S3 Object Ownership by allowing the S3 bucket owner full control canned ACL to be set when Athena writes query results to S3 buckets.


2.4.22
======

* api-change:``fsx``: This release adds support for the following FSx for OpenZFS features: snapshot lifecycle transition messages, force flag for deleting file systems with child resources, LZ4 data compression, custom record sizes, and unsetting volume quotas and reservations.
* api-change:``ec2``: This release adds support for new AMI property 'lastLaunchedTime'
* api-change:``amplify``: Add repositoryCloneMethod field for hosting an Amplify app. This field shows what authorization method is used to clone the repo: SSH, TOKEN, or SIGV4.
* api-change:``rds``: Documentation updates for Multi-AZ DB clusters.
* api-change:``amplifyuibuilder``: We are adding the ability to configure workflows and actions for components.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``fis``: This release adds logging support for AWS Fault Injection Simulator experiments. Experiment templates can now be configured to send experiment activity logs to Amazon CloudWatch Logs or to an S3 bucket.
* api-change:``route53-recovery-cluster``: This release adds a new API option to enable overriding safety rules to allow routing control state updates.
* api-change:``panorama``: Added NTP server configuration parameter to ProvisionDevice operation. Added alternate software fields to DescribeDevice response
* api-change:``kafkaconnect``: Adds operation for custom plugin deletion (DeleteCustomPlugin) and adds new StateDescription field to DescribeCustomPlugin and DescribeConnector responses to return errors from asynchronous resource creation.
* api-change:``mediapackage``: This release adds Hybridcast as an available profile option for Dash Origin Endpoints.
* api-change:``finspace-data``: Add new APIs for managing Users and Permission Groups.
* api-change:``athena``: This release adds support for updating an existing named query.
* api-change:``servicecatalog-appregistry``: AppRegistry is deprecating Application and Attribute-Group Name update feature. In this release, we are marking the name attributes for Update APIs as deprecated to give a heads up to our customers.
* api-change:``mgn``: Add support for GP3 and IO2 volume types. Add bootMode to LaunchConfiguration object (and as a parameter to UpdateLaunchConfigurationRequest).


2.4.21
======

* enhancement:dependency: bump cryptography version
* api-change:``fms``: AWS Firewall Manager now supports the configuration of AWS Network Firewall policies with either centralized or distributed deployment models. This release also adds support for custom endpoint configuration, where you can choose which Availability Zones to create firewall endpoints in.
* api-change:``route53``: SDK doc update for Route 53 to update some parameters with new information.
* api-change:``s3``: This release adds support for new integrity checking capabilities in Amazon S3. You can choose from four supported checksum algorithms for data integrity checking on your upload and download requests. In addition, AWS SDK can automatically calculate a checksum as it streams data into S3
* api-change:``s3control``: Amazon S3 Batch Operations adds support for new integrity checking capabilities in Amazon S3.
* api-change:``transfer``: The file input selection feature provides the ability to use either the originally uploaded file or the output file from the previous workflow step, enabling customers to make multiple copies of the original file while keeping the source file intact for file archival.
* api-change:``autoscaling``: You can now hibernate instances in a warm pool to stop instances without deleting their RAM contents. You can now also return instances to the warm pool on scale in, instead of always terminating capacity that you will need later.
* api-change:``lightsail``: This release adds support to delete and create Lightsail default key pairs that you can use with Lightsail instances.
* api-change:``lambda``: Lambda releases .NET 6 managed runtime to be available in all commercial regions.
* api-change:``databrew``: This AWS Glue Databrew release adds feature to merge job outputs into a max number of files for S3 File output type.
* api-change:``textract``: Added support for merged cells and column header for table response.
* api-change:``transfer``: Support automatic pagination when listing AWS Transfer Family resources.


2.4.20
======

* api-change:``dynamodb``: DynamoDB ExecuteStatement API now supports Limit as a request parameter to specify the maximum number of items to evaluate. If specified, the service will process up to the Limit and the results will include a LastEvaluatedKey value to continue the read in a subsequent operation.
* api-change:``wafv2``: Updated descriptions for logging configuration.
* api-change:``imagebuilder``: This release adds support to enable faster launching for Windows AMIs created by EC2 Image Builder.
* api-change:``apprunner``: AWS App Runner adds a Java platform (Corretto 8, Corretto 11 runtimes) and a Node.js 14 runtime.
* enhancement:SSO: Fixes `#5727 <https://github.com/aws/aws-cli/issues/5727>`__. Loosens the requirements to perform an ``aws sso login`` command to just the ``sso_start_url`` and ``sso_region``.
* api-change:``customer-profiles``: This release introduces apis CreateIntegrationWorkflow, DeleteWorkflow, ListWorkflows, GetWorkflow and GetWorkflowSteps. These apis are used to manage and view integration workflows.
* api-change:``transfer``: Properties for Transfer Family used with SFTP, FTP, and FTPS protocols. Display Banners are bodies of text that can be displayed before and/or after a user authenticates onto a server using one of the previously mentioned protocols.
* api-change:``gamelift``: Increase string list limit from 10 to 100.
* api-change:``translate``: This release enables customers to use translation settings for formality customization in their synchronous translation output.
* api-change:``budgets``: This change introduces DescribeBudgetNotificationsForAccount API which returns budget notifications for the specified account


2.4.19
======

* api-change:``glue``: Support for optimistic locking in UpdateTable
* enhancement:protocol: Add support for lists in headers
* api-change:``budgets``: Adds support for auto-adjusting budgets, a new budget method alongside fixed and planned. Auto-adjusting budgets introduces new metadata to configure a budget limit baseline using a historical lookback average or current period forecast.
* api-change:``evidently``: Add support for filtering list of experiments and launches by status
* api-change:``ce``: AWS Cost Anomaly Detection now supports SNS FIFO topic subscribers.
* api-change:``redshift``: SDK release for Cross region datasharing and cost-control for cross region datasharing
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``rds``: Adds support for determining which Aurora PostgreSQL versions support Babelfish.
* api-change:``ssm``: Assorted ticket fixes and updates for AWS Systems Manager.
* api-change:``athena``: This release adds a subfield, ErrorType, to the AthenaError response object in the GetQueryExecution API when a query fails.
* Depedency:prompt-toolkit: Update to prompt-toolkit dependency to 3.x (`#6507 <https://github.com/aws/aws-cli/issues/6507>`__).
* api-change:``appflow``: Launching Amazon AppFlow SAP as a destination connector SDK.
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``backup``: AWS Backup add new S3_BACKUP_OBJECT_FAILED and S3_RESTORE_OBJECT_FAILED event types in BackupVaultNotifications events list.
* api-change:``ssm``: Documentation updates for AWS Systems Manager.


2.4.18
======

* api-change:``wafv2``: Adds support for AWS WAF Fraud Control account takeover prevention (ATP), with configuration options for the new managed rule group AWSManagedRulesATPRuleSet and support for application integration SDKs for Android and iOS mobile apps.
* api-change:``pinpoint``: This SDK release adds a new paramater creation date for GetApp and GetApps Api call
* api-change:``sns``: Customer requested typo fix in API documentation.
* api-change:``lookoutvision``: This release makes CompilerOptions in Lookout for Vision's StartModelPackagingJob's Configuration object optional.
* api-change:``cloudformation``: This SDK release is for the feature launch of AWS CloudFormation Hooks.
* api-change:``cloudformation``: This SDK release adds AWS CloudFormation Hooks HandlerErrorCodes


2.4.17
======

* api-change:``apprunner``: This release adds support for App Runner to route outbound network traffic of a service through an Amazon VPC. New API: CreateVpcConnector, DescribeVpcConnector, ListVpcConnectors, and DeleteVpcConnector. Updated API: CreateService, DescribeService, and UpdateService.
* api-change:``synthetics``: Adding names parameters to the Describe APIs.
* api-change:``athena``: You can now optionally specify the account ID that you expect to be the owner of your query results output location bucket in Athena. If the account ID of the query results bucket owner does not match the specified account ID, attempts to output to the bucket will fail with an S3 permissions error.
* api-change:``sagemaker``: Autopilot now generates an additional report with information on the performance of the best model, such as a Confusion matrix and  Area under the receiver operating characteristic (AUC-ROC). The path to the report can be found in CandidateArtifactLocations.
* api-change:``s3control``: This release adds support for S3 Batch Replication. Batch Replication lets you replicate existing objects, already replicated objects to new destinations, and objects that previously failed to replicate. Customers will receive object-level visibility of progress and a detailed completion report.
* api-change:``lakeformation``: Add support for calling Update Table Objects without a TransactionId.
* api-change:``events``: Update events command to latest version
* api-change:``ssm-incidents``: Update RelatedItem enum to support SSM Automation
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Amazon FSx. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-fsx.html
* api-change:``rds``: updates for RDS Custom for Oracle 12.1 support
* api-change:``auditmanager``: This release updates 3 API parameters. UpdateAssessmentFrameworkControlSet now requires the controls attribute, and CreateAssessmentFrameworkControl requires the id attribute. Additionally, UpdateAssessmentFramework now has a minimum length constraint for the controlSets attribute.


2.4.16
======

* enhancement:datapipeline: Deprecated support for the datapipeline create-default-roles command
* api-change:``iot``: This release adds support for configuring AWS IoT logging level per client ID, source IP, or principal ID.
* api-change:``appconfig``: Documentation updates for AWS AppConfig
* api-change:``sagemaker``: This release added a new NNA accelerator compilation support for Sagemaker Neo.
* api-change:``appconfigdata``: Documentation updates for AWS AppConfig Data.
* api-change:``glue``: Launch Protobuf support for AWS Glue Schema Registry
* api-change:``appflow``: Launching Amazon AppFlow Custom Connector SDK.
* api-change:``dynamodb``: Documentation update for DynamoDB Java SDK.
* api-change:``ce``: Doc-only update for Cost Explorer API that adds INVOICING_ENTITY dimensions
* api-change:``emr``: Update emr command to latest version
* api-change:``rbin``: Add EC2 Image recycle bin support.
* api-change:``cognito-idp``: Doc updates for Cognito user pools API Reference.
* api-change:``secretsmanager``: Feature are ready to release on Jan 28th
* api-change:``comprehend``: Amazon Comprehend now supports sharing and importing custom trained models from one AWS account to another within the same region.
* api-change:``es``: Allows customers to get progress updates for blue/green deployments
* api-change:``elasticache``: Documentation update for AWS ElastiCache
* api-change:``meteringmarketplace``: Add CustomerAWSAccountId to ResolveCustomer API response and increase UsageAllocation limit to 2500.
* api-change:``ec2``: adds support for AMIs in Recycle Bin
* api-change:``robomaker``: The release deprecates the use various APIs of RoboMaker Deployment Service in favor of AWS IoT GreenGrass v2.0.
* api-change:``fis``: Added GetTargetResourceType and ListTargetResourceTypesAPI actions. These actions return additional details about resource types and parameters that can be targeted by FIS actions. Added a parameters field for the targets that can be specified in experiment templates.
* api-change:``personalize``: Adding minRecommendationRequestsPerSecond attribute to recommender APIs.
* api-change:``athena``: This release adds a field, AthenaError, to the GetQueryExecution response object when a query fails.


2.4.15
======

* api-change:``securityhub``: Adding top level Sample boolean field
* api-change:``frauddetector``: Added new APIs for viewing past predictions and obtaining prediction metadata including prediction explanations: ListEventPredictions and GetEventPredictionMetadata
* api-change:``ebs``: Documentation updates for Amazon EBS Direct APIs.
* api-change:``amplify``: Doc only update to the description of basicauthcredentials to describe the required encoding and format.
* api-change:``kafka``: Amazon MSK has updated the CreateCluster and UpdateBrokerStorage API that allows you to specify volume throughput during cluster creation and broker volume updates.
* api-change:``opensearch``: Allows customers to get progress updates for blue/green deployments
* api-change:``codeguru-reviewer``: Added failure state and adjusted timeout in waiter
* api-change:``ec2``: X2ezn instances are powered by Intel Cascade Lake CPUs that deliver turbo all core frequency of up to 4.5 GHz and up to 100 Gbps of networking bandwidth
* api-change:``connect``: This release adds support for configuring a custom chat duration when starting a new chat session via the StartChatContact API. The default value for chat duration is 25 hours, minimum configurable value is 1 hour (60 minutes) and maximum configurable value is 7 days (10,080 minutes).
* api-change:``sagemaker``: API changes relating to Fail steps in model building pipeline and add PipelineExecutionFailureReason in PipelineExecutionSummary.


2.4.14
======

* api-change:``transcribe``: Add support for granular PIIEntityTypes when using Batch ContentRedaction.
* api-change:``connect``: This release adds support for custom vocabularies to be used with Contact Lens. Custom vocabularies improve transcription accuracy for one or more specific words.
* api-change:``efs``: Update efs command to latest version
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for 4K AV1 output resolutions & 10-bit AV1 color, the ability to ingest sidecar Dolby Vision XML metadata files, and the ability to flag WebVTT and IMSC tracks for accessibility in HLS.
* api-change:``guardduty``: Amazon GuardDuty expands threat detection coverage to protect Amazon Elastic Kubernetes Service (EKS) workloads.
* api-change:``fsx``: This release adds support for growing SSD storage capacity and growing/shrinking SSD IOPS for FSx for ONTAP file systems.
* api-change:``route53-recovery-readiness``: Updated documentation for Route53 Recovery Readiness APIs.


2.4.13
======

* api-change:``guardduty``: Amazon GuardDuty findings now include remoteAccountDetails under AwsApiCallAction section if instance credential is exfiltrated.
* api-change:``mediatailor``: This release adds support for multiple Segment Delivery Configurations. Users can provide a list of names and URLs when creating or editing a source location. When retrieving content, users can send a header to choose which URL should be used to serve content.
* api-change:``ec2``: C6i, M6i and R6i instances are powered by a third-generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz
* api-change:``macie2``: This release of the Amazon Macie API introduces stricter validation of requests to create custom data identifiers.
* api-change:``connect``: This release adds tagging support for UserHierarchyGroups resource.
* api-change:``fis``: Added action startTime and action endTime timestamp fields to the ExperimentAction object
* api-change:``ec2-instance-connect``: Adds support for ED25519 keys. PushSSHPublicKey Availability Zone parameter is now optional. Adds EC2InstanceStateInvalidException for instances that are not running. This was previously a service exception, so this may require updating your code to handle this new exception.


2.4.12
======

* api-change:``ram``: This release adds the ListPermissionVersions API which lists the versions for a given permission.
* api-change:``lookoutmetrics``: This release adds a new DeactivateAnomalyDetector API operation.
* api-change:``location``: This release adds the CalculateRouteMatrix API which calculates routes for the provided departure and destination positions. The release also deprecates the use of pricing plan across all verticals.
* api-change:``cloudtrail``: This release fixes a documentation bug in the description for the readOnly field selector in advanced event selectors. The description now clarifies that users omit the readOnly field selector to select both Read and Write management events.
* api-change:``application-insights``: Application Insights support for Active Directory and SharePoint
* api-change:``ec2``: Add support for AWS Client VPN client login banner and session timeout.
* api-change:``config``: Update ResourceType enum with values for CodeDeploy, EC2 and Kinesis resources
* api-change:``honeycode``: Added read and write api support for multi-select picklist. And added errorcode field to DescribeTableDataImportJob API output, when import job fails.
* api-change:``ivs``: This release adds support for the new Thumbnail Configuration property for Recording Configurations. For more information see https://docs.aws.amazon.com/ivs/latest/userguide/record-to-s3.html
* api-change:``storagegateway``: Documentation update for adding bandwidth throttling support for S3 File Gateways.


2.4.11
======

* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``ec2``: Hpc6a instances are powered by a third-generation AMD EPYC processors (Milan) delivering all-core turbo frequency of 3.4 GHz
* api-change:``pinpoint``: Adds JourneyChannelSettings to WriteJourneyRequest
* api-change:``honeycode``: Honeycode is releasing new APIs to allow user to create, delete and list tags on resources.
* api-change:``pi``: This release adds three Performance Insights APIs. Use ListAvailableResourceMetrics to get available metrics, GetResourceMetadata to get feature metadata, and ListAvailableResourceDimensions to list available dimensions. The AdditionalMetrics field in DescribeDimensionKeys retrieves per-SQL metrics.
* api-change:``fms``: Shield Advanced policies for Amazon CloudFront resources now support automatic application layer DDoS mitigation. The max length for SecurityServicePolicyData ManagedServiceData is now 8192 characters, instead of 4096.
* api-change:``elasticache``: AWS ElastiCache for Redis has added a new Engine Log LogType in LogDelivery feature. You can now publish the Engine Log from your Amazon ElastiCache for Redis clusters to Amazon CloudWatch Logs and Amazon Kinesis Data Firehose.
* api-change:``nimble``: Amazon Nimble Studio now supports validation for Launch Profiles. Launch Profiles now report static validation results after create/update to detect errors in network or active directory configuration.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``glue``: This SDK release adds support to pass run properties when starting a workflow run
* api-change:``ssm``: AWS Systems Manager adds category support for DescribeDocument API


2.4.10
======

* api-change:``kendra``: Amazon Kendra now supports advanced query language and query-less search.
* api-change:``medialive``: This release adds support for selecting the Program Date Time (PDT) Clock source algorithm for HLS outputs.
* api-change:``workspaces``: Introducing new APIs for Workspaces audio optimization with Amazon Connect: CreateConnectClientAddIn, DescribeConnectClientAddIns, UpdateConnectClientAddIn and DeleteConnectClientAddIn.
* api-change:``compute-optimizer``: Adds support for new Compute Optimizer capability that makes it easier for customers to optimize their EC2 instances by leveraging multiple CPU architectures.
* api-change:``ce``: Doc only update for Cost Explorer API that fixes missing clarifications for MatchOptions definitions
* api-change:``ec2``: EC2 Capacity Reservations now supports RHEL instance platforms (RHEL with SQL Server Standard, RHEL with SQL Server Enterprise, RHEL with SQL Server Web, RHEL with HA, RHEL with HA and SQL Server Standard, RHEL with HA and SQL Server Enterprise)
* api-change:``lookoutmetrics``: This release adds FailureType in the response of DescribeAnomalyDetector.
* api-change:``finspace-data``: Documentation updates for FinSpace.
* api-change:``rds``: This release adds the db-proxy event type to support subscribing to RDS Proxy events.
* api-change:``ec2``: New feature: Updated EC2 API to support faster launching for Windows images. Optimized images are pre-provisioned, using snapshots to launch instances up to 65% faster.
* api-change:``iotevents-data``: This release provides documentation updates for Timer.timestamp in the IoT Events API Reference Guide.
* api-change:``databrew``: This SDK release adds support for specifying a Bucket Owner for an S3 location.
* api-change:``transcribe``: Documentation updates for Amazon Transcribe.


2.4.9
=====

* api-change:``iot``: This release adds an automatic retry mechanism for AWS IoT Jobs. You can now define a maximum number of retries for each Job rollout, along with the criteria to trigger the retry for FAILED/TIMED_OUT/ALL(both FAILED an TIMED_OUT) job.
* api-change:``opensearch``: Amazon OpenSearch Service adds support for Fine Grained Access Control for existing domains running Elasticsearch version 6.7 and above
* api-change:``lakeformation``: Add new APIs for 3rd Party Support for Lake Formation
* api-change:``glue``: Add Delta Lake target support for Glue Crawler and 3rd Party Support for Lake Formation
* api-change:``ec2``: This release introduces On-Demand Capacity Reservation support for Cluster Placement Groups, adds Tags on instance Metadata, and includes documentation updates for Amazon EC2.
* api-change:``appsync``: AppSync: AWS AppSync now supports configurable batching sizes for AWS Lambda resolvers, Direct AWS Lambda resolvers and pipeline functions
* api-change:``mwaa``: This release adds a "Source" field that provides the initiator of an update, such as due to an automated patch from AWS or due to modification via Console or API.
* api-change:``iotwireless``: Downlink Queue Management feature provides APIs for customers to manage the queued messages destined to device inside AWS IoT Core for LoRaWAN. Customer can view, delete or purge the queued message(s). It allows customer to preempt the queued messages and let more urgent messages go through.
* api-change:``sagemaker``: Amazon SageMaker now supports running training jobs on ml.g5 instance types.
* api-change:``quicksight``: Multiple Doc-only updates for Amazon QuickSight.
* api-change:``appstream``: Includes APIs for App Entitlement management regarding entitlement and entitled application association.
* api-change:``eks``: Amazon EKS now supports running applications using IPv6 address space
* api-change:``snowball``: Updating validation rules for interfaces used in the Snowball API to tighten security of service.
* api-change:``ec2``: This release adds a new API called ModifyVpcEndpointServicePayerResponsibility which allows VPC endpoint service owners to take payer responsibility of their VPC Endpoint connections.
* api-change:``cloudtrail``: This release adds support for CloudTrail Lake, a new feature that lets you run SQL-based queries on events that you have aggregated into event data stores. New APIs have been added for creating and managing event data stores, and creating, running, and managing queries in CloudTrail Lake.
* api-change:``mediatailor``: This release adds support for filler slate when updating MediaTailor channels that use the linear playback mode.
* api-change:``es``: Amazon OpenSearch Service adds support for Fine Grained Access Control for existing domains running Elasticsearch version 6.7 and above
* api-change:``ecs``: Documentation update for ticket fixes.


2.4.8
=====

* api-change:``s3``: Minor doc-based updates based on feedback bugs received.
* api-change:``detective``: Added and updated API operations to support the Detective integration with AWS Organizations. New actions are used to manage the delegated administrator account and the integration configuration.
* api-change:``greengrassv2``: This release adds the API operations to manage the Greengrass role associated with your account and to manage the core device connectivity information. Greengrass V2 customers can now depend solely on Greengrass V2 SDK for all the API operations needed to manage their fleets.
* api-change:``sagemaker``: The release allows users to pass pipeline definitions as Amazon S3 locations and control the pipeline execution concurrency using ParallelismConfiguration. It also adds support of EMR jobs as pipeline steps.
* api-change:``rds``: Multiple doc-only updates for Relational Database Service (RDS)
* api-change:``s3control``: Documentation updates for the renaming of Glacier to Glacier Flexible Retrieval.
* api-change:``rekognition``: This release introduces a new field IndexFacesModelVersion, which is the version of the face detect and storage model that was used when indexing the face vector.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added strength levels to the Sharpness Filter and now permits OGG files to be specified as sidecar audio inputs.


2.4.7
=====

* api-change:``imagebuilder``: Added a note to infrastructure configuration actions and data types concerning delivery of Image Builder event messages to encrypted SNS topics. The key that's used to encrypt the SNS topic must reside in the account that Image Builder runs under.
* api-change:``location``: Making PricingPlan optional as part of create resource API.
* api-change:``devops-guru``: Adds Tags support to DescribeOrganizationResourceCollectionHealth
* api-change:``customer-profiles``: This release adds an optional parameter, ObjectTypeNames to the PutIntegration API to support multiple object types per integration option. Besides, this release introduces Standard Order Objects which contain data from third party systems and each order object belongs to a specific profile.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports updating message attributes via channel flows
* api-change:``qldb``: Amazon QLDB now supports journal exports in JSON and Ion Binary formats. This release adds an optional OutputFormat parameter to the ExportJournalToS3 API.
* api-change:``finspace-data``: Make dataset description optional and allow s3 export for dataviews
* api-change:``redshift``: This release adds API support for managed Redshift datashares. Customers can now interact with a Redshift datashare that is managed by a different service, such as AWS Data Exchange.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``datasync``: AWS DataSync now supports FSx Lustre Locations.
* api-change:``mediaconnect``: You can now use the Fujitsu-QoS protocol for your MediaConnect sources and outputs to transport content to and from Fujitsu devices.
* api-change:``forecast``: Adds ForecastDimensions field to the DescribeAutoPredictorResponse
* api-change:``nimble``: Amazon Nimble Studio adds support for users to upload files during a streaming session using NICE DCV native client or browser.
* api-change:``apigateway``: Documentation updates for Amazon API Gateway
* api-change:``transfer``: Property for Transfer Family used with the FTPS protocol. TLS Session Resumption provides a mechanism to resume or share a negotiated secret key between the control and data connection for an FTPS session.
* api-change:``workmail``: This release allows customers to change their email monitoring configuration in Amazon WorkMail.
* api-change:``sagemaker``: This release adds a new ContentType field in AutoMLChannel for SageMaker CreateAutoMLJob InputDataConfig.
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for Firewall, and RuleGroup, FirewallPolicy Added additional details for AutoScalingGroup, LaunchConfiguration, and S3 buckets.
* api-change:``imagebuilder``: This release adds support for importing and exporting VM Images as part of the Image Creation workflow via EC2 VM Import/Export.
* api-change:``lookoutmetrics``: This release adds support for Causal Relationships. Added new ListAnomalyGroupRelatedMetrics API operation and InterMetricImpactDetails API data type


2.4.6
=====

* api-change:``health``: Documentation updates for AWS Health
* api-change:``savingsplans``: Adds the ability to specify Savings Plans hourly commitments using five digits after the decimal point.
* bugfix:s3: Support for S3 Glacer Instant Retrieval storage class.  Fixes `#6587 <https://github.com/aws/aws-cli/issues/6587>`__
* api-change:``ec2``: Adds waiters support for internet gateways.
* api-change:``logs``: This release adds AWS Organizations support as condition key in destination policy for cross account Subscriptions in CloudWatch Logs.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``route53domains``: Amazon Route 53 domain registration APIs now support filtering and sorting in the ListDomains API, deleting a domain by using the DeleteDomain API and getting domain pricing information by using the ListPrices API.
* api-change:``location``: This release adds support for Accuracy position filtering, position metadata and autocomplete for addresses and points of interest based on partial or misspelled free-form text.
* api-change:``appsync``: AWS AppSync now supports custom domain names, allowing you to associate a domain name that you own with an AppSync API in your account.
* api-change:``support``: Documentation updates for AWS Support.
* api-change:``sms``: This release adds SMS discontinuation information to the API and CLI references.
* api-change:``network-firewall``: This release adds support for managed rule groups.
* api-change:``route53``: Add PriorRequestNotComplete exception to UpdateHostedZoneComment API
* api-change:``sagemaker``: This release added a new Ambarella device(amba_cv2) compilation support for Sagemaker Neo.
* api-change:``route53-recovery-control-config``: This release adds tagging supports to Route53 Recovery Control Configuration. New APIs: TagResource, UntagResource and ListTagsForResource. Updates: add optional field `tags` to support tagging while calling CreateCluster, CreateControlPanel and CreateSafetyRule.
* api-change:``iot``: This release allows customer to enable caching of custom authorizer on HTTP protocol for clients that use persistent or Keep-Alive connection in order to reduce the number of Lambda invocations.
* api-change:``outposts``: This release adds the UpdateOutpost API.
* api-change:``comprehendmedical``: This release adds a new set of APIs (synchronous and batch) to support the SNOMED-CT ontology.
* api-change:``lookoutvision``: This release adds new APIs for packaging an Amazon Lookout for Vision model as an AWS IoT Greengrass component.


2.4.5
=====

* api-change:``networkmanager``: This release adds API support for AWS Cloud WAN.
* api-change:``rekognition``: This release added new KnownGender types for Celebrity Recognition.
* api-change:``amplifyuibuilder``: This release introduces the actions and data types for the new Amplify UI Builder API. The Amplify UI Builder API provides a programmatic interface for creating and configuring user interface (UI) component libraries and themes for use in Amplify applications.
* api-change:``ram``: This release adds the ability to use the new ResourceRegionScope parameter on List operations that return lists of resources or resource types. This new parameter filters the results by letting you differentiate between global or regional resource types.


2.4.4
=====

* api-change:``lakeformation``: This release adds support for row and cell-based access control in Lake Formation. It also adds support for Lake Formation Governed Tables, which support ACID transactions and automatic storage optimizations.
* api-change:``iottwinmaker``: AWS IoT TwinMaker makes it faster and easier to create, visualize and monitor digital twins of real-world systems like buildings, factories and industrial equipment to optimize operations. Learn more: https://docs.aws.amazon.com/iot-twinmaker/latest/apireference/Welcome.html (New Service) (Preview)
* api-change:``snowball``: Tapeball is to integrate tape gateway onto snowball, it enables customer to transfer local data on the tape to snowball,and then ingest the data into tape gateway on the cloud.
* api-change:``workspaces-web``: This is the initial SDK release for Amazon WorkSpaces Web. Amazon WorkSpaces Web is a low-cost, fully managed WorkSpace built to deliver secure web-based workloads and software-as-a-service (SaaS) application access to users within existing web browsers.
* api-change:``shield``: This release adds API support for Automatic Application Layer DDoS Mitigation for AWS Shield Advanced. Customers can now enable automatic DDoS mitigation in count or block mode for layer 7 protected resources.
* api-change:``iot``: Added the ability to enable/disable IoT Fleet Indexing for Device Defender and Named Shadow information, and search them through IoT Fleet Indexing APIs.
* api-change:``accessanalyzer``: AWS IAM Access Analyzer now supports policy validation for resource policies attached to S3 buckets and access points. You can run additional policy checks by specifying the S3 resource type you want to attach to your resource policy.
* api-change:``kafka``: This release adds three new V2 APIs. CreateClusterV2 for creating both provisioned and serverless clusters. DescribeClusterV2 for getting information about provisioned and serverless clusters and ListClustersV2 for listing all clusters (both provisioned and serverless) in your account.
* api-change:``directconnect``: Adds SiteLink support to private and transit virtual interfaces. SiteLink is a new Direct Connect feature that allows routing between Direct Connect points of presence.
* api-change:``ec2``: This release adds support for Is4gen and Im4gn instances. This release also adds a new subnet attribute, enableLniAtDeviceIndex, to support local network interfaces, which are logical networking components that connect an EC2 instance to your on-premises network.
* api-change:``redshift-data``: Data API now supports serverless queries.
* api-change:``glue``: Support for DataLake transactions
* api-change:``s3``: Introduce Amazon S3 Glacier Instant Retrieval storage class and a new setting in S3 Object Ownership to disable ACLs for bucket and the objects in it.
* api-change:``outposts``: This release adds the SupportedHardwareType parameter to CreateOutpost.
* api-change:``kinesis``: Amazon Kinesis Data Streams now supports on demand streams.
* api-change:``sagemaker``: This release enables - 1/ Inference endpoint configuration recommendations and ability to run custom load tests to meet performance needs. 2/ Deploy serverless inference endpoints. 3/ Query, filter and retrieve end-to-end ML lineage graph, and incorporate model quality/bias detection in ML workflow.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``backup-gateway``: Initial release of AWS Backup gateway which enables you to centralize and automate protection of on-premises VMware and VMware Cloud on AWS workloads using AWS Backup.
* api-change:``dynamodb``: Add support for Table Classes and introduce the Standard Infrequent Access table class.
* api-change:``ec2``: This release adds support for Amazon VPC IP Address Manager (IPAM), which enables you to plan, track, and monitor IP addresses for your workloads. This release also adds support for VPC Network Access Analyzer, which enables you to analyze network access to resources in your Virtual Private Clouds.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``kendra``: Experience Builder allows customers to build search applications without writing code. Analytics Dashboard provides quality and usability metrics for Kendra indexes. Custom Document Enrichment allows customers to build a custom ingestion pipeline to pre-process documents and generate metadata.
* api-change:``fsx``: This release adds support for the FSx for OpenZFS file system type, FSx for Lustre file systems with the Persistent_2 deployment type, and FSx for Lustre file systems with Amazon S3 data repository associations and automatic export policies.
* api-change:``devops-guru``: DevOps Guru now provides detailed, database-specific analyses of performance issues and recommends corrective actions for Amazon Aurora database instances with Performance Insights turned on. You can also use AWS tags to choose which resources to analyze and define your applications.
* api-change:``storagegateway``: Added gateway type VTL_SNOW. Added new SNOWBALL HostEnvironment for gateways running on a Snowball device. Added new field HostEnvironmentId to serve as an identifier for the HostEnvironment on which the gateway is running.


2.4.3
=====

* api-change:``personalize``: This release adds API support for Recommenders and BatchSegmentJobs.
* api-change:``dataexchange``: This release enables providers and subscribers to use Data Set, Job, and Asset operations to work with API assets from Amazon API Gateway. In addition, this release enables subscribers to use the SendApiAsset operation to invoke a provider's Amazon API Gateway API that they are entitled to.
* api-change:``s3``: Amazon S3 Event Notifications adds Amazon EventBridge as a destination and supports additional event types. The PutBucketNotificationConfiguration API can now skip validation of Amazon SQS, Amazon SNS and AWS Lambda destinations.
* api-change:``ssm``: Added two new attributes to DescribeInstanceInformation called SourceId and SourceType along with new string filters SourceIds and SourceTypes to filter instance records.
* api-change:``textract``: This release adds support for synchronously analyzing identity documents through a new API: AnalyzeID
* api-change:``migration-hub-refactor-spaces``: This is the initial SDK release for AWS Migration Hub Refactor Spaces
* api-change:``ecr``: This release adds supports for pull through cache rules and enhanced scanning.
* api-change:``inspector2``: This release adds support for the new Amazon Inspector API. The new Amazon Inspector can automatically discover and scan Amazon EC2 instances and Amazon ECR container images for software vulnerabilities and unintended network exposure, and report centralized findings across multiple AWS accounts.
* api-change:``evidently``: Introducing Amazon CloudWatch Evidently. This is the first public release of Amazon CloudWatch Evidently.
* api-change:``rum``: This is the first public release of CloudWatch RUM
* api-change:``ec2``: This release adds support for G5g and M6a instances. This release also adds support for Amazon EBS Snapshots Archive, a feature that enables you to archive your EBS snapshots; and Recycle Bin, a feature that enables you to protect your EBS snapshots against accidental deletion.
* api-change:``rbin``: This release adds support for Recycle Bin.
* enhancement:Wizards: Add save to file option for more details panel (`#6574 <https://github.com/aws/aws-cli/issues/6574>`__).
* enhancement:``new-rule``: Add support for CloudWatch Logs as a target and CodeCommit as a source (`#6575 <https://github.com/aws/aws-cli/issues/6575>`__).
* api-change:``wellarchitected``: This update provides support for Well-Architected API users to use custom lens features.
* enhancement:``new-rule``: Add support for specifying custom event pattern for new-rule EventBridge wizard (`#6573 <https://github.com/aws/aws-cli/issues/6573>`__).
* api-change:``personalize-runtime``: This release adds inference support for Recommenders.
* api-change:``compute-optimizer``: Adds support for the enhanced infrastructure metrics paid feature. Also adds support for two new sets of resource efficiency metrics, including savings opportunity metrics and performance improvement opportunity metrics.
* api-change:``iotsitewise``: AWS IoT SiteWise now supports retention configuration for the hot tier storage.


2.4.2
=====

* api-change:``iotdeviceadvisor``: Documentation update for Device Advisor GetEndpoint API
* api-change:``proton``: This release adds APIs for getting the outputs and provisioned stacks for Environments, Pipelines, and ServiceInstances.  You can now add tags to EnvironmentAccountConnections.  It also adds APIs for working with PR-based provisioning.  Also, it adds APIs for syncing templates with a git repository.
* api-change:``outposts``: This release adds new APIs for working with Outpost sites and orders.
* api-change:``timestream-query``: Releasing Amazon Timestream Scheduled Queries. It makes real-time analytics more performant and cost-effective for customers by calculating and storing frequently accessed aggregates, and other computations, typically used in operational dashboards, business reports, and other analytics applications
* api-change:``ec2``: Documentation updates for EC2.
* api-change:``lambda``: Remove Lambda function url apis
* api-change:``customer-profiles``: This release introduces a new auto-merging feature for profile matching. The auto-merging configurations can be set via CreateDomain API or UpdateDomain API. You can use GetIdentityResolutionJob API and ListIdentityResolutionJobs API to fetch job status.
* api-change:``pinpoint``: Added a One-Time Password (OTP) management feature. You can use the Amazon Pinpoint API to generate OTP codes and send them to your users as SMS messages. Your apps can then call the API to verify the OTP codes that your users input
* api-change:``autoscaling``: Customers can now configure predictive scaling policies to proactively scale EC2 Auto Scaling groups based on any CloudWatch metrics that more accurately represent the load on the group than the four predefined metrics. They can also use math expressions to further customize the metrics.
* api-change:``translate``: This release enables customers to use translation settings to mask profane words and phrases in their translation output.
* api-change:``timestream-write``: This release adds support for multi-measure records and magnetic store writes. Multi-measure records allow customers to store multiple measures in a single table row. Magnetic store writes enable customers to write late arrival data (data with timestamp in the past) directly into the magnetic store.
* api-change:``imagebuilder``: This release adds support for sharing AMIs with Organizations within an EC2 Image Builder Distribution Configuration.
* api-change:``mgn``: Application Migration Service now supports an additional replication method that does not require agent installation on each source server. This option is available for source servers running on VMware vCenter versions 6.7 and 7.0.
* api-change:``iotsitewise``: AWS IoT SiteWise now accepts data streams that aren't associated with any asset properties. You can organize data by updating data stream associations.
* api-change:``elasticache``: Doc only update for ElastiCache
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling.


2.4.1
=====

* api-change:``lambda``: Add support for Lambda Function URLs. Customers can use Function URLs to create built-in HTTPS endpoints on their functions.
* api-change:``s3control``: Added Amazon CloudWatch publishing option for S3 Storage Lens metrics.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``rds``: Adds local backup support to Amazon RDS on AWS Outposts.
* api-change:``backup``: This release adds new opt-in settings for advanced features for DynamoDB backups
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``sqs``: Amazon SQS adds a new queue attribute, SqsManagedSseEnabled, which enables server-side queue encryption using SQS owned encryption keys.
* api-change:``ssm``: Adds new parameter to CreateActivation API . This parameter is for "internal use only".
* api-change:``opensearch``: This release adds an optional parameter dry-run for the UpdateDomainConfig API to perform basic validation checks, and detect the deployment type that will be required for the configuration change, without actually applying the change.
* api-change:``iotdeviceadvisor``: This release introduces a new feature for Device Advisor: ability to execute multiple test suites in parallel for given customer account. You can use GetEndpoint API to get the device-level test endpoint and call StartSuiteRun with "parallelRun=true" to run suites in parallel.
* api-change:``sts``: Documentation updates for AWS Security Token Service.
* api-change:``redshift``: This release adds support for reserved node exchange with restore/resize
* api-change:``chime-sdk-meetings``: Added new APIs for enabling Echo Reduction with Voice Focus.
* api-change:``dynamodb``: DynamoDB PartiQL now supports ReturnConsumedCapacity, which returns capacity units consumed by PartiQL APIs if the request specified returnConsumedCapacity parameter. PartiQL APIs include ExecuteStatement, BatchExecuteStatement, and ExecuteTransaction.
* api-change:``s3``: Introduce two new Filters to S3 Lifecycle configurations - ObjectSizeGreaterThan and ObjectSizeLessThan. Introduce a new way to trigger actions on noncurrent versions by providing the number of newer noncurrent versions along with noncurrent days.
* api-change:``finspace-data``: Update documentation for createChangeset API.
* api-change:``appstream``: Includes APIs for managing resources for Elastic fleets: applications, app blocks, and application-fleet associations.
* api-change:``cloudformation``: The StackSets ManagedExecution feature will allow concurrency for non-conflicting StackSet operations and queuing the StackSet operations that conflict at a given time for later execution.
* api-change:``connect``: This release adds support for UpdateContactFlowMetadata, DeleteContactFlow and module APIs. For details, see the Release Notes in the Amazon Connect Administrator Guide.
* api-change:``batch``: Documentation updates for AWS Batch.
* api-change:``eks``: Adding missing exceptions to RegisterCluster operation
* api-change:``es``: This release adds an optional parameter dry-run for the UpdateElasticsearchDomainConfig API to perform basic validation checks, and detect the deployment type that will be required for the configuration change, without actually applying the change.
* api-change:``finspace-data``: Add new APIs for managing Datasets, Changesets, and Dataviews.
* enhancement:``logs``: Add a JSON pretty print log format to the ``aws logs tail`` command.
* api-change:``dms``: Added new S3 endpoint settings to allow to convert the current UTC time into a specified time zone when a date partition folder is created. Using with 'DatePartitionedEnabled'.
* api-change:``quicksight``: Add support for Exasol data source, 1 click enterprise embedding and email customization.
* api-change:``application-insights``: Application Insights now supports monitoring for HANA
* api-change:``elasticache``: Adding support for r6gd instances for Redis with data tiering. In a cluster with data tiering enabled, when available memory capacity is exhausted, the least recently used data is automatically tiered to solid state drives for cost-effective capacity scaling with minimal performance impact.
* api-change:``medialive``: This release adds support for specifying a SCTE-35 PID on input. MediaLive now supports SCTE-35 PID selection on inputs containing one or more active SCTE-35 PIDs.
* api-change:``redshift``: Added support of default IAM role for CreateCluster, RestoreFromClusterSnapshot and ModifyClusterIamRoles APIs
* api-change:``macie2``: Documentation updates for Amazon Macie
* enhancement:``cloudformation``: Expand the ``~`` character for the template file argument in the ``aws cloudformation deploy`` command.
* api-change:``iot``: This release introduces a new feature, Managed Job Template, for AWS IoT Jobs Service. Customers can now use service provided managed job templates to easily create jobs for supported standard job actions.
* api-change:``iotwireless``: Two new APIs, GetNetworkAnalyzerConfiguration and UpdateNetworkAnalyzerConfiguration, are added for the newly released Network Analyzer feature which enables customers to view real-time frame information and logs from LoRaWAN devices and gateways.
* api-change:``braket``: This release adds support for Amazon Braket Hybrid Jobs.
* api-change:``lambda``: Release Lambda event source filtering for SQS, Kinesis Streams, and DynamoDB Streams.
* api-change:``cloudformation``: This release include SDK changes for the feature launch of Stack Import to Service Managed StackSet.
* api-change:``workspaces``: Documentation updates for Amazon WorkSpaces
* api-change:``ecs``: Documentation update for ARM support on Amazon ECS.
* api-change:``ec2``: This release adds a new parameter ipv6Native to the allow creation of IPv6-only subnets using the CreateSubnet operation, and the operation ModifySubnetAttribute includes new parameters to modify subnet attributes to use resource-based naming and enable DNS resolutions for Private DNS name.
* api-change:``rds``: Adds support for Multi-AZ DB clusters for RDS for MySQL and RDS for PostgreSQL.


2.4.0
=====

* api-change:``drs``: Introducing AWS Elastic Disaster Recovery (AWS DRS), a new service that minimizes downtime and data loss with fast, reliable recovery of on-premises and cloud-based applications using affordable storage, minimal compute, and point-in-time recovery.
* feature:Endpoints: Add support for resolving FIPS and Dualstack endpoints via AWS_USE_DUALSTACK_ENDPOINT and AWS_USE_FIPS_ENDPOINT environment variables as well as shared config file variables.
* api-change:``kafka``: Amazon MSK has added a new API that allows you to update the connectivity settings for an existing cluster to enable public accessibility.
* api-change:``forecast``: NEW CreateExplanability API that helps you understand how attributes such as price, promotion, etc. contributes to your forecasted values; NEW CreateAutoPredictor API that trains up to 40% more accurate forecasting model, saves up to 50% of retraining time, and provides model level explainability.
* api-change:``chime-sdk-meetings``: Adds new Transcribe API parameters to StartMeetingTranscription, including support for content identification and redaction (PII & PHI), partial results stabilization, and custom language models.
* api-change:``sns``: Amazon SNS introduces the PublishBatch API, which enables customers to publish up to 10 messages per API request. The new API is valid for Standard and FIFO topics.
* api-change:``appconfigdata``: AWS AppConfig Data is a new service that allows you to retrieve configuration deployed by AWS AppConfig. See the AppConfig user guide for more details on getting started. https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
* api-change:``lambda``: Added support for CLIENT_CERTIFICATE_TLS_AUTH and SERVER_ROOT_CA_CERTIFICATE as SourceAccessType for MSK and Kafka event source mappings.
* api-change:``ivs``: Add APIs for retrieving stream session information and support for filtering live streams by health.  For more information, see https://docs.aws.amazon.com/ivs/latest/userguide/stream-health.html
* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Dashboard views. You can now view insights data for your active assessments, and quickly identify non-compliant evidence that needs to be remediated.
* api-change:``appconfig``: Add Type to support feature flag configuration profiles
* api-change:``chime``: Adds new Transcribe API parameters to StartMeetingTranscription, including support for content identification and redaction (PII & PHI), partial results stabilization, and custom language models.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``apigateway``: Documentation updates for Amazon API Gateway.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``databrew``: This SDK release adds the following new features: 1) PII detection in profile jobs, 2) Data quality rules, enabling validation of data quality in profile jobs, 3) SQL query-based datasets for Amazon Redshift and Snowflake data sources, and 4) Connecting DataBrew datasets with Amazon AppFlow flows.
* api-change:``amplifybackend``: New APIs to support the Amplify Storage category. Add and manage file storage in your Amplify app backend.


2.3.7
=====

* api-change:``location``: This release adds the support for Relevance, Distance, Time Zone, Language and Interpolated Address for Geocoding and Reverse Geocoding.
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added automatic modes for GOP configuration and added the ability to ingest screen recordings generated by Safari on MacOS 12 Monterey.
* api-change:``ec2``: Adds a new VPC Subnet attribute "EnableDns64." When enabled on IPv6 Subnets, the Amazon-Provided DNS Resolver returns synthetic IPv6 addresses for IPv4-only destinations.
* api-change:``ssm``: This Patch Manager release supports creating Patch Baselines for RaspberryPi OS (formerly Raspbian)
* api-change:``connect``: This release adds APIs for creating and managing scheduled tasks. Additionally, adds APIs to describe and update a contact and list associated references.
* api-change:``ssm``: Adds support for Session Reason and Max Session Duration for Systems Manager Session Manager.
* api-change:``transfer``: AWS Transfer Family now supports integrating a custom identity provider using AWS Lambda
* api-change:``ec2``: C6i instances are powered by a third-generation Intel Xeon Scalable processor (Ice Lake) delivering all-core turbo frequency of 3.5 GHz. G5 instances feature up to 8 NVIDIA A10G Tensor Core GPUs and second generation AMD EPYC processors.
* api-change:``migrationhubstrategy``: AWS SDK for Migration Hub Strategy Recommendations. It includes APIs to start the portfolio assessment, import portfolio data for assessment, and to retrieve recommendations. For more information, see the AWS Migration Hub documentation at https://docs.aws.amazon.com/migrationhub/index.html
* api-change:``wafv2``: Your options for logging web ACL traffic now include Amazon CloudWatch Logs log groups and Amazon S3 buckets.
* api-change:``devops-guru``: Add support for cross account APIs.
* api-change:``appstream``: This release includes support for images of AmazonLinux2 platform type.
* api-change:``eks``: Adding Tags support to Cluster Registrations.
* api-change:``cloudtrail``: CloudTrail Insights now supports ApiErrorRateInsight, which enables customers to identify unusual activity in their AWS account based on API error codes and their rate.
* api-change:``dms``: Add Settings in JSON format for the source GCP MySQL endpoint


2.3.6
=====

* api-change:``resiliencehub``: Initial release of AWS Resilience Hub, a managed service that enables you to define, validate, and track the resilience of your applications on AWS
* api-change:``backup``: AWS Backup SDK provides new options when scheduling backups: select supported services and resources that are assigned to a particular tag, linked to a combination of tags, or can be identified by a partial tag value, and exclude resources from their assignments.
* api-change:``ecs``: This release adds support for container instance health.
* api-change:``ec2``: This release provides an additional route target for the VPC route table.
* api-change:``translate``: This release enables customers to import Multi-Directional Custom Terminology and use Multi-Directional Custom Terminology in both real-time translation and asynchronous batch translation.
* api-change:``dynamodb``: Updated Help section for "dynamodb update-contributor-insights" API


2.3.5
=====

* api-change:``health``: Documentation updates for AWS Health.
* api-change:``chime-sdk-meetings``: Updated format validation for ids and regions.
* api-change:``resourcegroupstaggingapi``: Documentation updates and improvements.
* api-change:``sagemaker``: SageMaker CreateEndpoint and UpdateEndpoint APIs now support additional deployment configuration to manage traffic shifting options and automatic rollback monitoring. DescribeEndpoint now shows new in-progress deployment details with stage status.
* api-change:``wafv2``: You can now configure rules to run a CAPTCHA check against web requests and, as needed, send a CAPTCHA challenge to the client.
* api-change:``ec2``: This release adds internal validation on the GatewayAssociationState field
* api-change:``batch``: Adds support for scheduling policy APIs.
* api-change:``ec2``: DescribeInstances now returns customer-owned IP addresses for instances running on an AWS Outpost.
* api-change:``translate``: This release enable customers to use their own KMS keys to encrypt output files when they submit a batch transform job.
* api-change:``greengrassv2``: This release adds support for Greengrass core devices running Windows. You can now specify name of a Windows user to run a component.


2.3.4
=====

* api-change:``iotwireless``: Adding APIs for the FUOTA (firmware update over the air) and multicast for LoRaWAN devices and APIs to support event notification opt-in feature for Sidewalk related events. A few existing APIs need to be modified for this new feature.
* api-change:``ec2``: This release adds a new instance replacement strategy for EC2 Fleet, Spot Fleet. Now you can select an action to perform when your instance gets a rebalance notification. EC2 Fleet, Spot Fleet can launch a replacement then terminate the instance that received notification after a termination delay
* api-change:``connectparticipant``: This release adds a new boolean attribute - Connect Participant - to the CreateParticipantConnection API, which can be used to mark the participant as connected.
* api-change:``sagemaker``: ListDevices and DescribeDevice now show Edge Manager agent version.
* api-change:``connect``: This release adds CRUD operation support for Security profile resource in Amazon Connect
* api-change:``datasync``: AWS DataSync now supports Hadoop Distributed File System (HDFS) Locations
* api-change:``finspace``: Adds superuser and data-bundle parameters to CreateEnvironment API
* api-change:``chime-sdk-meetings``: The Amazon Chime SDK Meetings APIs allow software developers to create meetings and attendees for interactive audio, video, screen and content sharing in custom meeting applications which use the Amazon Chime SDK.
* api-change:``macie2``: This release adds support for specifying the severity of findings that a custom data identifier produces, based on the number of occurrences of text that matches the detection criteria.


2.3.3
=====

* api-change:``cloudfront``: CloudFront now supports response headers policies to add HTTP headers to the responses that CloudFront sends to viewers. You can use these policies to add CORS headers, control browser caching, and more, without modifying your origin or writing any code.
* api-change:``lightsail``: This release adds support to enable access logging for buckets in the Lightsail object storage service.
* api-change:``nimble``: Amazon Nimble Studio adds support for users to stop and start streaming sessions.
* api-change:``ec2``: Support added for AMI sharing with organizations and organizational units in ModifyImageAttribute API
* api-change:``connect``: Amazon Connect Chat now supports real-time message streaming.
* api-change:``neptune``: Adds support for major version upgrades to ModifyDbCluster API
* api-change:``connect``: Amazon Connect Chat now supports real-time message streaming.
* api-change:``rekognition``: This release added new attributes to Rekognition Video GetCelebrityRecognition API operations.
* api-change:``networkmanager``: This release adds API support to aggregate resources, routes, and telemetry data across a Global Network.
* api-change:``rekognition``: This Amazon Rekognition Custom Labels release introduces the management of datasets with  projects
* api-change:``transcribe``: Transcribe and Transcribe Call Analytics now support automatic language identification along with custom vocabulary, vocabulary filter, custom language model and PII redaction.
* api-change:``application-insights``: Added Monitoring support for SQL Server Failover Cluster Instance. Additionally, added a new API to allow one-click monitoring of containers resources.


2.3.2
=====

* api-change:``eks``: EKS managed node groups now support BOTTLEROCKET_x86_64 and BOTTLEROCKET_ARM_64 AMI types.
* api-change:``autoscaling``: This release adds support for attribute-based instance type selection, a new EC2 Auto Scaling feature that lets customers express their instance requirements as a set of attributes, such as vCPU, memory, and storage.
* api-change:``sagemaker``: This release allows customers to describe one or more versioned model packages through BatchDescribeModelPackage, update project via UpdateProject, modify and read customer metadata properties using Create, Update and Describe ModelPackage and enables cross account registration of model packages.
* bugfix:Source: Fix invalid dependency specification in pyproject.toml (`#6513 <https://github.com/aws/aws-cli/pull/6513>`__).
* api-change:``ec2``: This release adds: attribute-based instance type selection for EC2 Fleet, Spot Fleet, a feature that lets customers express instance requirements as attributes like vCPU, memory, and storage; and Spot placement score, a feature that helps customers identify an optimal location to run Spot workloads.
* enhancement:Source: Remove unsupported aws_legacy_completer script from source (`#6515 <https://github.com/aws/aws-cli/pull/6515>`__).
* api-change:``ecs``: Amazon ECS now supports running Fargate tasks on Windows Operating Systems Families which includes Windows Server 2019 Core and Windows Server 2019 Full.
* api-change:``textract``: This release adds support for asynchronously analyzing invoice and receipt documents through two new APIs: StartExpenseAnalysis and GetExpenseAnalysis
* api-change:``gamelift``: Added support for Arm-based AWS Graviton2 instances, such as M6g, C6g, and R6g.
* api-change:``ssm-incidents``: Updating documentation, adding new field to ConflictException to indicate earliest retry timestamp for some operations, increase maximum length of nextToken fields
* api-change:``ec2``: Added new read-only DenyAllIGWTraffic network interface attribute. Added support for DL1 24xlarge instances powered by Habana Gaudi Accelerators for deep learning model training workloads
* api-change:``sagemaker``: This release adds support for RStudio on SageMaker.
* api-change:``connectparticipant``: This release adds a new boolean attribute - Connect Participant - to the CreateParticipantConnection API, which can be used to mark the participant as connected.


2.3.1
=====

* api-change:``auditmanager``: This release introduces a new feature for Audit Manager: Custom framework sharing. You can now share your custom frameworks with another AWS account, or replicate them into another AWS Region under your own account.
* api-change:``quicksight``: Added QSearchBar option for GenerateEmbedUrlForRegisteredUser ExperienceConfiguration to support Q search bar embedding
* api-change:``emr-containers``: This feature enables auto-generation of certificate  to secure the managed-endpoint and removes the need for customer provided certificate-arn during managed-endpoint setup.
* api-change:``auditmanager``: This release introduces character restrictions for ControlSet names. We updated regex patterns for the following attributes: ControlSet, CreateAssessmentFrameworkControlSet, and UpdateAssessmentFrameworkControlSet.
* api-change:``chime-sdk-identity``: The Amazon Chime SDK now supports push notifications through Amazon Pinpoint
* api-change:``rds``: This release adds support for Amazon RDS Custom, which is a new RDS management type that gives you full access to your database and operating system. For more information, see https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-custom.html
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now supports push notifications through Amazon Pinpoint
* api-change:``chime``: Chime VoiceConnector and VoiceConnectorGroup APIs will now return an ARN.
* api-change:``route53resolver``: New API for ResolverConfig, which allows autodefined rules for reverse DNS resolution to be disabled for a VPC
* api-change:``ec2``: This release adds support to create a VPN Connection that is not attached to a Gateway at the time of creation. Use this to create VPNs associated with Core Networks, or modify your VPN and attach a gateway using the modify API after creation.


2.3.0
=====

* api-change:``panorama``: General availability for AWS Panorama. AWS SDK for Panorama includes APIs to manage your devices and nodes, and deploy computer vision applications to the edge. For more information, see the AWS Panorama documentation at http://docs.aws.amazon.com/panorama
* api-change:``connect``: Released Amazon Connect hours of operation API for general availability (GA). This API also supports AWS CloudFormation. For more information, see Amazon Connect Resource Type Reference in the AWS CloudFormation User Guide.
* api-change:``mediapackage-vod``: MediaPackage passes through digital video broadcasting (DVB) subtitles into the output.
* feature:Serialization: rest-json serialization defaults aligned across AWS SDKs
* enhancement:Source: Absorb implementations of botocore and s3transfer libraries to improve building of CLI codebase (`#6494 <https://github.com/aws/aws-cli/pull/6494>`__).
* api-change:``securityhub``: Added support for cross-Region finding aggregation, which replicates findings from linked Regions to a single aggregation Region. Added operations to view, enable, update, and delete the finding aggregation.
* api-change:``directconnect``: This release adds 4 new APIS, which needs to be public able
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for specifying caption time delta in milliseconds and the ability to apply color range legalization to source content other than AVC video.
* api-change:``mediapackage``: When enabled, MediaPackage passes through digital video broadcasting (DVB) subtitles into the output.
* api-change:``appflow``: Feature to add support for  JSON-L format for S3 as a source.


2.2.47
======

* api-change:``glue``: Enable S3 event base crawler API.
* api-change:``dataexchange``: This release adds support for our public preview of AWS Data Exchange for Amazon Redshift. This enables data providers to list products including AWS Data Exchange datashares for Amazon Redshift, giving subscribers read-only access to provider data in Amazon Redshift.
* api-change:``efs``: Update efs command to latest version
* api-change:``quicksight``: AWS QuickSight Service  Features    - Add IP Restriction UI and public APIs support.
* api-change:``ivs``: Bug fix: remove unsupported maxResults and nextToken pagination parameters from ListTagsForResource
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK now allows developers to execute business logic on in-flight messages before they are delivered to members of a messaging channel with channel flows.


2.2.46
======

* api-change:``robomaker``: Adding support to GPU simulation jobs as well as non-ROS simulation jobs.
* api-change:``config``: Adding Config support for AWS::OpenSearch::Domain
* api-change:``autoscaling``: Amazon EC2 Auto Scaling now supports filtering describe Auto Scaling groups API using tags
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``workmail``: This release adds APIs for adding, removing and retrieving details of mail domains
* api-change:``ec2``: This release adds support for additional VPC Flow Logs delivery options to S3, such as Apache Parquet formatted files, Hourly partitions and Hive-compatible S3 prefixes
* api-change:``ec2``: EncryptionSupport for InstanceStorageInfo added to DescribeInstanceTypes API
* api-change:``cloudsearch``: Adds an additional validation exception for Amazon CloudSearch configuration APIs for better error handling.
* api-change:``ecs``: Documentation only update to address tickets.
* api-change:``sagemaker``: This release updates the provisioning artifact ID to an optional parameter in CreateProject API. The provisioning artifact ID defaults to the latest provisioning artifact ID of the product if you don't provide one.
* enhancement:``s3``: Update awscrt version to 0.12.4, which adds proxy support for the ``crt`` S3 transfer client
* api-change:``storagegateway``: Adding support for Audit Logs on NFS shares and Force Closing Files on SMB shares.
* api-change:``kinesisanalyticsv2``: Support for Apache Flink 1.13 in Kinesis Data Analytics. Changed the required status of some Update properties to better fit the corresponding Create properties.
* api-change:``mediatailor``: MediaTailor now supports ad prefetching.


2.2.45
======

* api-change:``kendra``: Amazon Kendra now supports indexing and querying documents in different languages.
* api-change:``ec2``: Documentation update for Amazon EC2.
* api-change:``sagemaker``: This release adds a new TrainingInputMode FastFile for SageMaker Training APIs.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``securityhub``: Added new resource details objects to ASFF, including resources for WAF rate-based rules, EC2 VPC endpoints, ECR repositories, EKS clusters, X-Ray encryption, and OpenSearch domains. Added additional details for CloudFront distributions, CodeBuild projects, ELB V2 load balancers, and S3 buckets.
* api-change:``chime``: This release enables customers to configure Chime MediaCapturePipeline via API.
* api-change:``mediaconvert``: AWS Elemental MediaConvert has added the ability to set account policies which control access restrictions for HTTP, HTTPS, and S3 content sources.
* api-change:``kendra``: Amazon Kendra now supports integration with AWS SSO
* api-change:``schemas``: Removing unused request/response objects.
* api-change:``medialive``: This release adds support for Transport Stream files as an input type to MediaLive encoders.
* api-change:``secretsmanager``: Documentation updates for Secrets Manager
* api-change:``fsx``: This release adds support for Lustre 2.12 to FSx for Lustre.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``amplifybackend``: Adding a new field 'AmplifyFeatureFlags' to the response of the GetBackend operation. It will return a stringified version of the cli.json file for the given Amplify project.
* api-change:``frauddetector``: New model type: Transaction Fraud Insights, which is optimized for online transaction fraud. Stored Events, which allows customers to send and store data directly within Amazon Fraud Detector. Batch Import, which allows customers to upload a CSV file of historic event data for processing and storage
* api-change:``grafana``: Initial release of the SDK for Amazon Managed Grafana API.
* api-change:``ec2``: This release removes a requirement for filters on SearchLocalGatewayRoutes operations.
* api-change:``firehose``: Allow support for Amazon Opensearch Service(successor to Amazon Elasticsearch Service) as a Kinesis Data Firehose delivery destination.
* api-change:``backup``: Launch of AWS Backup Vault Lock, which protects your backups from malicious and accidental actions, works with existing backup policies, and helps you meet compliance requirements.


2.2.44
======

* api-change:``synthetics``: CloudWatch Synthetics now enables customers to choose a customer managed AWS KMS key or an Amazon S3-managed key instead of an AWS managed key (default) for the encryption of artifacts that the canary stores in Amazon S3. CloudWatch Synthetics also supports artifact S3 location updation now.
* api-change:``backup``: AWS Backup Audit Manager framework report.
* api-change:``ec2``: Released Capacity Reservation Fleet, a feature of Amazon EC2 Capacity Reservations, which provides a way to manage reserved capacity across instance types. For more information: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/cr-fleets.html
* api-change:``ssm``: When "AutoApprovable" is true for a Change Template, then specifying --auto-approve (boolean) in Start-Change-Request-Execution will create a change request that bypasses approver review. (except for change calendar restrictions)
* api-change:``glue``: This release adds tag as an input of CreateConnection
* api-change:``codebuild``: CodeBuild now allows you to select how batch build statuses are sent to the source provider for a project.
* api-change:``application-autoscaling``: With this release, Application Auto Scaling adds support for Amazon Neptune. Customers can now automatically add or remove Read Replicas of their Neptune clusters to keep the average CPU Utilization at the target value specified by the customers.
* api-change:``location``: Add support for PositionFiltering.
* api-change:``kms``: Added SDK examples for ConnectCustomKeyStore, CreateCustomKeyStore, CreateKey, DeleteCustomKeyStore, DescribeCustomKeyStores, DisconnectCustomKeyStore, GenerateDataKeyPair, GenerateDataKeyPairWithoutPlaintext, GetPublicKey, ReplicateKey, Sign, UpdateCustomKeyStore and Verify APIs
* api-change:``efs``: Update efs command to latest version
* api-change:``workmail``: This release allows customers to change their inbound DMARC settings in Amazon WorkMail.
* enhancement:Source: Automatically build auto-complete index as part of building the wheel (`#6448 <https://github.com/aws/aws-cli/pull/6448>`__).
* api-change:``apprunner``: This release contains several minor bug fixes.


2.2.43
======

* api-change:``macie2``: Amazon S3 bucket metadata now indicates whether an error or a bucket's permissions settings prevented Amazon Macie from retrieving data about the bucket or the bucket's objects.
* api-change:``cloudcontrol``: Initial release of the SDK for AWS Cloud Control API
* api-change:``account``: This release of the Account Management API enables customers to manage the alternate contacts for their AWS accounts. For more information, see https://docs.aws.amazon.com/accounts/latest/reference/accounts-welcome.html
* api-change:``lambda``: Adds support for Lambda functions powered by AWS Graviton2 processors. Customers can now select the CPU architecture for their functions.
* api-change:``dataexchange``: This release enables subscribers to set up automatic exports of newly published revisions using the new EventAction API.
* api-change:``amp``: This release adds alert manager and rule group namespace APIs
* api-change:``sesv2``: This release includes the ability to use 2048 bits RSA key pairs for DKIM in SES, either with Easy DKIM or Bring Your Own DKIM.
* api-change:``workspaces``: Added CreateUpdatedWorkspaceImage API to update WorkSpace images with latest software and drivers. Updated DescribeWorkspaceImages API to display if there are updates available for WorkSpace images.
* api-change:``network-firewall``: This release adds support for strict ordering for stateful rule groups. Using strict ordering, stateful rules are evaluated in the exact order in which you provide them.
* api-change:``workmail``: This release adds support for mobile device access overrides management in Amazon WorkMail.


2.2.42
======

* api-change:``wisdom``: Released Amazon Connect Wisdom, a feature of Amazon Connect, which provides real-time recommendations and search functionality in general availability (GA).  For more information, see https://docs.aws.amazon.com/wisdom/latest/APIReference/Welcome.html.
* api-change:``ec2``: DescribeInstances now returns Platform Details, Usage Operation, and Usage Operation Update Time.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``imagebuilder``: Fix description for AmiDistributionConfiguration Name property, which actually refers to the output AMI name. Also updated for consistent terminology to use "base" image, and another update to fix description text.
* enhancement:Source: Migrate source code to be buildable via `PEP 517 <https://www.python.org/dev/peps/pep-0517/>`__
* api-change:``connect``: This release updates a set of APIs: CreateIntegrationAssociation, ListIntegrationAssociations, CreateUseCase, and StartOutboundVoiceContact. You can use it to create integrations with Amazon Pinpoint for the Amazon Connect Campaigns use case, Amazon Connect Voice ID, and Amazon Connect Wisdom.
* api-change:``voice-id``: Released the Amazon Voice ID SDK, for usage with the Amazon Connect Voice ID feature released for Amazon Connect.
* api-change:``pinpoint``: Added support for journey with contact center activity
* api-change:``transfer``: Added changes for managed workflows feature APIs.
* api-change:``license-manager``: AWS License Manager now allows customers to get the LicenseArn in the Checkout API Response.
* api-change:``appintegrations``: The Amazon AppIntegrations service enables you to configure and reuse connections to external applications.


2.2.41
======

* api-change:``iam``: Added changes to OIDC API about not using port numbers in the URL.
* api-change:``imagebuilder``: This feature adds support for specifying GP3 volume throughput and configuring instance metadata options for instances launched by EC2 Image Builder.
* api-change:``ssm``: Added cutoff behavior support for preventing new task invocations from starting when the maintenance window cutoff time is reached.
* api-change:``mediatailor``: This release adds support to configure logs for playback configuration.
* api-change:``license-manager``: AWS License Manager now allows customers to change their Windows Server or SQL license types from Bring-Your-Own-License (BYOL) to License Included or vice-versa (using the customer's media).
* api-change:``mediaconvert``: This release adds style and positioning support for caption or subtitle burn-in from rich text sources such as TTML. This release also introduces configurable image-based trick play track generation.
* api-change:``mediapackage-vod``: MediaPackage VOD will now return the current processing statuses of an asset's endpoints. The status can be QUEUED, PROCESSING, PLAYABLE, or FAILED.
* api-change:``wafv2``: Added the regex match rule statement, for matching web requests against a single regular expression.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``appsync``: Documented the new OpenSearchServiceDataSourceConfig data type. Added deprecation notes to the ElasticsearchDataSourceConfig data type.


2.2.40
======

* api-change:``es``: This release adds an optional parameter in the ListDomainNames API to filter domains based on the engine type (OpenSearch/Elasticsearch).
* api-change:``comprehend``: Amazon Comprehend now supports versioning of custom models, improved training with ONE_DOC_PER_FILE text documents for custom entity recognition, ability to provide specific test sets during training, and live migration to new model endpoints.
* api-change:``ecr``: This release adds additional support for repository replication
* api-change:``dms``: Optional flag force-planned-failover added to reboot-replication-instance API call. This flag can be used to test a planned failover scenario used during some maintenance operations.
* api-change:``iot``: This release adds support for verifying, viewing and filtering AWS IoT Device Defender detect violations with four verification states.
* api-change:``opensearch``: This release adds an optional parameter in the ListDomainNames API to filter domains based on the engine type (OpenSearch/Elasticsearch).
* api-change:``ec2``: This update adds support for downloading configuration templates using new APIs (GetVpnConnectionDeviceTypes and GetVpnConnectionDeviceSampleConfiguration) and Internet Key Exchange version 2 (IKEv2) parameters for many popular CGW devices.


2.2.39
======

* api-change:``pinpoint``: This SDK release adds a new feature for Pinpoint campaigns, in-app messaging.
* api-change:``robomaker``: Adding support to create container based Robot and Simulation applications by introducing an environment field
* api-change:``kafkaconnect``: This is the initial SDK release for Amazon Managed Streaming for Apache Kafka Connect (MSK Connect).
* api-change:``macie2``: This release adds support for specifying which managed data identifiers are used by a classification job, and retrieving a list of managed data identifiers that are available.
* api-change:``sagemaker``: Add API for users to retry a failed pipeline execution or resume a stopped one.
* api-change:``s3``: Add support for access point arn filtering in S3 CW Request Metrics
* api-change:``transcribe``: This release adds support for subtitling with Amazon Transcribe batch jobs.


2.2.38
======

* api-change:``chime``: Adds support for SipHeaders parameter for CreateSipMediaApplicationCall.
* api-change:``rds``: This release adds support for providing a custom timeout value for finding a scaling point during autoscaling in Aurora Serverless v1.
* api-change:``quicksight``: Add new data source type for Amazon OpenSearch (successor to Amazon ElasticSearch).
* api-change:``comprehend``: Amazon Comprehend now allows you to train and run PDF and Word documents for custom entity recognition. With PDF and Word formats, you can extract information from documents containing headers, lists and tables.
* api-change:``transcribe``: This release adds an API option for startTranscriptionJob and startMedicalTranscriptionJob that allows the user to specify encryption context key value pairs for batch jobs.
* api-change:``iot``: AWS IoT Rules Engine adds OpenSearch action. The OpenSearch rule action lets you stream data from IoT sensors and applications to Amazon OpenSearch Service which is a successor to Amazon Elasticsearch Service.
* api-change:``wafv2``: This release adds support for including rate based rules in a rule group.
* api-change:``sagemaker``: This release adds support for "Project Search"
* api-change:``ec2``: This release adds support for vt1 3xlarge, 6xlarge and 24xlarge instances powered by Xilinx Alveo U30 Media Accelerators for video transcoding workloads
* api-change:``ec2``: Adds support for T3 instances on Amazon EC2 Dedicated Hosts.
* api-change:``ecr``: This release updates terminology around KMS keys.
* api-change:``sagemaker``: This release adds support for "Lifecycle Configurations" to SageMaker Studio
* api-change:``cloudformation``: Doc only update for CloudFormation that fixes several customer-reported issues.


2.2.37
======

* api-change:``kafka``: Amazon MSK has added a new API that allows you to update the encrypting and authentication settings for an existing cluster.
* api-change:``lookoutequipment``: Added OffCondition parameter to CreateModel API
* api-change:``codeguru-reviewer``: The Amazon CodeGuru Reviewer API now includes the RuleMetadata data object and a Severity attribute on a RecommendationSummary object. A RuleMetadata object contains information about a rule that generates a recommendation. Severity indicates how severe the issue associated with a recommendation is.
* api-change:``emr``: Update emr command to latest version
* api-change:``opensearch``: Updated Configuration APIs for Amazon OpenSearch Service (successor to Amazon Elasticsearch Service)
* api-change:``ram``: A minor text-only update that fixes several customer issues.


2.2.36
======

* api-change:``outposts``: This release adds a new API CreateOrder.
* api-change:``ssm-contacts``: Added SDK examples for SSM-Contacts.
* api-change:``mediapackage``: SPEKE v2 support for live CMAF packaging type. SPEKE v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, it supports live DASH currently.
* api-change:``chime-sdk-identity``: Documentation updates for Chime
* api-change:``frauddetector``: Enhanced GetEventPrediction API response to include risk scores from imported SageMaker models
* api-change:``forecast``: Predictor creation now supports selecting an accuracy metric to optimize in AutoML and hyperparameter optimization. This release adds additional accuracy metrics for predictors - AverageWeightedQuantileLoss, MAPE and MASE.
* api-change:``chime-sdk-messaging``: Documentation updates for Chime
* api-change:``codeguru-reviewer``: Added support for CodeInconsistencies detectors
* api-change:``xray``: Updated references to AWS KMS keys and customer managed keys to reflect current terminology.
* api-change:``amp``: This release adds tagging support for Amazon Managed Service for Prometheus workspace.
* api-change:``eks``: Adding RegisterCluster and DeregisterCluster operations, to support connecting external clusters to EKS.
* api-change:``elasticache``: Doc only update for ElastiCache


2.2.35
======

* api-change:``transfer``: AWS Transfer Family introduces Managed Workflows for creating, executing, monitoring, and standardizing post file transfer processing
* api-change:``fsx``: Announcing Amazon FSx for NetApp ONTAP, a new service that provides fully managed shared storage in the AWS Cloud with the data access and management capabilities of ONTAP.
* api-change:``cloudtrail``: Documentation updates for CloudTrail
* enhancement:emr-containers: Adds addition aws partition support for update-role-trust-policy
* api-change:``config``: Documentation updates for config
* api-change:``servicecatalog-appregistry``: Introduction of GetAssociatedResource API and GetApplication response extension for Resource Groups support.
* api-change:``quicksight``: This release adds support for referencing parent datasets as sources in a child dataset.
* api-change:``efs``: Update efs command to latest version
* api-change:``acm-pca``: Private Certificate Authority Service now allows customers to enable an online certificate status protocol (OCSP) responder service on their private certificate authorities. Customers can also optionally configure a custom CNAME for their OCSP responder.
* api-change:``ec2``: Added LaunchTemplate support for the IMDS IPv6 endpoint
* api-change:``accessanalyzer``: Updates service API, documentation, and paginators to support multi-region access points from Amazon S3.
* api-change:``ebs``: Documentation updates for Amazon EBS direct APIs.
* api-change:``mediatailor``: This release adds support for wall clock programs in LINEAR channels.
* api-change:``schemas``: This update include the support for Schema Discoverer to discover the events sent to the bus from another account. The feature will be enabled by default when discoverer is created or updated but can also be opt-in or opt-out  by specifying the value for crossAccount.
* api-change:``securityhub``: New ASFF Resources: AwsAutoScalingLaunchConfiguration, AwsEc2VpnConnection, AwsEcrContainerImage. Added KeyRotationStatus to AwsKmsKey. Added AccessControlList, BucketLoggingConfiguration,BucketNotificationConfiguration and BucketNotificationConfiguration to AwsS3Bucket.
* api-change:``s3control``: S3 Multi-Region Access Points provide a single global endpoint to access a data set that spans multiple S3 buckets in different AWS Regions.
* api-change:``lex-models``: Lex now supports Korean (ko-KR) locale.
* enhancement:``s3``: Add support for multi-region access points.


2.2.34
======

* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer
* api-change:``codebuild``: Documentation updates for CodeBuild
* api-change:``emr``: Update emr command to latest version
* api-change:``cloudformation``: AWS CloudFormation allows you to iteratively develop your applications when failures are encountered without rolling back successfully provisioned resources. By specifying stack failure options, you can troubleshoot resources in a CREATE_FAILED or UPDATE_FAILED status.
* api-change:``sqs``: Amazon SQS adds a new queue attribute, RedriveAllowPolicy, which includes the dead-letter queue redrive permission parameters. It defines which source queues can specify dead-letter queues as a JSON object.
* api-change:``firehose``: This release adds the Dynamic Partitioning feature to Kinesis Data Firehose service for S3 destinations.
* api-change:``s3``: Documentation updates for Amazon S3.
* api-change:``polly``: Amazon Polly adds new South African English voice - Ayanda. Ayanda is available as Neural voice only.
* api-change:``kms``: This release has changes to KMS nomenclature to remove the word master from both the "Customer master key" and "CMK" abbreviation and replace those naming conventions with "KMS key".
* api-change:``memorydb``: Documentation updates for MemoryDB
* api-change:``iot``: Added Create/Update/Delete/Describe/List APIs for a new IoT resource named FleetMetric. Added a new Fleet Indexing query API named GetBucketsAggregation. Added a new field named DisconnectedReason in Fleet Indexing query response. Updated their related documentations.
* api-change:``ec2``: This release adds the BootMode flag to the ImportImage API and showing the detected BootMode of an ImportImage task.


2.2.33
======

* api-change:``compute-optimizer``: Adds support for 1) the AWS Graviton (AWS_ARM64) recommendation preference for Amazon EC2 instance and Auto Scaling group recommendations, and 2) the ability to get the enrollment statuses for all member accounts of an organization.
* api-change:``transcribe``: This release adds support for batch transcription in six new languages - Afrikaans, Danish, Mandarin Chinese (Taiwan), New Zealand English, South African English, and Thai.
* api-change:``events``: AWS CWEvents adds an enum of EXTERNAL for EcsParameters LaunchType for PutTargets API
* api-change:``ec2``: Support added for resizing VPC prefix lists
* api-change:``ec2``: Support added for IMDS IPv6 endpoint
* api-change:``rekognition``: This release added new attributes to Rekognition RecognizeCelebities and GetCelebrityInfo API operations.
* api-change:``fms``: AWS Firewall Manager now supports triggering resource cleanup workflow when account or resource goes out of policy scope for AWS WAF, Security group, AWS Network Firewall, and Amazon Route 53 Resolver DNS Firewall policies.
* enhancement:``logs tail``: Add filter by streams for ``logs tail`` command. Fixes aws/aws-cli`#5560 <https://github.com/aws/aws-cli/issues/5560>`__
* api-change:``datasync``: Added include filters to CreateTask and UpdateTask, and added exclude filters to StartTaskExecution, giving customers more granular control over how DataSync transfers files, folders, and objects.


2.2.32
======

* api-change:``iot-data``: Updated Publish with support for new Retain flag and added two new API operations: GetRetainedMessage, ListRetainedMessages.
* api-change:``eks``: Adds support for EKS add-ons "preserve" flag, which allows customers to maintain software on their EKS clusters after removing it from EKS add-ons management.
* api-change:``ec2``: encryptionInTransitSupported added to DescribeInstanceTypes API
* api-change:``robomaker``: Documentation updates for RoboMaker
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added MBAFF encoding support for AVC video and the ability to pass encryption context from the job settings to S3.
* api-change:``dlm``: Added AMI deprecation support for Amazon Data Lifecycle Manager EBS-backed AMI policies.
* api-change:``iotsitewise``: Documentation updates for AWS IoT SiteWise
* api-change:``polly``: Amazon Polly adds new New Zealand English voice - Aria. Aria is available as Neural voice only.
* api-change:``frauddetector``: Updated an element of the DescribeModelVersion API response (LogitMetrics -> logOddsMetrics) for clarity. Added new exceptions to several APIs to protect against unlikely scenarios.
* api-change:``glue``: Add support for Custom Blueprints
* api-change:``apigateway``: Adding some of the pending releases (1) Adding WAF Filter to GatewayResponseType enum (2) Ensuring consistent error model for all operations (3) Add missing BRE to GetVpcLink operation
* api-change:``dms``: Amazon AWS DMS service now support Redis target endpoint migration. Now S3 endpoint setting is capable to setup features which are used to be configurable only in extract connection attributes.
* api-change:``backup``: AWS Backup - Features: Evaluate your backup activity and generate audit reports.
* api-change:``ssm``: Updated Parameter Store property for logging improvements.
* api-change:``comprehend``: Add tagging support for Comprehend async inference job.
* api-change:``transcribe``: This release adds support for feature tagging with Amazon Transcribe batch jobs.


2.2.31
======

* api-change:``ec2``: The ImportImage API now supports the ability to create AMIs with AWS-managed licenses for Microsoft SQL Server for both Windows and Linux.
* api-change:``route53resolver``: Documentation updates for Route 53 Resolver
* api-change:``memorydb``: AWS MemoryDB  SDK now supports all APIs for newly launched MemoryDB service.
* api-change:``application-autoscaling``: This release extends Application Auto Scaling support for replication group of Amazon ElastiCache Redis clusters. Auto Scaling monitors and automatically expands node group count and number of replicas per node group when a critical usage threshold is met or according to customer-defined schedule.
* api-change:``route53``: Documentation updates for route53
* api-change:``codebuild``: CodeBuild now allows you to make the build results for your build projects available to the public without requiring access to an AWS account.
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``sagemaker``: Amazon SageMaker now supports Asynchronous Inference endpoints. Adds PlatformIdentifier field that allows Notebook Instance creation with different platform selections. Increases the maximum number of containers in multi-container endpoints to 15. Adds more instance types to InstanceType field.
* api-change:``appflow``: This release adds support for SAPOData connector and extends Veeva connector for document extraction.


2.2.30
======

* api-change:``logs``: Documentation-only update for CloudWatch Logs
* api-change:``codebuild``: CodeBuild now allows you to select how batch build statuses are sent to the source provider for a project.
* api-change:``emr``: Update emr command to latest version
* api-change:``config``: Update ResourceType enum with values for Backup Plan, Selection, Vault, RecoveryPoint; ECS Cluster, Service, TaskDefinition; EFS AccessPoint, FileSystem; EKS Cluster; ECR Repository resources
* api-change:``elasticache``: This release adds ReplicationGroupCreateTime field to ReplicationGroup which indicates the UTC time when ElastiCache ReplicationGroup is created
* api-change:``license-manager``: AWS License Manager now allows end users to call CheckoutLicense API using new CheckoutType PERPETUAL. Perpetual checkouts allow sellers to check out a quantity of entitlements to be drawn down for consumption.
* api-change:``quicksight``: Documentation updates for QuickSight.
* api-change:``ce``: This release is a new feature for Cost Categories: Split charge rules. Split charge rules enable you to allocate shared costs between your cost category values.
* api-change:``clouddirectory``: Documentation updates for clouddirectory
* api-change:``ec2``: This release adds support for EC2 ED25519 key pairs for authentication
* api-change:``customer-profiles``: This release introduces Standard Profile Objects, namely Asset and Case which contain values populated by data from third party systems and belong to a specific profile. This release adds an optional parameter, ObjectFilter to the ListProfileObjects API in order to search for these Standard Objects.
* api-change:``iotsitewise``: AWS IoT SiteWise added query window for the interpolation interval. AWS IoT SiteWise computes each interpolated value by using data points from the timestamp of each interval minus the window to the timestamp of each interval plus the window.
* api-change:``cloud9``: Added DryRun parameter to CreateEnvironmentEC2 API. Added ManagedCredentialsActions parameter to UpdateEnvironment API
* api-change:``ds``: This release adds support for describing client authentication settings.
* api-change:``s3``: Documentation updates for Amazon S3


2.2.29
======

* api-change:``codebuild``: CodeBuild now allows you to make the build results for your build projects available to the public without requiring access to an AWS account.
* api-change:``ecs``: Documentation updates for ECS.
* api-change:``snow-device-management``: AWS Snow Family customers can remotely monitor and operate their connected AWS Snowcone devices.
* api-change:``nimble``: Add new attribute 'ownedBy' in Streaming Session APIs. 'ownedBy' represents the AWS SSO Identity Store User ID of the owner of the Streaming Session resource.
* api-change:``lambda``: Lambda Python 3.9 runtime launch
* api-change:``ebs``: Documentation updates for Amazon EBS direct APIs.
* api-change:``databrew``: This SDK release adds support for the output of a recipe job results to Tableau Hyper format.
* api-change:``apigatewayv2``: Adding support for ACM imported or private CA certificates for mTLS enabled domain names
* api-change:``route53``: Documentation updates for route53
* api-change:``apigateway``: Adding support for ACM imported or private CA certificates for mTLS enabled domain names
* api-change:``sagemaker``: Amazon SageMaker Autopilot adds new metrics for all candidate models generated by Autopilot experiments.


2.2.28
======

* api-change:``chime``: Add support for "auto" in Region field of StartMeetingTranscription API request.
* api-change:``chime-sdk-messaging``: The Amazon Chime SDK Messaging APIs allow software developers to send and receive messages in custom messaging applications.
* api-change:``chime-sdk-identity``: The Amazon Chime SDK Identity APIs allow software developers to create and manage unique instances of their messaging applications.
* api-change:``athena``: Documentation updates for Athena.
* api-change:``lightsail``: This release adds support to track when a bucket access key was last used.
* api-change:``connect``: This release adds support for agent status and hours of operation. For details, see the Release Notes in the Amazon Connect Administrator Guide.
* api-change:``ssm``: Documentation updates for AWS Systems Manager.
* api-change:``synthetics``: Documentation updates for Visual Monitoring feature and other doc ticket fixes.
* api-change:``rekognition``: This release adds support for four new types of segments (opening credits, content segments, slates, and studio logos), improved accuracy for credits and shot detection and new filters to control black frame detection.
* api-change:``wafv2``: This release adds APIs to support versioning feature of AWS WAF Managed rule groups


2.2.27
======

* api-change:``events``: Update events command to latest version
* api-change:``rds``: This release adds AutomaticRestartTime to the DescribeDBInstances and DescribeDBClusters operations. AutomaticRestartTime indicates the time when a stopped DB instance or DB cluster is restarted automatically.
* api-change:``autoscaling``: EC2 Auto Scaling adds configuration checks and Launch Template validation to Instance Refresh.
* api-change:``imagebuilder``: Updated list actions to include a list of valid filters that can be used in the request.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``ssm-incidents``: Documentation updates for Incident Manager.
* api-change:``transcribe``: This release adds support for call analytics (batch) within Amazon Transcribe.


2.2.26
======

* api-change:``secretsmanager``: Add support for KmsKeyIds in the ListSecretVersionIds API response
* api-change:``greengrassv2``: This release adds support for component system resource limits and idempotent Create operations. You can now specify the maximum amount of CPU and memory resources that each component can use.
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``redshift``: API support for Redshift Data Sharing feature.
* bugfix:``eks``: Fixes `#6308 <https://github.com/aws/aws-cli/issues/6308>`__ version mismatch running eks get-login without eks update-config
* api-change:``glue``: Add ConcurrentModificationException to create-table, delete-table, create-database, update-database, delete-database
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added control over the passthrough of XDS captions metadata to outputs.
* api-change:``sagemaker``: API changes with respect to Lambda steps in model building pipelines. Adds several waiters to async Sagemaker Image APIs. Add more instance types to AppInstanceType field
* api-change:``ssm-contacts``: Added new attribute in AcceptCode API. AcceptCodeValidation takes in two values - ENFORCE, IGNORE. ENFORCE forces validation of accept code and IGNORE ignores it which is also the default behavior; Corrected TagKeyList length from 200 to 50
* api-change:``appsync``: AWS AppSync now supports a new authorization mode allowing you to define your own authorization logic using an AWS Lambda function.
* api-change:``proton``: Docs only add idempotent create apis
* api-change:``iotsitewise``: My AWS Service (placeholder) - This release introduces custom Intervals and offset for tumbling window in metric for AWS IoT SiteWise.


2.2.25
======

* bugfix:``eks``: Fixes `#6308 <https://github.com/aws/aws-cli/issues/6308>`__ version mismatch running eks get-login without eks update-config


2.2.24
======

* api-change:``iotsitewise``: Added support for AWS IoT SiteWise Edge. You can now create an AWS IoT SiteWise gateway that runs on AWS IoT Greengrass V2. With the gateway,  you can collect local server and equipment data, process the data, and export the selected data from the edge to the AWS Cloud.
* enhancement:eks: Updated Kubernetes client authentication API version
* api-change:``ec2``: This release adds support for G4ad xlarge and 2xlarge instances powered by AMD Radeon Pro V520 GPUs and AMD 2nd Generation EPYC processors
* api-change:``chime``: Adds support for live transcription of meetings with Amazon Transcribe and Amazon Transcribe Medical.  The new APIs, StartMeetingTranscription and StopMeetingTranscription, control the generation of user-attributed transcriptions sent to meeting clients via Amazon Chime SDK data messages.
* api-change:``cloudformation``: SDK update to support Importing existing Stacks to new/existing Self Managed StackSet - Stack Import feature.
* api-change:``sso-admin``: Documentation updates for arn:aws:trebuchet:::service:v1:03a2216d-1cda-4696-9ece-1387cb6f6952
* api-change:``iot``: Increase maximum credential duration of role alias to 12 hours.
* api-change:``savingsplans``: Documentation update for valid Savings Plans offering ID pattern


2.2.23
======

* api-change:``quicksight``: Add support to use row-level security with tags when embedding dashboards for users not provisioned in QuickSight
* api-change:``route53``: This release adds support for the RECOVERY_CONTROL health check type to be used in conjunction with Route53 Application Recovery Controller.
* api-change:``route53-recovery-cluster``: Amazon Route 53 Application Recovery Controller's routing control - Routing Control Data Plane APIs help you update the state (On/Off) of the routing controls to reroute traffic across application replicas in a 100% available manner.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``s3control``: S3 Access Point aliases can be used anywhere you use S3 bucket names to access data in S3
* api-change:``route53-recovery-control-config``: Amazon Route 53 Application Recovery Controller's routing control - Routing Control Configuration APIs help you create and delete clusters, control panels, routing controls and safety rules. State changes (On/Off) of routing controls are not part of configuration APIs.
* api-change:``proton``: Documentation-only update links
* api-change:``imagebuilder``: Update to documentation to reapply missing change to SSM uninstall switch default value and improve description.
* api-change:``redshift-data``: Added structures to support new Data API operation BatchExecuteStatement, used to execute multiple SQL statements within a single transaction.
* api-change:``identitystore``: Documentation updates for SSO API Ref.
* api-change:``route53-recovery-readiness``: Amazon Route 53 Application Recovery Controller's readiness check capability continually monitors resource quotas, capacity, and network routing policies to ensure that the recovery environment is scaled and configured to take over when needed.
* api-change:``shield``: Change name of DDoS Response Team (DRT) to Shield Response Team (SRT)
* api-change:``s3outposts``: Add on-premise access type support for endpoints
* api-change:``iotanalytics``: IoT Analytics now supports creating a dataset resource with IoT SiteWise MultiLayerStorage data stores, enabling customers to query industrial data within the service. This release includes adding JOIN functionality for customers to query multiple data sources in a dataset.
* api-change:``batch``: Add support for ListJob filters
* api-change:``securityhub``: Added product name, company name, and Region fields for security findings. Added details objects for RDS event subscriptions and AWS ECS services. Added fields to the details for AWS Elasticsearch domains.
* enhancement:IMDS: Add support for configuring IMDS endpoint for region resolution via ``ec2_metadata_service_endpoint`` config option and ``AWS_EC2_METADATA_SERVICE_ENDPOINT`` environment variable.
* api-change:``textract``: Adds support for AnalyzeExpense, a new API to extract relevant data such as contact information, items purchased, and vendor name, from almost any invoice or receipt without the need for any templates or configuration.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``synthetics``: CloudWatch Synthetics now supports visual testing in its canaries.
* api-change:``iotwireless``: Add SidewalkManufacturingSn as an identifier to allow Customer to query WirelessDevice, in the response, AmazonId is added in the case that Sidewalk device is return.


2.2.22
======

* api-change:``emr``: Update emr command to latest version
* api-change:``proton``: Documentation updates for AWS Proton
* api-change:``ec2``: This release allows customers to assign prefixes to their elastic network interface and to reserve IP blocks in their subnet CIDRs. These reserved blocks can be used to assign prefixes to elastic network interfaces or be excluded from auto-assignment.
* api-change:``medialive``: MediaLive now supports passing through style data on WebVTT caption outputs.
* api-change:``databrew``: This SDK release adds two new features: 1) Output to Native JDBC destinations and 2) Adding configurations to profile jobs
* api-change:``codebuild``: AWS CodeBuild now allows you to set the access permissions for build artifacts, project artifacts, and log files that are uploaded to an Amazon S3 bucket that is owned by another account.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``lambda``: New ResourceConflictException error code for PutFunctionEventInvokeConfig, UpdateFunctionEventInvokeConfig, and DeleteFunctionEventInvokeConfig operations.
* api-change:``s3control``: Documentation updates for Amazon S3-control
* api-change:``personalize``: My AWS Service (placeholder) - Making minProvisionedTPS an optional parameter when creating a campaign. If not provided, it defaults to 1.
* api-change:``rds``: Adds the OriginalSnapshotCreateTime field to the DBSnapshot response object. This field timestamps the underlying data of a snapshot and doesn't change when the snapshot is copied.
* api-change:``kendra``: Amazon Kendra now provides a data source connector for Amazon WorkDocs. For more information, see https://docs.aws.amazon.com/kendra/latest/dg/data-source-workdocs.html
* api-change:``qldb``: Amazon QLDB now supports ledgers encrypted with customer managed KMS keys. Changes in CreateLedger, UpdateLedger and DescribeLedger APIs to support the changes.
* api-change:``elbv2``: Update elbv2 command to latest version


2.2.21
======

* api-change:``ec2``: Added idempotency to the CreateVolume API using the ClientToken request parameter
* api-change:``health``: In the Health API, the maximum number of entities for the EventFilter and EntityFilter data types has changed from 100 to 99. This change is related to an internal optimization of the AWS Health service.
* api-change:``chime``: This SDK release adds Account Status as one of the attributes in Account API response
* api-change:``imagebuilder``: Documentation updates for reversal of default value for additional instance configuration SSM switch, plus improved descriptions for semantic versioning.
* api-change:``emr-containers``: Updated DescribeManagedEndpoint and ListManagedEndpoints to return failureReason and stateDetails in API response.
* api-change:``location``: Add five new API operations: UpdateGeofenceCollection, UpdateMap, UpdatePlaceIndex, UpdateRouteCalculator, UpdateTracker.
* api-change:``auditmanager``: This release relaxes the S3 URL character restrictions in AWS Audit Manager. Regex patterns have been updated for the following attributes: s3RelativePath, destination, and s3ResourcePath. 'AWS' terms have also been replaced with entities to align with China Rebrand documentation efforts.
* api-change:``directconnect``: Documentation updates for directconnect
* api-change:``robomaker``: This release allows customers to create a new version of WorldTemplates with support for Doors.
* api-change:``compute-optimizer``: Documentation updates for Compute Optimizer
* api-change:``appintegrations``: Documentation update for AppIntegrations Service


2.2.20
======

* api-change:``glue``: Add support for Event Driven Workflows
* api-change:``iotsitewise``: Update the default endpoint for the APIs used to manage asset models, assets, gateways, tags, and account configurations. If you have firewalls with strict egress rules, configure the rules to grant you access to api.iotsitewise.[region].amazonaws.com or api.iotsitewise.[cn-region].amazonaws.com.cn.
* api-change:``healthlake``: General availability for Amazon HealthLake. StartFHIRImportJob and StartFHIRExportJob APIs now require AWS KMS parameter. For more information, see the Amazon HealthLake Documentation https://docs.aws.amazon.com/healthlake/index.html.
* api-change:``ec2``: This feature enables customers  to specify weekly recurring time window(s) for scheduled events that reboot, stop or terminate EC2 instances.
* api-change:``dms``: Release of feature needed for ECA-Endpoint settings. This allows customer to delete a field in endpoint settings by using --exact-settings flag in modify-endpoint api. This also displays default values for certain required fields of endpoint settings in describe-endpoint-settings api.
* api-change:``acm``: Added support for RSA 3072 SSL certificate import
* api-change:``wellarchitected``: This update provides support for Well-Architected API users to mark answer choices as not applicable.
* api-change:``ecs``: Documentation updates for support of awsvpc mode on Windows.
* api-change:``lex-models``: Lex now supports the en-IN locale
* api-change:``cognito-idp``: Documentation updates for cognito-idp
* api-change:``lightsail``: This release adds support for the Amazon Lightsail object storage service, which allows you to create buckets and store objects.


2.2.19
======

* api-change:``kendra``: Amazon Kendra now supports Principal Store
* api-change:``directconnect``: This release adds a new filed named awsLogicalDeviceId that it displays the AWS Direct Connect endpoint which terminates a physical connection's BGP Sessions.
* api-change:``pricing``: Documentation updates for api.pricing
* api-change:``mediaconvert``: MediaConvert now supports color, style and position information passthrough from 608 and Teletext to SRT and WebVTT subtitles. MediaConvert now also supports Automatic QVBR quality levels for QVBR RateControlMode.
* api-change:``redshift``: Release new APIs to support new Redshift feature - Authentication Profile
* api-change:``sagemaker``: Releasing new APIs related to Tuning steps in model building pipelines.
* api-change:``eks``: Documentation updates for Wesley to support the parallel node upgrade feature.
* api-change:``amplifybackend``: Added Sign in with Apple OAuth provider.
* api-change:``lex-models``: Customers can now migrate bots built with Lex V1 APIs to V2 APIs. This release adds APIs to initiate and manage the migration of a bot.
* api-change:``frauddetector``: This release adds support for ML Explainability to display model variable importance value in Amazon Fraud Detector.
* api-change:``ssm``: Changes to OpsCenter APIs to support a new feature, operational insights.


2.2.18
======

* api-change:``ssm-contacts``: Updated description for CreateContactChannel contactId.
* api-change:``chime``: Releasing new APIs for AWS Chime MediaCapturePipeline
* api-change:``mediatailor``: Add ListAlerts for Channel, Program, Source Location, and VOD Source to return alerts for resources.
* api-change:``iotsitewise``: This release add storage configuration APIs for AWS IoT SiteWise.
* api-change:``mq``: adds support for modifying the maintenance window for brokers.
* api-change:``outposts``: Added property filters for listOutposts
* api-change:``storagegateway``: Adding support for oplocks for SMB file shares,  S3 Access Point and S3 Private Link for all file shares and IP address support for file system associations
* api-change:``ec2``: This release adds resource ids and tagging support for VPC security group rules.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``cloudfront``: Amazon CloudFront now provides two new APIs, ListConflictingAliases and AssociateAlias, that help locate and move Alternate Domain Names (CNAMEs) if you encounter the CNAMEAlreadyExists error code.
* api-change:``fms``: AWS Firewall Manager now supports route table monitoring, and provides remediation action recommendations to security administrators for AWS Network Firewall policies with misconfigured routes.
* api-change:``devops-guru``: Add AnomalyReportedTimeRange field to include open and close time of anomalies.
* api-change:``eks``: Added waiters for EKS FargateProfiles.
* api-change:``sts``: Documentation updates for AWS Security Token Service.


2.2.17
======

* api-change:``sns``: Documentation updates for Amazon SNS.
* api-change:``ec2``: This release removes network-insights-boundary
* api-change:``imagebuilder``: Adds support for specifying parameters to customize components for recipes. Expands configuration of the Amazon EC2 instances that are used for building and testing images, including the ability to specify commands to run on launch, and more control over installation and removal of the SSM agent.
* api-change:``macie2``: Sensitive data findings in Amazon Macie now include enhanced location data for JSON and JSON Lines files
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``mgn``: Bug fix: Remove not supported EBS encryption type "NONE"
* api-change:``eks``: Adding new error code UnsupportedAddonModification for Addons in EKS
* api-change:``lambda``: Added support for AmazonMQRabbitMQ as an event source. Added support for VIRTUAL_HOST as SourceAccessType for streams event source mappings.


2.2.16
======

* api-change:``mediapackage-vod``: Add support for Widevine DRM on CMAF packaging configurations. Both Widevine and FairPlay DRMs can now be used simultaneously, with CBCS encryption.
* api-change:``sqs``: Documentation updates for Amazon SQS.
* api-change:``kendra``: Amazon Kendra Enterprise Edition now offered in smaller more granular units to enable customers with smaller workloads. Virtual Storage Capacity units now offer scaling in increments of 100,000 documents (up to 30GB) per unit and Virtual Query Units offer scaling increments of 8,000 queries per day.
* api-change:``sagemaker``: SageMaker model registry now supports up to 5 containers and associated environment variables.
* api-change:``autoscaling``: Amazon EC2 Auto Scaling infrastructure improvements and optimizations.
* api-change:``ec2``: Adding a new reserved field to support future infrastructure improvements for Amazon EC2 Fleet.
* api-change:``ssm-contacts``: Fixes the tag key length range to 128 chars,  tag value length to 256 chars; Adds support for UTF-8 chars for contact and channel names, Allows users to unset name in UpdateContact API; Adds throttling exception to StopEngagement API, validation exception to APIs UntagResource, ListTagsForResource
* api-change:``servicediscovery``: AWS Cloud Map now allows configuring the TTL of the SOA record for a hosted zone to control the negative caching for new services.
* api-change:``databrew``: Adds support for the output of job results to the AWS Glue Data Catalog.


2.2.15
======

* api-change:``amplifybackend``: Imports an existing backend authentication resource.
* api-change:``sagemaker``: Sagemaker Neo now supports running compilation jobs using customer's Amazon VPC
* api-change:``redshift``: Added InvalidClusterStateFault to the DisableLogging API, thrown when calling the API on a non available cluster.
* api-change:``mediaconvert``: MediaConvert adds support for HDR10+, ProRes 4444,  and XAVC outputs, ADM/DAMF support for Dolby Atmos ingest, and alternative audio and WebVTT caption ingest via HLS inputs. MediaConvert also now supports creating trickplay outputs for Roku devices for HLS, CMAF, and DASH output groups.
* api-change:``snowball``: AWS Snow Family customers can remotely monitor and operate their connected AWS Snowcone devices. AWS Snowball Edge Storage Optimized customers can now import and export their data using NFS.
* api-change:``proton``: Added waiters for template registration, service operations, and environment deployments.
* api-change:``glue``: Add JSON Support for Glue Schema Registry


2.2.14
======

* api-change:``docdb``: DocumentDB documentation-only edits
* api-change:``license-manager``: AWS License Manager now allows license administrators and end users to communicate to each other by setting custom status reasons when updating the status on a granted license.
* api-change:``cloud9``: Minor update to AWS Cloud9 documentation to allow correct parsing of outputted text
* api-change:``dax``: Add support for encryption in transit to DAX clusters.
* api-change:``cloudsearch``: This release replaces previous generation CloudSearch instances with equivalent new instances that provide better stability at the same price.
* bugfix:Pager: Display error message when unable to open pager. Fixes `#6225 <https://github.com/aws/aws-cli/issues/6225>`__
* api-change:``codebuild``: BucketOwnerAccess is currently not supported
* api-change:``quicksight``: Releasing new APIs for AWS QuickSight Folders
* api-change:``cloudfront``: Amazon CloudFront adds support for a new security policy, TLSv1.2_2021.
* api-change:``chime``: Adds EventIngestionUrl field to MediaPlacement
* api-change:``securityhub``: Added new resource details for ECS clusters and ECS task definitions. Added additional information for S3 buckets, Elasticsearch domains, and API Gateway V2 stages.
* api-change:``ec2``: This release adds support for provisioning your own IP (BYOIP) range in multiple regions. This feature is in limited Preview for this release. Contact your account manager if you are interested in this feature.
* api-change:``codeguru-reviewer``: Adds support for S3 based full repository analysis and changed lines scan.
* api-change:``mediatailor``: Update GetChannelSchedule to return information on ad breaks.
* api-change:``cloud9``: Updated documentation for CreateEnvironmentEC2 to explain that because Amazon Linux AMI has ended standard support as of December 31, 2020, we recommend you choose Amazon Linux 2--which includes long term support through 2023--for new AWS Cloud9 environments.
* api-change:``wafv2``: Added support for 15 new text transformation.
* api-change:``cloudformation``: CloudFormation registry service now supports 3rd party public type sharing
* api-change:``connect``: Released Amazon Connect quick connects management API for general availability (GA). For more information, see https://docs.aws.amazon.com/connect/latest/APIReference/Welcome.html
* api-change:``kendra``: Amazon Kendra now supports SharePoint 2013 and SharePoint 2016 when using a SharePoint data source.
* api-change:``events``: Added the following parameters to ECS targets: CapacityProviderStrategy, EnableECSManagedTags, EnableExecuteCommand, PlacementConstraints, PlacementStrategy, PropagateTags, ReferenceId, and Tags
* api-change:``transfer``: Customers can successfully use legacy clients with Transfer Family endpoints enabled for FTPS and FTP behind routers, firewalls, and load balancers by providing a Custom IP address used for data channel communication.


2.2.13
======

* api-change:``rds``: This release enables Database Activity Streams for RDS Oracle
* api-change:``rds``: This release enables fast cloning in Aurora Serverless. You can now clone between Aurora Serverless clusters and Aurora Provisioned clusters.
* api-change:``sagemaker``: Enable ml.g4dn instance types for SageMaker Batch Transform and SageMaker Processing
* api-change:``chime``: This release adds a new API UpdateSipMediaApplicationCall, to update an in-progress call for SipMediaApplication.
* api-change:``ec2``: This release adds support for VLAN-tagged network traffic over an Elastic Network Interface (ENI). This feature is in limited Preview for this release. Contact your account manager if you are interested in this feature.
* api-change:``mediatailor``: Adds AWS Secrets Manager Access Token Authentication for Source Locations
* api-change:``kms``: Adds support for multi-Region keys
* api-change:``kendra``: Amazon Kendra now supports the indexing of web documents for search through the web crawler.


2.2.12
======

* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``redshift-data``: Redshift Data API service now supports SQL parameterization.
* api-change:``mediaconnect``: When you enable source failover, you can now designate one of two sources as the primary source. You can choose between two failover modes to prevent any disruption to the video stream. Merge combines the sources into a single stream. Failover allows switching between a primary and a backup stream.
* api-change:``medialive``: AWS MediaLive now supports OCR-based conversion of DVB-Sub and SCTE-27 image-based source captions to WebVTT, and supports ingest of ad avail decorations in HLS input manifests.
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``greengrassv2``: We have verified the APIs being released here and are ready to release
* api-change:``iotanalytics``: Adds support for data store partitions.
* api-change:``ec2``: EC2 M5n, M5dn, R5n, R5dn metal instances with 100 Gbps network performance and Elastic Fabric Adapter (EFA) for ultra low latency
* api-change:``ec2``: Amazon EC2 adds new AMI property to flag outdated AMIs
* api-change:``connect``: This release adds new sets of APIs: AssociateBot, DisassociateBot, and ListBots. You can use it to programmatically add an Amazon Lex bot or Amazon Lex V2 bot on the specified Amazon Connect instance
* api-change:``lookoutmetrics``: Added "LEARNING" status for anomaly detector and updated description for "Offset" parameter in MetricSet APIs.


2.2.11
======

* api-change:``cognito-idp``: Amazon Cognito now supports targeted sign out through refresh token revocation
* api-change:``ram``: AWS Resource Access Manager (RAM) is releasing new field isResourceTypeDefault in ListPermissions and GetPermission response, and adding permissionArn parameter to GetResourceShare request to filter by permission attached
* api-change:``managedblockchain``: This release supports KMS customer-managed Customer Master Keys (CMKs) on member-specific Hyperledger Fabric resources.
* api-change:``transfer``: Documentation updates for the AWS Transfer Family service.
* api-change:``chime``: This SDK release adds support for UpdateAccount API to allow users to update their default license on Chime account.
* api-change:``personalize-events``: Support for unstructured text inputs in the items dataset to to automatically extract key information from product/content description as an input when creating solution versions.
* api-change:``appmesh``: AppMesh now supports additional routing capabilities in match and rewrites for Gateway Routes and Routes. Additionally, App Mesh also supports specifying DNS Response Types in Virtual Nodes.
* api-change:``sagemaker``: Using SageMaker Edge Manager with AWS IoT Greengrass v2 simplifies accessing, maintaining, and deploying models to your devices. You can now create deployable IoT Greengrass components during edge packaging jobs. You can choose to create a device fleet with or without creating an AWS IoT role alias.
* api-change:``ec2``: This release adds a new optional parameter connectivityType (public, private) for the CreateNatGateway API. Private NatGateway does not require customers to attach an InternetGateway to the VPC and can be used for communication with other VPCs and on-premise networks.
* api-change:``redshift``: Added InvalidClusterStateFault to the ModifyAquaConfiguration API, thrown when calling the API on a non available cluster.
* api-change:``appflow``: Adding MAP_ALL task type support.
* api-change:``kendra``: AWS Kendra now supports checking document status.
* api-change:``sagemaker-featurestore-runtime``: Release BatchGetRecord API for AWS SageMaker Feature Store Runtime.
* api-change:``proton``: This is the initial SDK release for AWS Proton


2.2.10
======

* api-change:``servicecatalog``: increase max pagesize for List/Search apis
* api-change:``sagemaker``: AWS SageMaker - Releasing new APIs related to Callback steps in model building pipelines. Adds experiment integration to model building pipelines.
* api-change:``cognito-idp``: Documentation updates for cognito-idp
* api-change:``qldb``: Documentation updates for Amazon QLDB
* api-change:``rds``: Documentation updates for RDS: fixing an outdated link to the RDS documentation in DBInstance$DBInstanceStatus
* api-change:``personalize``: Update regex validation in kmsKeyArn and s3 path API parameters for AWS Personalize APIs
* api-change:``pi``: The new GetDimensionKeyDetails action retrieves the attributes of the specified dimension group for a DB instance or data source.
* api-change:``autoscaling``: Documentation updates for Amazon EC2 Auto Scaling
* api-change:``cloudtrail``: AWS CloudTrail supports data events on new service resources, including Amazon DynamoDB tables and S3 Object Lambda access points.
* api-change:``eks``: Added updateConfig option that allows customers to control upgrade velocity in Managed Node Group.
* api-change:``fsx``: This release adds support for auditing end-user access to files, folders, and file shares using Windows event logs, enabling customers to meet their security and compliance needs.
* api-change:``glue``: Add SampleSize variable to S3Target to enable s3-sampling feature through API.
* api-change:``macie2``: This release of the Amazon Macie API introduces stricter validation of S3 object criteria for classification jobs.
* api-change:``medialive``: Add support for automatically setting the H.264 adaptive quantization and GOP B-frame fields.


2.2.9
=====

* api-change:``braket``: Introduction of a RETIRED status for devices.
* api-change:``ecs``: Documentation updates for Amazon ECS.
* api-change:``autoscaling``: You can now launch EC2 instances with GP3 volumes when using Auto Scaling groups with Launch Configurations
* api-change:``docdb``: This SDK release adds support for DocDB global clusters.
* api-change:``s3``: S3 Inventory now supports Bucket Key Status
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``forecast``: Added optional field AutoMLOverrideStrategy to CreatePredictor API that allows users to customize AutoML strategy. If provided in CreatePredictor request, this field is visible in DescribePredictor and GetAccuracyMetrics responses.
* api-change:``ssm``: Documentation updates for ssm to fix customer reported issue
* api-change:``route53resolver``: Documentation updates for Route 53 Resolver
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``s3control``: Amazon S3 Batch Operations now supports S3 Bucket Keys.


2.2.8
=====

* api-change:``ec2``: Added idempotency to CreateNetworkInterface using the ClientToken parameter.
* api-change:``lookoutmetrics``: Allowing dot(.) character in table name for RDS and Redshift as source connector.
* api-change:``iotwireless``: Added six new public customer logging APIs to allow customers to set/get/reset log levels at resource type and resource id level. The log level set from the APIs will be used to filter log messages that can be emitted to CloudWatch in customer accounts.
* api-change:``location``: Adds support for calculation of routes, resource tagging and customer provided KMS keys.
* api-change:``datasync``: Added SecurityDescriptorCopyFlags option that allows for control of which components of SMB security descriptors are copied from source to destination objects.
* api-change:``servicediscovery``: Bugfixes - The DiscoverInstances API operation now provides an option to return all instances for health-checked services when there are no healthy instances available.
* api-change:``polly``: Amazon Polly adds new Canadian French voice - Gabrielle. Gabrielle is available as Neural voice only.
* api-change:``sns``: This release adds SMS sandbox in Amazon SNS and the ability to view all configured origination numbers. The SMS sandbox provides a safe environment for sending SMS messages, without risking your reputation as an SMS sender.


2.2.7
=====

* api-change:``iotsitewise``: IoT SiteWise Monitor Portal API updates to add alarms feature configuration.
* api-change:``lightsail``: Documentation updates for Lightsail
* api-change:``devicefarm``: Introduces support for using our desktop testing service with applications hosted within your Virtual Private Cloud (VPC).
* api-change:``resource-groups``: Documentation updates for Resource Groups.
* api-change:``iotevents``: Releasing new APIs for AWS IoT Events Alarms
* api-change:``outposts``: Add ConflictException to DeleteOutpost, CreateOutpost
* api-change:``acm-pca``: This release enables customers to store CRLs in S3 buckets with Block Public Access enabled. The release adds the S3ObjectAcl parameter to the CreateCertificateAuthority and UpdateCertificateAuthority APIs to allow customers to choose whether their CRL will be publicly available.
* api-change:``mwaa``: Adds scheduler count selection for Environments using Airflow version 2.0.2 or later.
* api-change:``sqs``: Documentation updates for Amazon SQS for General Availability of high throughput for FIFO queues.
* api-change:``fsx``: This release adds LZ4 data compression support to FSx for Lustre to reduce storage consumption of both file system storage and file system backups.
* api-change:``ec2``: This release removes resource ids and tagging support for VPC security group rules.
* api-change:``qldb``: Support STANDARD permissions mode in CreateLedger and DescribeLedger. Add UpdateLedgerPermissionsMode to update permissions mode on existing ledgers.
* api-change:``ecs``: The release adds support for registering External instances to your Amazon ECS clusters.
* api-change:``cloudfront``: Documentation fix for CloudFront
* api-change:``kendra``: Amazon Kendra now suggests popular queries in order to help guide query typing and help overall accuracy.
* api-change:``ec2``: This release adds resource ids and tagging support for VPC security group rules.
* api-change:``iotevents-data``: Releasing new APIs for AWS IoT Events Alarms


2.2.6
=====

* api-change:``eks``: Update the EKS AddonActive waiter.
* api-change:``quicksight``: Add new parameters on RegisterUser and UpdateUser APIs to assign or update external ID associated to QuickSight users federated through web identity.
* api-change:``compute-optimizer``: Adds support for 1) additional instance types, 2) additional instance metrics, 3) finding reasons for instance recommendations, and 4) platform differences between a current instance and a recommended instance type.
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``mediaconnect``: MediaConnect now supports JPEG XS for AWS Cloud Digital Interface (AWS CDI) uncompressed workflows, allowing you to establish a bridge between your on-premises live video network and the AWS Cloud.
* api-change:``iot``: This release includes support for a new feature: Job templates for AWS IoT Device Management Jobs. The release includes job templates as a new resource and APIs for managing job templates.
* api-change:``license-manager``: AWS License Manager now supports periodic report generation.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``personalize``: Amazon Personalize now supports the ability to optimize a solution for a custom objective in addition to maximizing relevance.
* api-change:``ec2``: This release adds support for creating and managing EC2 On-Demand Capacity Reservations on Outposts.
* api-change:``iotsitewise``: Documentation updates for AWS IoT SiteWise.
* api-change:``support``: Documentation updates for support
* api-change:``neptune``: Neptune support for CopyTagsToSnapshots
* api-change:``kinesisanalyticsv2``: Kinesis Data Analytics now allows rapid iteration on Apache Flink stream processing through the Kinesis Data Analytics Studio feature.
* api-change:``iotdeviceadvisor``: AWS IoT Core Device Advisor is fully managed test capability for IoT devices. Device manufacturers can use Device Advisor to test their IoT devices for reliable and secure connectivity with AWS IoT.
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``applicationcostprofiler``: APIs for AWS Application Cost Profiler.
* api-change:``efs``: Update efs command to latest version
* api-change:``apprunner``: AWS App Runner is a service that provides a fast, simple, and cost-effective way to deploy from source code or a container image directly to a scalable and secure web application in the AWS Cloud.
* api-change:``workspaces``: Adds support for Linux device types in WorkspaceAccessProperties
* api-change:``autoscaling``: With this release, customers can easily use Predictive Scaling as a policy directly through Amazon EC2 Auto Scaling configurations to proactively scale their applications ahead of predicted demand.
* api-change:``compute-optimizer``: This release enables compute optimizer to support exporting  recommendations to Amazon S3 for EBS volumes and Lambda Functions.
* api-change:``quicksight``: Add ARN based Row Level Security support to CreateDataSet/UpdateDataSet APIs.
* api-change:``ce``: Introduced FindingReasonCodes, PlatformDifferences, DiskResourceUtilization and NetworkResourceUtilization to GetRightsizingRecommendation action
* api-change:``elasticache``: Documentation updates for elasticache
* api-change:``forecast``: Updated attribute statistics in DescribeDatasetImportJob response to support Long values
* api-change:``rekognition``: Amazon Rekognition Custom Labels adds support for customer managed encryption, using AWS Key Management Service, of image files copied into the service and files written back to the customer.
* api-change:``personalize``: Added new API to stop a solution version creation that is pending or in progress for Amazon Personalize
* api-change:``logs``: This release provides dimensions and unit support for metric filters.
* api-change:``opsworkscm``: New PUPPET_API_CRL attribute returned by DescribeServers API; new EngineVersion of 2019 available for Puppet Enterprise servers.
* api-change:``transfer``: AWS Transfer Family customers can now use AWS Managed Active Directory or AD Connector to authenticate their end users, enabling seamless migration of file transfer workflows that rely on AD authentication, without changing end users' credentials or needing a custom authorizer.
* api-change:``iam``: Add pagination to ListUserTags operation
* api-change:``sagemaker-a2i-runtime``: Documentation updates for Amazon A2I Runtime model


2.2.5
=====

* api-change:``imagebuilder``: Text-only updates for bundled documentation feedback tickets - spring 2021.
* api-change:``detective``: Updated descriptions of array parameters to add the restrictions on the array and value lengths.
* api-change:``securityhub``: Updated descriptions to add notes on array lengths.
* bugfix:``s3``: Fixed regression in not respecting ``--source-region`` for S3 to S3 copies. Fixes `#6152 <https://github.com/aws/aws-cli/issues/6152>`__
* api-change:``macie2``: This release of the Amazon Macie API adds support for defining run-time, S3 bucket criteria for classification jobs. It also adds resources for querying data about AWS resources that Macie monitors.
* api-change:``es``: Adds support for cold storage.
* api-change:``transcribe``: Transcribe Medical now supports identification of PHI entities within transcripts
* api-change:``ec2``: High Memory virtual instances are powered by Intel Sky Lake CPUs and offer up to 12TB of memory.
* api-change:``events``: Update InputTransformer variable limit from 10 to 100 variables.


2.2.4
=====

* api-change:``ssm-incidents``: AWS Systems Manager Incident Manager enables faster resolution of critical application availability and performance issues, management of contacts and post-incident analysis
* api-change:``eks``: This release updates create-nodegroup and update-nodegroup-config APIs for adding/updating taints on managed nodegroups.
* api-change:``iotwireless``: Add three new optional fields to support filtering and configurable sub-band in WirelessGateway APIs. The filtering is for all the RF region supported. The sub-band configuration is only applicable to LoRa gateways of US915 or AU915 RF region.
* api-change:``ssm``: This release adds new APIs to associate, disassociate and list related items in SSM OpsCenter; and this release adds DisplayName as a version-level attribute for SSM Documents and introduces two new document types: ProblemAnalysis, ProblemAnalysisTemplate.
* api-change:``ssm-contacts``: AWS Systems Manager Incident Manager enables faster resolution of critical application availability and performance issues, management of contacts and post incident analysis
* api-change:``config``: Adds paginator to multiple APIs: By default, the paginator allows user to iterate over the results and allows the CLI to return up to 1000 results.
* api-change:``kinesisanalyticsv2``: Amazon Kinesis Analytics now supports ListApplicationVersions and DescribeApplicationVersion API for Apache Flink applications
* api-change:``lookoutmetrics``: Enforcing UUID style for parameters that are already in UUID format today. Documentation specifying eventual consistency of lookoutmetrics resources.
* api-change:``lakeformation``: This release adds Tag Based Access Control to AWS Lake Formation service
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``ecs``: This release contains updates for Amazon ECS.
* api-change:``s3control``: Documentation updates for Amazon S3-control
* api-change:``mediaconvert``: AWS Elemental MediaConvert SDK has added support for Kantar SNAP File Audio Watermarking with a Kantar Watermarking account, and Display Definition Segment(DDS) segment data controls for DVB-Sub caption outputs.
* api-change:``connect``: Adds tagging support for Connect APIs CreateIntegrationAssociation and CreateUseCase.


2.2.3
=====

* api-change:``kinesisanalyticsv2``: Amazon Kinesis Analytics now supports RollbackApplication for Apache Flink applications to revert the application to the previous running version
* api-change:``servicediscovery``: Bugfix: Improved input validation for RegisterInstance action, InstanceId field
* api-change:``ssm``: SSM feature release - ChangeCalendar integration with StateManager.
* api-change:``finspace``: Documentation updates for FinSpace API.
* api-change:``auditmanager``: This release updates the CreateAssessmentFrameworkControlSet and UpdateAssessmentFrameworkControlSet API data types. For both of these data types, the control set name is now a required attribute.
* api-change:``sagemaker``: Amazon SageMaker Autopilot now provides the ability to automatically deploy the best model to an endpoint
* api-change:``nimble``: Documentation Updates for Amazon Nimble Studio.
* api-change:``kafka``: IAM Access Control for Amazon MSK enables you to create clusters that use IAM to authenticate clients and to allow or deny Apache Kafka actions for those clients.
* api-change:``snowball``: AWS Snow Family adds APIs for ordering and managing Snow jobs with long term pricing
* api-change:``finspace-data``: Documentation updates for FinSpaceData API.


2.2.2
=====

* api-change:``mturk``: Update mturk command to latest version
* api-change:``sagemaker``: Enable retrying Training and Tuning Jobs that fail with InternalServerError by setting RetryStrategy.
* api-change:``chime``: This release adds the ability to search for and order international phone numbers for Amazon Chime SIP media applications.
* api-change:``devops-guru``: Added GetCostEstimation and StartCostEstimation to get the monthly resource usage cost and added ability to view resource health by AWS service name and to search insights be AWS service name.
* api-change:``health``: Documentation updates for health
* api-change:``forecast``: Added new DeleteResourceTree operation that helps in deleting all the child resources of a given resource including the given resource.
* api-change:``robomaker``: Adds ROS2 Foxy as a supported Robot Software Suite Version and Gazebo 11 as a supported Simulation Software Suite Version
* api-change:``personalize``: Update URL for dataset export job documentation.
* api-change:``finspace-data``: Update FinSpace Data serviceAbbreviation
* api-change:``chime``: Added new BatchCreateChannelMembership API to support multiple membership creation for channels
* api-change:``cloudfront``: CloudFront now supports CloudFront Functions, a native feature of CloudFront that enables you to write lightweight functions in JavaScript for high-scale, latency-sensitive CDN customizations.
* api-change:``securityhub``: Updated ASFF to add the following new resource details objects: AwsEc2NetworkAcl, AwsEc2Subnet, and AwsElasticBeanstalkEnvironment.
* api-change:``customer-profiles``: This release introduces GetMatches and MergeProfiles APIs to fetch and merge duplicate profiles
* api-change:``marketplace-catalog``: Allows user defined names for Changes in a ChangeSet. Users can use ChangeNames to reference properties in another Change within a ChangeSet. This feature allows users to make changes to an entity when the entity identifier is not yet available while constructing the StartChangeSet request.
* api-change:``finspace-data``: This is the initial SDK release for the data APIs for Amazon FinSpace. Amazon FinSpace is a data management and analytics application for the financial services industry (FSI).
* api-change:``acm-pca``: This release adds the KeyStorageSecurityStandard parameter to the CreateCertificateAuthority API to allow customers to mandate a security standard to which the CA key will be stored within.
* api-change:``finspace``: This is the initial SDK release for the management APIs for Amazon FinSpace. Amazon FinSpace is a data management and analytics service for the financial services industry (FSI).


2.2.1
=====

* api-change:``organizations``: Minor text updates for AWS Organizations API Reference
* api-change:``nimble``: Amazon Nimble Studio is a virtual studio service that empowers visual effects, animation, and interactive content teams to create content securely within a scalable, private cloud service.
* api-change:``macie2``: The Amazon Macie API now provides S3 bucket metadata that indicates whether a bucket policy requires server-side encryption of objects when objects are uploaded to the bucket.
* api-change:``cloudformation``: Add CallAs parameter to GetTemplateSummary to enable use with StackSets delegated administrator integration
* api-change:``iotsitewise``: AWS IoT SiteWise interpolation API will get interpolated values for an asset property per specified time interval during a period of time.
* bugfix:``configure``: Fix `list` command to show correct profile location when AWS_DEFAULT_PROFILE set, fixes `#6119 <https://github.com/aws/aws-cli/issues/6119>`__
* api-change:``connect``: Updated max number of tags that can be attached from 200 to 50. MaxContacts is now an optional parameter for the UpdateQueueMaxContact API.
* api-change:``chime``: Increase AppInstanceUserId length to 64 characters
* api-change:``mediapackage-vod``: MediaPackage now offers the option to place your Sequence Parameter Set (SPS), Picture Parameter Set (PPS), and Video Parameter Set (VPS) encoder metadata in every video segment instead of in the init fragment for DASH and CMAF endpoints.
* api-change:``ecs``: Add support for EphemeralStorage on TaskDefinition and TaskOverride
* enhancement:arguments: Remove redundant '-' from two character pluralized acronyms in argument names
* enhancement:arguments: Remove redundant '-' from two character pluralized acronyms in argument names


2.2.0
=====

* api-change:``iotwireless``: Add a new optional field MessageType to support Sidewalk devices in SendDataToWirelessDevice API
* api-change:``forecast``: This release adds EstimatedTimeRemaining minutes field to the DescribeDatasetImportJob, DescribePredictor, DescribeForecast API response which denotes the time remaining to complete the job IN_PROGRESS.
* enhancement:``s3``: Add support for expressing rate configurations (e.g. ``max_bandwidth``) in terms of bits per second (``b/s``).
* api-change:``elasticache``: This release introduces log delivery of Redis slow log from Amazon ElastiCache.
* api-change:``kinesisanalyticsv2``: Amazon Kinesis Data Analytics now supports custom application maintenance configuration using UpdateApplicationMaintenanceConfiguration API for Apache Flink applications. Customers will have visibility when their application is under maintenance status using 'MAINTENANCE' application status.
* api-change:``glue``: Adding Kafka Client Auth Related Parameters
* api-change:``eks``: This release updates existing Amazon EKS input validation so customers will see an InvalidParameterException instead of a ParamValidationError when they enter 0 for minSize and/or desiredSize. It also adds LaunchTemplate information to update responses and a new "CUSTOM" value for AMIType.
* api-change:``cognito-idp``: Documentation updates for cognito-idp
* feature:``s3``: Add experimental support for performing S3 transfers using the AWS Common Runtime (CRT). It provides a C-based S3 transfer client that can improve transfer throughput for ``s3`` commands.
* api-change:``mediapackage``: Add support for Widevine DRM on CMAF origin endpoints. Both Widevine and FairPlay DRMs can now be used simultaneously, with CBCS encryption.
* api-change:``ec2``: Adding support for Red Hat Enterprise Linux with HA for Reserved Instances.
* api-change:``auditmanager``: This release restricts using backslashes in control, assessment, and framework names. The controlSetName field of the UpdateAssessmentFrameworkControlSet API now allows strings without backslashes.
* api-change:``mediaconvert``: Documentation updates for mediaconvert
* api-change:``codeguru-reviewer``: Include KMS Key Details in Repository Association APIs to enable usage of customer managed KMS Keys.
* api-change:``personalize``: Added support for exporting data imported into an Amazon Personalize dataset to a specified data source (Amazon S3 bucket).
* api-change:``securityhub``: Replaced the term "master" with "administrator". Added new actions to replace AcceptInvitation, GetMasterAccount, and DisassociateFromMasterAccount. In Member, replaced MasterId with AdministratorId.
* bugfix:``pager``: Fix bug with spawning pager process if there is not output. Fixes `#5144 <https://github.com/aws/aws-cli/issues/5144>`__
* api-change:``sns``: Amazon SNS adds two new attributes, TemplateId and EntityId, for using sender IDs to send SMS messages to destinations in India.


2.1.39
======

* api-change:``kendra``: Amazon Kendra now enables users to override index-level boosting configurations for each query.
* api-change:``redshift``: Add operations: AddPartner, DescribePartners, DeletePartner, and UpdatePartnerStatus to support tracking integration status with data partners.
* api-change:``groundstation``: Support new S3 Recording Config allowing customers to write downlink data directly to S3.
* api-change:``ce``: Adding support for Sagemaker savings plans in GetSavingsPlansPurchaseRecommendation API
* api-change:``detective``: Added parameters to track the data volume in bytes for a member account. Deprecated the existing parameters that tracked the volume as a percentage of the allowed volume for a behavior graph. Changes reflected in MemberDetails object.
* api-change:``savingsplans``: Added support for Amazon SageMaker in Machine Learning Savings Plans
* api-change:``cloudformation``: Added support for creating and updating stack sets with self-managed permissions from templates that reference macros.


2.1.38
======

* api-change:``dms``: AWS DMS added support of TLS for Kafka endpoint. Added Describe endpoint setting API for DMS endpoints.
* api-change:``codestar-connections``: This release adds tagging support for CodeStar Connections Host resources
* api-change:``route53``: Documentation updates for route53
* api-change:``sts``: STS now supports assume role with Web Identity using JWT token length upto 20000 characters
* api-change:``mediaconnect``: For flows that use Listener protocols, you can now easily locate an output's outbound IP address for a private internet. Additionally, MediaConnect now supports the Waiters feature that makes it easier to poll for the status of a flow until it reaches its desired state.
* api-change:``config``: Add exception for DeleteRemediationConfiguration and DescribeRemediationExecutionStatus


2.1.37
======

* api-change:``fsx``: Support for cross-region and cross-account backup copies
* api-change:``rds``: Clarify that enabling or disabling automated backups causes a brief downtime, not an outage.
* api-change:``sts``: This release adds the SourceIdentity parameter that can be set when assuming a role.
* api-change:``shield``: CreateProtection now throws InvalidParameterException instead of InternalErrorException when system tags (tag with keys prefixed with "aws:") are passed in.
* api-change:``codebuild``: AWS CodeBuild now allows you to set the access permissions for build artifacts, project artifacts, and log files that are uploaded to an Amazon S3 bucket that is owned by another account.
* api-change:``redshift``: Add support for case sensitive table level restore
* api-change:``ec2``: Add paginator support to DescribeStoreImageTasks and update documentation.
* api-change:``lightsail``: Documentation updates for Amazon Lightsail.
* api-change:``comprehendmedical``: The InferICD10CM API now returns TIME_EXPRESSION entities that refer to medical conditions.
* api-change:``redshift``: Added support to enable AQUA in Amazon Redshift clusters.


2.1.36
======

* api-change:``ivs``: This release adds support for the Auto-Record to S3 feature. Amazon IVS now enables you to save your live video to Amazon S3.
* api-change:``robomaker``: This release allows RoboMaker customers to specify custom tools to run with their simulation job
* api-change:``lookoutequipment``: This release introduces support for Amazon Lookout for Equipment.
* bugfix:``profile``: Fix bug in profile resolution order when AWS_PROFILE environment variable contains non-existing profile but `--profile` command line argument contains correct profile name
* api-change:``kinesis-video-archived-media``: Documentation updates for archived.kinesisvideo
* api-change:``autoscaling``: Amazon EC2 Auto Scaling announces Warm Pools that help applications to scale out faster by pre-initializing EC2 instances and save money by requiring fewer continuously running instances
* api-change:``appstream``: This release provides support for image updates
* api-change:``elasticache``: This release adds tagging support for all AWS ElastiCache resources except Global Replication Groups.
* api-change:``storagegateway``: File Gateway APIs now support FSx for Windows as a cloud storage.
* api-change:``accessanalyzer``: IAM Access Analyzer now analyzes your CloudTrail events to identify actions and services that have been used by an IAM entity (user or role) and generates an IAM policy that is based on that activity.
* api-change:``ram``: Documentation updates for AWS RAM resource sharing
* api-change:``mgn``: Add new service - Application Migration Service.
* bugfix:``profile``: Fix bug in profile resolution order when AWS_PROFILE environment variable contains non-existing profile but `--profile` command line argument contains correct profile name
* api-change:``customer-profiles``: Documentation updates for Put-Integration API


2.1.35
======

* api-change:``auditmanager``: AWS Audit Manager has updated the GetAssessment API operation to include a new response field called userRole. The userRole field indicates the role information and IAM ARN of the API caller.
* api-change:``ssm``: Supports removing a label or labels from a parameter, enables ScheduledEndTime and ChangeDetails for StartChangeRequestExecution API, supports critical/security/other noncompliant count for patch API.
* api-change:``medialive``: MediaLive now support HTML5 Motion Graphics overlay
* api-change:``mediapackage``: SPEKE v2 is an upgrade to the existing SPEKE API to support multiple encryption keys, based on an encryption contract selected by the customer.
* api-change:``appflow``: Added destination properties for Zendesk.
* api-change:``medialive``: MediaLive VPC outputs update to include Availability Zones, Security groups, Elastic Network Interfaces, and Subnet Ids in channel response
* api-change:``cloud9``: Documentation updates for Cloud9
* api-change:``imagebuilder``: This release adds support for Block Device Mappings for container image builds, and adds distribution configuration support for EC2 launch templates in AMI builds.
* api-change:``ec2``: This release adds support for storing EBS-backed AMIs in S3 and restoring them from S3 to enable cross-partition copying of AMIs


2.1.34
======

* api-change:``batch``: AWS Batch adds support for Amazon EFS File System
* api-change:``lightsail``: - This release adds support for state detail for Amazon Lightsail container services.
* api-change:``iotwireless``: Add Sidewalk support to APIs: GetWirelessDevice, ListWirelessDevices, GetWirelessDeviceStatistics. Add Gateway connection status in GetWirelessGatewayStatistics API.
* api-change:``detective``: Added the ability to assign tag values to Detective behavior graphs. Tag values can be used for attribute-based access control, and for cost allocation for billing.
* api-change:``directconnect``: This release adds MACsec support to AWS Direct Connect
* api-change:``comprehend``: Support for customer managed KMS encryption of Comprehend custom models
* api-change:``machinelearning``: Minor documentation updates and link updates.
* bugfix:Configuration: Fixed an issue when using the aws configure set command to update profiles with a space in the profile name.
* api-change:``cloudhsm``: Minor documentation and link updates.
* api-change:``datapipeline``: Minor documentation updates and link updates.
* api-change:``workmail``: This release adds support for mobile device access rules management in Amazon WorkMail.
* api-change:``cloud9``: Add ImageId input parameter to CreateEnvironmentEC2 endpoint. New parameter enables creation of environments with different AMIs.
* api-change:``ec2``: VPC Flow Logs Service adds a new API, GetFlowLogsIntegrationTemplate, which generates CloudFormation templates for Athena. For more info, see https://docs.aws.amazon.com/console/vpc/flow-logs/athena
* api-change:``lex-models``: Lex now supports the ja-JP locale
* api-change:``cloudformation``: 1. Added a new parameter RegionConcurrencyType in OperationPreferences. 2. Changed the name of AccountUrl to AccountsUrl in DeploymentTargets parameter.
* api-change:``fms``: Added Firewall Manager policy support for AWS Route 53 Resolver DNS Firewall.
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``redshift``: Enable customers to share access to their Redshift clusters from other VPCs (including VPCs from other accounts).
* api-change:``wafv2``: Added support for ScopeDownStatement for ManagedRuleGroups, Labels, LabelMatchStatement, and LoggingFilter. For more information on these features, see the AWS WAF Developer Guide.
* api-change:``route53resolver``: Route 53 Resolver DNS Firewall is a firewall service that allows you to filter and regulate outbound DNS traffic for your VPCs.
* api-change:``kendra``: AWS Kendra's ServiceNow data source now supports OAuth 2.0 authentication and knowledge article filtering via a ServiceNow query.
* api-change:``transcribe``: Amazon Transcribe now supports creating custom language models in the following languages: British English (en-GB), Australian English (en-AU), Indian Hindi (hi-IN), and US Spanish (es-US).
* api-change:``cognito-sync``: Minor documentation updates and link updates.
* api-change:``iot``: Added ability to prefix search on attribute value for ListThings API.
* api-change:``mediaconvert``: MediaConvert now supports HLS ingest, sidecar WebVTT ingest, Teletext color & style passthrough to TTML subtitles, TTML to WebVTT subtitle conversion with style, & DRC profiles in AC3 audio.
* api-change:``pricing``: Minor documentation and link updates.


2.1.33
======

* api-change:``sagemaker``: Amazon SageMaker Autopilot now supports 1) feature importance reports for AutoML jobs and 2) PartialFailures for AutoML jobs
* api-change:``events``: Add support for SageMaker Model Builder Pipelines Targets to EventBridge
* api-change:``iotwireless``: Support tag-on-create for WirelessDevice.
* api-change:``config``: Adding new APIs to support ConformancePack Compliance CI in Aggregators
* api-change:``lookoutmetrics``: Allowing uppercase alphabets for RDS and Redshift database names.
* api-change:``location``: Amazon Location added support for specifying pricing plan information on resources in alignment with our cost model.
* api-change:``lookoutmetrics``: Amazon Lookout for Metrics is now generally available. You can use Lookout for Metrics to monitor your data for anomalies. For more information, see the Amazon Lookout for Metrics Developer Guide.
* api-change:``customer-profiles``: This release adds an optional parameter named FlowDefinition in PutIntegrationRequest.
* api-change:``ec2``: ReplaceRootVolume feature enables customers to replace the EBS root volume of a running instance to a previously known state. Add support to grant account-level access to the EC2 serial console
* api-change:``sagemaker``: This feature allows customer to specify the environment variables in their CreateTrainingJob requests.
* api-change:``glue``: Allow Dots in Registry and Schema Names for CreateRegistry, CreateSchema; Fixed issue when duplicate keys are present and not returned as part of QuerySchemaVersionMetadata.
* api-change:``iam``: AWS Identity and Access Management GetAccessKeyLastUsed API will throw a custom error if customer public key is not found for access keys.
* api-change:``frauddetector``: This release adds support for Batch Predictions in Amazon Fraud Detector.
* api-change:``medialive``: EML now supports handling HDR10 and HLG 2020 color space from a Link input.
* api-change:``docdb``: This release adds support for Event Subscriptions to DocumentDB.
* api-change:``wafv2``: Added custom request handling and custom response support in rule actions and default action; Added the option to inspect the web request body as parsed and filtered JSON.
* api-change:``rekognition``: This release introduces AWS tagging support for Amazon Rekognition collections, stream processors, and Custom Label models.
* api-change:``alexaforbusiness``: Added support for enabling and disabling data retention in the CreateProfile and UpdateProfile APIs and retrieving the state of data retention for a profile in the GetProfile API.
* api-change:``transcribe``: Amazon Transcribe now supports tagging words that match your vocabulary filter for batch transcription.
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``pinpoint``: Added support for journey pause/resume, journey updatable import segment and journey quiet time wait.
* api-change:``sqs``: Documentation updates for Amazon SQS
* api-change:``databrew``: This SDK release adds two new dataset features: 1) support for specifying a database connection as a dataset input 2) support for dynamic datasets that accept configurable parameters in S3 path.
* api-change:``ec2-instance-connect``: Adding support to push SSH keys to the EC2 serial console in order to allow an SSH connection to your Amazon EC2 instance's serial port.


2.1.32
======

* api-change:``ec2``: X2gd instances are the next generation of memory-optimized instances powered by AWS-designed, Arm-based AWS Graviton2 processors.
* api-change:``ec2``: maximumEfaInterfaces added to DescribeInstanceTypes API
* api-change:``ssm``: This release allows SSM Explorer customers to enable OpsData sources across their organization when creating a resource data sync.
* api-change:``fis``: Updated maximum allowed size of action parameter from 64 to 1024
* api-change:``gamelift``: GameLift adds support for using event notifications to monitor game session placements. Specify an SNS topic or use CloudWatch Events to track activity for a game session queue.
* api-change:``codeartifact``: Documentation updates for CodeArtifact
* api-change:``s3``: Documentation updates for Amazon S3
* api-change:``ce``: You can now create cost categories with inherited value rules and specify default values for any uncategorized costs.
* api-change:``route53``: Documentation updates for route53
* api-change:``macie2``: This release of the Amazon Macie API adds support for publishing sensitive data findings to AWS Security Hub and specifying which categories of findings to publish to Security Hub.
* api-change:``s3control``: Documentation updates for s3-control
* api-change:``ec2``: This release adds support for UEFI boot on selected AMD- and Intel-based EC2 instances.
* api-change:``greengrass``: Updated the parameters to make name required for CreateGroup API.
* api-change:``sagemaker``: Adding authentication support for pulling images stored in private Docker registries to build containers for real-time inference.
* api-change:``iam``: Documentation updates for IAM operations and descriptions.


2.1.31
======

* api-change:``workspaces``: Adds API support for WorkSpaces bundle management operations.
* api-change:``gamelift``: GameLift expands to six new AWS Regions, adds support for multi-location fleets to streamline management of hosting resources, and lets you customize more of the game session placement process.
* api-change:``ssm``: Update ssm command to latest version
* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``accessanalyzer``: This release adds support for the ValidatePolicy API. IAM Access Analyzer is adding over 100 policy checks and actionable recommendations that help you validate your policies during authoring.
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``autoscaling``: Amazon EC2 Auto Scaling Instance Refresh now supports phased deployments.
* api-change:``codedeploy``: AWS CodeDeploy can now detect instances running an outdated revision of your application and automatically update them with the latest revision.
* api-change:``lambda``: Allow empty list for function response types
* api-change:``fis``: Initial release of AWS Fault Injection Simulator, a managed service that enables you to perform fault injection experiments on your AWS workloads
* api-change:``mwaa``: This release adds UPDATE_FAILED and UNAVAILABLE MWAA environment states.
* api-change:``iam``: Documentation updates for AWS Identity and Access Management (IAM).
* api-change:``s3``: S3 Object Lambda is a new S3 feature that enables users to apply their own custom code to process the output of a standard S3 GET request by automatically invoking a Lambda function with a GET request
* api-change:``s3control``: S3 Object Lambda is a new S3 feature that enables users to apply their own custom code to process the output of a standard S3 GET request by automatically invoking a Lambda function with a GET request
* api-change:``medialive``: Update medialive command to latest version
* api-change:``mediatailor``: MediaTailor channel assembly is a new manifest-only service that allows you to assemble linear streams using your existing VOD content.
* api-change:``batch``: Making serviceRole an optional parameter when creating a compute environment. If serviceRole is not provided then Service Linked Role will be created (or reused if it already exists).
* api-change:``ecs``: This is for ecs exec feature release which includes two new APIs - execute-command and update-cluster and an AWS CLI customization for execute-command API
* api-change:``mediaconnect``: This release adds support for the SRT-listener protocol on sources and outputs.
* api-change:``sagemaker``: Support new target device ml_eia2 in SageMaker CreateCompilationJob API
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``redshift``: Add new fields for additional information about VPC endpoint for clusters with reallocation enabled, and a new field for total storage capacity for all clusters.
* api-change:``securityhub``: New object for separate provider and customer values. New objects track S3 Public Access Block configuration and identify sensitive data. BatchImportFinding requests are limited to 100 findings.
* api-change:``cur``: - Added optional billingViewArn field for OSG.


2.1.30
======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``wellarchitected``: Update wellarchitected command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``health``: Update health command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``mwaa``: Update mwaa command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``ecr-public``: Update ecr-public command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``rds``: Update rds command to latest version


2.1.29
======

* bugfix:``locale``: Fix when UTF-8 isn't preferred encoding with locale equals to "POSIX" or "C"


2.1.28
======

* enhancement:Python: Update embedded Python version to 3.8.8 for standalone artifacts


2.1.27
======

* api-change:``iam``: Update iam command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``workmailmessageflow``: Update workmailmessageflow command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version


2.1.26
======

* api-change:``rds``: Update rds command to latest version
* api-change:``databrew``: Update databrew command to latest version


2.1.25
======

* api-change:``organizations``: Update organizations command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``macie``: Update macie command to latest version


2.1.24
======

* api-change:``emr-containers``: Update emr-containers command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``databrew``: Update databrew command to latest version


2.1.23
======

* api-change:``medialive``: Update medialive command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``rds-data``: Update rds-data command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``location``: Update location command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``connect``: Update connect command to latest version


2.1.22
======

* api-change:``backup``: Update backup command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``greengrassv2``: Update greengrassv2 command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``customer-profiles``: Update customer-profiles command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``lexv2-runtime``: Update lexv2-runtime command to latest version
* api-change:``lexv2-models``: Update lexv2-models command to latest version
* api-change:``wellarchitected``: Update wellarchitected command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version


2.1.21
======

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* enhancement:codeartifact: Added login support for NuGet client v4.9.4
* api-change:``kafka``: Update kafka command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


2.1.20
======

* api-change:``chime``: Update chime command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``ecs``: Update ecs command to latest version


2.1.19
======

* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version


2.1.18
======

* api-change:``ssm``: Update ssm command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``appstream``: Update appstream command to latest version


2.1.17
======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``autoscaling-plans``: Update autoscaling-plans command to latest version
* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version


2.1.16
======

* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``healthlake``: Update healthlake command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``cloudsearch``: Update cloudsearch command to latest version


2.1.15
======

* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* enhancement:Wizards: Migrate ``lambda wizard new-function`` command to new UI
* api-change:``dms``: Update dms command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version


2.1.14
======

* api-change:``s3``: Update s3 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``service-quotas``: Update service-quotas command to latest version
* api-change:``connectparticipant``: Update connectparticipant command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


2.1.13
======

* api-change:``sqs``: Update sqs command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``route53resolver``: Update route53resolver command to latest version


2.1.12
======

* api-change:``location``: Update location command to latest version
* api-change:``amp``: Update amp command to latest version
* enhancement:Wizards: Migrate ``dynamodb wizard new-table`` command to new UI
* api-change:``wellarchitected``: Update wellarchitected command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


2.1.11
======

* api-change:``amp``: Update amp command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``greengrassv2``: Update greengrassv2 command to latest version
* api-change:``iotwireless``: Update iotwireless command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``iotfleethub``: Update iotfleethub command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``iotdeviceadvisor``: Update iotdeviceadvisor command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``pi``: Update pi command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version


2.1.10
======

* api-change:``networkmanager``: Update networkmanager command to latest version
* enhancement:Wizards: Add support for new form-based wizard UI. Migrated ``iam wizard new-role`` command to new UI in order to add support for the displaying of policy documents, generation of sample AWS CLI commands, and generation of sample AWS CloudFormation templates.
* api-change:``kendra``: Update kendra command to latest version
* enhancement:Wizards: Add ``events wizard new-rule`` command. The wizard helps create an EventBridge rule and add a target for that rule.
* api-change:``ec2``: Update ec2 command to latest version


2.1.9
=====

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``redshift``: Update redshift command to latest version


2.1.8
=====

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``healthlake``: Update healthlake command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``sagemaker-edge``: Update sagemaker-edge command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``emr-containers``: Update emr-containers command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``auditmanager``: Update auditmanager command to latest version


2.1.7
=====

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``amplifybackend``: Update amplifybackend command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``batch``: Update batch command to latest version


2.1.6
=====

* api-change:``customer-profiles``: Update customer-profiles command to latest version
* api-change:``ecr-public``: Update ecr-public command to latest version
* api-change:``appintegrations``: Update appintegrations command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``honeycode``: Update honeycode command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``amplifybackend``: Update amplifybackend command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``lookoutvision``: Update lookoutvision command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker-featurestore-runtime``: Update sagemaker-featurestore-runtime command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``devops-guru``: Update devops-guru command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``connect-contact-lens``: Update connect-contact-lens command to latest version
* api-change:``lambda``: Update lambda command to latest version


2.1.5
=====

* api-change:``ec2``: Update ec2 command to latest version


2.1.4
=====

* api-change:``fsx``: Update fsx command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``mwaa``: Update mwaa command to latest version
* api-change:``cognito-identity``: Update cognito-identity command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``signer``: Update signer command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudtrail``: Update cloudtrail command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``translate``: Update translate command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``timestream-write``: Update timestream-write command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``timestream-query``: Update timestream-query command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``forecast``: Update forecast command to latest version


2.1.3
=====

* enhancement:autoprompt: Add output panel to autoprmpot mode
* api-change:``glue``: Update glue command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``ds``: Update ds command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


2.1.2
=====

* api-change:``rds``: Update rds command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``iotsecuretunneling``: Update iotsecuretunneling command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``codepipeline``: Update codepipeline command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``network-firewall``: Update network-firewall command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``dms``: Update dms command to latest version


2.1.1
=====

* api-change:``forecast``: Update forecast command to latest version
* api-change:``iot``: Update iot command to latest version
* enhancement:``lightsail push-container-image``: Add ``lightsail push-container-image`` command
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``databrew``: Update databrew command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``servicecatalog-appregistry``: Update servicecatalog-appregistry command to latest version
* api-change:``amplify``: Update amplify command to latest version


2.1.0
=====

* feature:autoprompt: Improved autoprompt mode. See `#5664 <https://github.com/aws/aws-cli/issues/5664>`__
* api-change:``ssm``: Update ssm command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``ec2``: Update ec2 command to latest version


2.0.63
======

* api-change:``datasync``: Update datasync command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``iotanalytics``: Update iotanalytics command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version


2.0.62
======

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version


2.0.61
======

* api-change:``workmail``: Update workmail command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version


2.0.60
======

* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``neptune``: Update neptune command to latest version
* api-change:``macie2``: Update macie2 command to latest version


2.0.59
======

* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version


2.0.58
======

* api-change:``appsync``: Update appsync command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``docdb``: Update docdb command to latest version


2.0.57
======

* api-change:``amplify``: Update amplify command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``snowball``: Update snowball command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``workmail``: Update workmail command to latest version


2.0.56
======

* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


2.0.55
======

* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``marketplace-catalog``: Update marketplace-catalog command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version


2.0.54
======

* api-change:``s3``: Update s3 command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``s3outposts``: Update s3outposts command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``emr``: Update emr command to latest version


2.0.53
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``timestream-write``: Update timestream-write command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``docdb``: Update docdb command to latest version
* api-change:``batch``: Update batch command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``schemas``: Update schemas command to latest version
* api-change:``timestream-query``: Update timestream-query command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``sts``: Update sts command to latest version


2.0.52
======

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``savingsplans``: Update savingsplans command to latest version
* api-change:``textract``: Update textract command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``translate``: Update translate command to latest version


2.0.51
======

* api-change:``dynamodbstreams``: Update dynamodbstreams command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``comprehend``: Update comprehend command to latest version


2.0.50
======

* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``greengrass``: Update greengrass command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``connect``: Update connect command to latest version


2.0.49
======

* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``budgets``: Update budgets command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``docdb``: Update docdb command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``kafka``: Update kafka command to latest version


2.0.48
======

* api-change:``glue``: Update glue command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``redshift-data``: Update redshift-data command to latest version
* api-change:``sso-admin``: Update sso-admin command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ebs``: Update ebs command to latest version
* api-change:``kinesisanalyticsv2``: Update kinesisanalyticsv2 command to latest version


2.0.47
======

* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``xray``: Update xray command to latest version


2.0.46
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version


2.0.45
======

* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``cur``: Update cur command to latest version
* api-change:``route53``: Update route53 command to latest version


2.0.44
======

* api-change:``redshift``: Update redshift command to latest version
* api-change:``appflow``: Update appflow command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``route53resolver``: Update route53resolver command to latest version


2.0.43
======

* api-change:``logs``: Update logs command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``dms``: Update dms command to latest version
* enhancement:pager: Add ``--no-cli-pager`` command line option to disable output ot pager
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``ssm``: Update ssm command to latest version


2.0.42
======

* api-change:``chime``: Update chime command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``lakeformation``: Update lakeformation command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version


2.0.41
======

* api-change:``license-manager``: Update license-manager command to latest version
* api-change:``identitystore``: Update identitystore command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``acm-pca``: Update acm-pca command to latest version
* api-change:``appstream``: Update appstream command to latest version
* api-change:``acm``: Update acm command to latest version
* api-change:``elb``: Update elb command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``kinesis``: Update kinesis command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``securityhub``: Update securityhub command to latest version


2.0.40
======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``braket``: Update braket command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``cloud9``: Update cloud9 command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``rds``: Update rds command to latest version


2.0.39
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``sms``: Update sms command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``savingsplans``: Update savingsplans command to latest version
* enhancement:``cloudformation``: CloudFormation ``deploy`` command now supports various JSON file formats as an input for ``--parameter-overrides`` option `#2828 <https://github.com/aws/aws-cli/issues/2828>`__
* enhancement:``codeartifact login``: Add support for ``--namespace`` parameter `#5291 <https://github.com/aws/aws-cli/issues/5291>`__


2.0.38
======

* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lex-runtime``: Update lex-runtime command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``personalize-events``: Update personalize-events command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``transcribe``: Update transcribe command to latest version


2.0.37
======

* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``health``: Update health command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version


2.0.36
======

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``resource-groups``: Update resource-groups command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``firehose``: Update firehose command to latest version


2.0.35
======

* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``kendra``: Update kendra command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``datasync``: Update datasync command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``ivs``: Update ivs command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``mediapackage``: Update mediapackage command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``mq``: Update mq command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``ec2``: Update ec2 command to latest version


2.0.34
======

* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``config``: Update config command to latest version
* api-change:``workspaces``: Update workspaces command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``quicksight``: Update quicksight command to latest version


2.0.33
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``groundstation``: Update groundstation command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``connect``: Update connect command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


2.0.31
======

* api-change:``ivs``: Update ivs command to latest version
* bugfix:``s3``: Fix `s3 cp` bug when request-payer parameter wasn't passed to subcommands
* enhancement:docs: Improve AWS CLI docs to include documentation strings for parameters in nested input structures


2.0.30
======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``events``: Update events command to latest version
* api-change:``cloudhsmv2``: Update cloudhsmv2 command to latest version
* api-change:``ebs``: Update ebs command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``forecast``: Update forecast command to latest version
* api-change:``sns``: Update sns command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``comprehend``: Update comprehend command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``amplify``: Update amplify command to latest version


2.0.29
======

* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``lakeformation``: Update lakeformation command to latest version


2.0.28
======

* api-change:``connect``: Update connect command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``appsync``: Update appsync command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


2.0.27
======

* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ecr``: Update ecr command to latest version


2.0.26
======

* api-change:``codecommit``: Update codecommit command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``honeycode``: Update honeycode command to latest version
* api-change:``amplify``: Update amplify command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``emr``: Update emr command to latest version


2.0.25
======

* api-change:``ec2``: Update ec2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``sqs``: Update sqs command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``rekognition``: Update rekognition command to latest version


2.0.24
======

* api-change:``rds``: Update rds command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* bugfix:locale: Add support for AWS_CLI_FILE_ENCODING environment variable to cloudformation and eks customizations
* api-change:``snowball``: Update snowball command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``sesv2``: Update sesv2 command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``support``: Update support command to latest version
* api-change:``appmesh``: Update appmesh command to latest version


2.0.23
======

* api-change:``lambda``: Update lambda command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``dataexchange``: Update dataexchange command to latest version
* api-change:``qldb``: Update qldb command to latest version
* api-change:``polly``: Update polly command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``alexaforbusiness``: Update alexaforbusiness command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``autoscaling``: Update autoscaling command to latest version


2.0.22
======

* api-change:``iot-data``: Update iot-data command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``ecs``: Update ecs command to latest version


2.0.21
======

* api-change:``macie2``: Update macie2 command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codeartifact``: Update codeartifact command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``compute-optimizer``: Update compute-optimizer command to latest version


2.0.20
======

* api-change:``personalize``: Update personalize command to latest version
* api-change:``shield``: Update shield command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``cloudfront``: Update cloudfront command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``transfer``: Update transfer command to latest version
* bugfix:config file: Improve config parsing to handle values with square brackets. fixes `#5263 <https://github.com/aws/aws-cli/issues/5263>`__
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``sagemaker-runtime``: Update sagemaker-runtime command to latest version
* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version


2.0.19
======

* api-change:``es``: Update es command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``directconnect``: Update directconnect command to latest version
* api-change:``meteringmarketplace``: Update meteringmarketplace command to latest version
* bugfix:``cloudformation package``: Preserve quotes for YAML boolean strings. Fixes `#5245 <https://github.com/aws/aws-cli/issues/5245>`__
* api-change:``glue``: Update glue command to latest version
* api-change:``lightsail``: Update lightsail command to latest version


2.0.18
======

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``worklink``: Update worklink command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``marketplace-catalog``: Update marketplace-catalog command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``kms``: Update kms command to latest version
* api-change:``qldb-session``: Update qldb-session command to latest version


2.0.17
======

* api-change:``autoscaling``: Update autoscaling command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``macie``: Update macie command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``dlm``: Update dlm command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``ec2``: Update ec2 command to latest version


2.0.16
======

* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``s3``: Update s3 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``backup``: Update backup command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``codebuild``: Update codebuild command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``codedeploy``: Update codedeploy command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version


2.0.15
======

* enhancement:IMDS: Use IMDSv2 for autodiscovering EC2 region. Fixes `#4976 <https://github.com/aws/aws-cli/issues/4976>`__
* api-change:``glue``: Update glue command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``sts``: Update sts command to latest version
* api-change:``dynamodb``: Update dynamodb command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``qldb``: Update qldb command to latest version
* api-change:``health``: Update health command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``ecr``: Update ecr command to latest version
* bugfix:s3: Mute warnings for not restored glacier deep archive objects if --ignore-glacier-warnings option enabled. Fixes `#4039 <https://github.com/aws/aws-cli/issues/4039>`__
* api-change:``macie2``: Update macie2 command to latest version
* api-change:``ecs``: Update ecs command to latest version


2.0.14
======

* api-change:``macie2``: Update macie2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version


2.0.13
======

* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* enhancement:encoding: Add environment variable to set encoding used for text files. fixes `#5086 <https://github.com/aws/aws-cli/issues/5086>`__
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``resourcegroupstaggingapi``: Update resourcegroupstaggingapi command to latest version
* api-change:``workmail``: Update workmail command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``kendra``: Update kendra command to latest version


2.0.12
======

* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``codestar-connections``: Update codestar-connections command to latest version
* api-change:``logs``: Update logs command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``codebuild``: Update codebuild command to latest version


2.0.11
======

* api-change:``support``: Update support command to latest version
* api-change:``servicediscovery``: Update servicediscovery command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``ecr``: Update ecr command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``iotsitewise``: Update iotsitewise command to latest version
* api-change:``waf``: Update waf command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``waf-regional``: Update waf-regional command to latest version
* api-change:``schemas``: Update schemas command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``kinesis-video-archived-media``: Update kinesis-video-archived-media command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``kinesisvideo``: Update kinesisvideo command to latest version


2.0.10
======

* api-change:``dataexchange``: Update dataexchange command to latest version
* bugfix:cloudformation: Fixed an issue with ``cloudformation package`` where virtual style S3 URLs were incorrectly validated for a stack resource's template URL.
* api-change:``rds``: Update rds command to latest version
* api-change:``dms``: Update dms command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``elastic-inference``: Update elastic-inference command to latest version
* api-change:``application-autoscaling``: Update application-autoscaling command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``mediapackage-vod``: Update mediapackage-vod command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``firehose``: Update firehose command to latest version
* api-change:``transfer``: Update transfer command to latest version
* api-change:``ram``: Update ram command to latest version
* api-change:``dlm``: Update dlm command to latest version


2.0.9
=====

* api-change:``route53domains``: Update route53domains command to latest version
* api-change:``emr``: Update emr command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``synthetics``: Update synthetics command to latest version
* api-change:``mediatailor``: Update mediatailor command to latest version
* api-change:``imagebuilder``: Update imagebuilder command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``frauddetector``: Update frauddetector command to latest version
* api-change:``sagemaker-a2i-runtime``: Update sagemaker-a2i-runtime command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``mgh``: Update mgh command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``snowball``: Update snowball command to latest version


2.0.8
=====

* api-change:``apigateway``: Update apigateway command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* bugfix:``logs tail``: Fix bug when we're using --follow parameter. It wasn't picking newly created streams during polling.
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``cloudformation``: Update cloudformation command to latest version
* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``codeguru-reviewer``: Update codeguru-reviewer command to latest version
* api-change:``migrationhub-config``: Update migrationhub-config command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``ecs``: Update ecs command to latest version


2.0.7
=====

* api-change:``personalize-runtime``: Update personalize-runtime command to latest version
* api-change:``wafv2``: Update wafv2 command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``storagegateway``: Update storagegateway command to latest version
* api-change:``rekognition``: Update rekognition command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``mediastore``: Update mediastore command to latest version
* api-change:``organizations``: Update organizations command to latest version
* api-change:``lambda``: Update lambda command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``elasticbeanstalk``: Update elasticbeanstalk command to latest version
* api-change:``elastic-inference``: Update elastic-inference command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``iot``: Update iot command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``iam``: Update iam command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``gamelift``: Update gamelift command to latest version
* api-change:``chime``: Update chime command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``fms``: Update fms command to latest version
* api-change:``medialive``: Update medialive command to latest version


2.0.6
=====

* api-change:``kendra``: Update kendra command to latest version
* api-change:``es``: Update es command to latest version
* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``rds-data``: Update rds-data command to latest version
* enhancement:shorthand: The CLI now no longer allows a key to be spcified twice in a shorthand parameter. For example foo=bar,foo=baz would previously be accepted, with only baz being set, and foo=bar silently being ignored. Now an error will be raised pointing out the issue, and suggesting a fix.
* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``ce``: Update ce command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``xray``: Update xray command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``application-insights``: Update application-insights command to latest version
* api-change:``detective``: Update detective command to latest version
* api-change:``fsx``: Update fsx command to latest version
* api-change:``athena``: Update athena command to latest version
* api-change:``managedblockchain``: Update managedblockchain command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``organizations``: Update organizations command to latest version


2.0.5
=====

* api-change:``mediaconvert``: Update mediaconvert command to latest version
* api-change:``mediaconnect``: Update mediaconnect command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``rds``: Update rds command to latest version
* api-change:``eks``: Update eks command to latest version
* api-change:``personalize``: Update personalize command to latest version
* api-change:``servicecatalog``: Update servicecatalog command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``route53``: Update route53 command to latest version
* api-change:``acm``: Update acm command to latest version


2.0.4
=====

* api-change:``securityhub``: Update securityhub command to latest version
* api-change:``apigatewayv2``: Update apigatewayv2 command to latest version
* api-change:``marketplacecommerceanalytics``: Update marketplacecommerceanalytics command to latest version
* api-change:``lex-models``: Update lex-models command to latest version
* api-change:``iotevents``: Update iotevents command to latest version
* api-change:``s3control``: Update s3control command to latest version
* api-change:``efs``: Update efs command to latest version
* api-change:``ssm``: Update ssm command to latest version
* api-change:``elasticache``: Update elasticache command to latest version
* api-change:``ecs``: Update ecs command to latest version
* api-change:``serverlessrepo``: Update serverlessrepo command to latest version
* api-change:``cognito-idp``: Update cognito-idp command to latest version
* api-change:``medialive``: Update medialive command to latest version
* api-change:``redshift``: Update redshift command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appconfig``: Update appconfig command to latest version
* api-change:``iot``: Update iot command to latest version
* bugfix:cloudformation: Revert pr that added support for comments https://github.com/aws/aws-cli/pull/4873. Comment support also changed from using the 'safe' yaml representer to the 'rt' (round trip) yaml representer. In some cases this causes the `package` command to emit yaml that the CloudFormation service cannot parse, resulting in a service error.
* api-change:``dms``: Update dms command to latest version


2.0.3
=====

* api-change:``eks``: Update eks command to latest version
* api-change:``cloudwatch``: Update cloudwatch command to latest version
* api-change:``comprehendmedical``: Update comprehendmedical command to latest version
* api-change:``opsworkscm``: Update opsworkscm command to latest version
* api-change:``pinpoint``: Update pinpoint command to latest version
* api-change:``guardduty``: Update guardduty command to latest version
* api-change:``robomaker``: Update robomaker command to latest version
* api-change:``signer``: Update signer command to latest version
* api-change:``ec2``: Update ec2 command to latest version
* api-change:``appmesh``: Update appmesh command to latest version


2.0.2
=====

* api-change:``sagemaker``: Update sagemaker command to latest version
* api-change:``transcribe``: Update transcribe command to latest version
* api-change:``elbv2``: Update elbv2 command to latest version
* api-change:``outposts``: Update outposts command to latest version
* api-change:``accessanalyzer``: Update accessanalyzer command to latest version
* api-change:``lightsail``: Update lightsail command to latest version
* api-change:``workdocs``: Update workdocs command to latest version
* api-change:``sagemaker-a2i-runtime``: Update sagemaker-a2i-runtime command to latest version
* api-change:``quicksight``: Update quicksight command to latest version
* api-change:``globalaccelerator``: Update globalaccelerator command to latest version
* api-change:``glue``: Update glue command to latest version
* api-change:``stepfunctions``: Update stepfunctions command to latest version
* api-change:``secretsmanager``: Update secretsmanager command to latest version
* api-change:``codeguruprofiler``: Update codeguruprofiler command to latest version
* api-change:``securityhub``: Update securityhub command to latest version
* bugfix:codecommit: Fix codecommit credential-helper input parsing to allow a trailing newline.
* api-change:``config``: Update config command to latest version
* api-change:``appmesh``: Update appmesh command to latest version
* api-change:``kafka``: Update kafka command to latest version
* api-change:``ec2``: Update ec2 command to latest version


2.0.1
=====

* bugfix:SSO: Fix issue where browser would not open in modern linux distros (`#4839 <https://github.com/aws/aws-cli/issues/4839>`__)
* enhancement:Installer: macOS PKG installer now supports custom install locations.


2.0.0
=====

* breaking-change:aliases: Removed backwards compatibility aliases for improperly generated command names and parameters. See `#3640 <https://github.com/aws/aws-cli/issues/3640>`__.
* breaking-change:cloudformation: Changed the default value of the ``--fail-on-empty-changeset`` flag to false for the cloudformation deploy command. See `#4844 <https://github.com/aws/aws-cli/issues/4844>`__.
* breaking-change:cloudtrail: Removed support for the ``cloudtrail create-subscription`` and ``cloudtrail update-subscription`` command. See `#4819 <https://github.com/aws/aws-cli/issues/4819>`__.
* breaking-change:config: Change precedence of profile env vars to ``AWS_PROFILE``, then ``AWS_DEFAULT_PROFILE``
* breaking-change:config: Removed support for ``api_versions`` configuration. See `#4751 <https://github.com/aws/aws-cli/issues/4751>`__.
* breaking-change:ecr: Removed support for the ``ecr get-login`` command in favor of ``ecr get-login-password``. See `#4886 <https://github.com/aws/aws-cli/issues/4886>`__.
* breaking-change:endpoints: Removed support for STS regional endpoint configuration. STS commands will now use the regional endpoints by default.
* breaking-change:endpoints: Removed S3 regional endpoint configuration. S3 commands will now use the region specific version of the endpoint for the specified region.
* breaking-change:input: Added support for the ``--cli-binary-format`` flag which controls how the CLI formats binary input and output. The AWS CLI now expects binary input provided directly as a parameter to be Base64 encoded by default. See `#4748 <https://github.com/aws/aws-cli/issues/4748>`__.
* breaking-change:output: Changed the default timestamp format to ``iso8601``. See `#3610 <https://github.com/aws/aws-cli/issues/3610>`__.
* breaking-change:output: Renamed the timestamp format ``none`` to ``wire``. See `#3610 <https://github.com/aws/aws-cli/issues/3610>`__.
* breaking-change:paginator: Fixed an issue where pagination parameters provided via ``--cli-input-json`` behaved differently than if provided directly to the CLI. See `#4699 <https://github.com/aws/aws-cli/issues/4699>`__.
* breaking-change:paramfile: Remove support for fetching remote file contents when the parameter begins with ``http://`` or ``https://``. See `#3590 <https://github.com/aws/aws-cli/issues/3590>`__.
* breaking-change:plugins: Deprecated support for legacy pluins. The ``cli_legacy_plugin_path`` configuration must now be set to load legacy plugins. See `#4854 <https://github.com/aws/aws-cli/issues/4854>`__.
* breaking-change:python: Removed support for older Python runtimes. AWS CLI V2 officially supports Python 3.7+. See `#3588 <https://github.com/aws/aws-cli/issues/3588>`__, `#4901 <https://github.com/aws/aws-cli/issues/4901>`__.
* breaking-change:rc: Improved return code consistency and conventions. For more information run aws help return-codes. See `#4890 <https://github.com/aws/aws-cli/issues/4890>`__.
* breaking-change:s3: Removed support for S3 Signature Version 2. All S3 API calls and pre-signed URLs now use Signature Version 4. See `#4764 <https://github.com/aws/aws-cli/issues/4764>`__.
* breaking-change:sms-voice: Removed the ``sms-voice`` service command in favor of ``pinpoint-sms-voice``. See `#4902 <https://github.com/aws/aws-cli/issues/4902>`__.
* breaking-change:retries: Add support for standard mode retries, which lowers the maximum attempts to 3, includes a consistent set of errors to retry, and implements retry quotas which limit the number of unsuccessful retries an SDK can make. See `boto/botocore#1952 <https://github.com/boto/botocore/pull/1952>`__.
* feature:autocomplete: Improved command and parameter autocompletion, including support for service side resource ID autocompletion. See `#3725 <https://github.com/aws/aws-cli/issues/3725>`__.
* feature:config: Add support for the ``AWS_REGION`` env var.  This value has precedence over ``AWS_DEFAULT_REGION`` (`#4934 <https://github.com/aws/aws-cli/issues/4934>`__).
* feature:configure: Added the ``configure list-profiles`` command. See `#3735 <https://github.com/aws/aws-cli/issues/3735>`__.
* feature:configure: Added the ``configure import`` command. This supports importing credentials from a CSV file generated by the AWS Web Console. See `#3720 <https://github.com/aws/aws-cli/issues/3720>`__.
* feature:credentials: Added support for configuring and pulling credentials from AWS Single Sign-On. See `#4627 <https://github.com/aws/aws-cli/issues/4627>`__.
* feature:ddb: Added the high level command ``ddb put`` which provides a simplified interface for putting items into a DynamoDB table. See `#3741 <https://github.com/aws/aws-cli/issues/3741>`__.
* feature:ddb: Added the high level command ``ddb select`` which provides a simplified interface to search a DynamoDB table or index. See `#3740 <https://github.com/aws/aws-cli/issues/3740>`__.
* feature:input: Added support for the ``--cli-auto-prompt`` flag which provides interactive prompts to fill out the parameters for the specified command. See `#4725 <https://github.com/aws/aws-cli/issues/4725>`__.
* feature:input: Added support for ``--cli-input-yaml`` and ``--generate-cli-skeleton yaml-input``. See `#4700 <https://github.com/aws/aws-cli/issues/4700>`__.
* feature:logs: Added the ``logs tail`` command. This tracks new additions to a CloudWatch Logs group printing updates as they become available. See `#3729 <https://github.com/aws/aws-cli/issues/3729>`__.
* feature:output: Added support for the ``--output yaml`` format. See `#3706 <https://github.com/aws/aws-cli/issues/3706>`__.
* feature:output: Added support for sending output to a pager. By default output is now sent to a pager if available. See `#4702 <https://github.com/aws/aws-cli/issues/4702>`__.
* feature:output: Added support for ``--output yaml-stream``. See `#4711 <https://github.com/aws/aws-cli/issues/4711>`__.
* feature:region: Added support for pulling the default region from IMDS when running on an EC2 instance. See `#3680 <https://github.com/aws/aws-cli/issues/3680>`__.
* feature:s3: Added support for the ``--copy-props`` parameter to the high level S3 commands. This new parameter configures how additional metadata, tags, etc. should be copied for S3 to S3 transfers. See `#4840 <https://github.com/aws/aws-cli/issues/4840>`__.
* feature:wizard: Added support for AWS CLI Wizards. See `#3752 <https://github.com/aws/aws-cli/issues/3752>`__.

