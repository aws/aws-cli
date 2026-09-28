# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest
from botocore.model import OperationModel

from awscli.clidriver import create_clidriver

# Command parameters that *exactly* match a top level (global) option.  The CLI
# parses global options in an earlier stage than command parameters, so the
# global always wins and these parameters are completely unreachable.  Renaming
# them is backwards incompatible, so the fix is deferred to a future major
# version (see CLI-9380).  Keyed by ``(command_path, arg_name)`` so that a new
# exact shadow in any other command still fails this test.
KNOWN_EXACT_SHADOWS = frozenset(
    {
        ('sagemaker.wait.image-version-created', 'version'),
        ('sagemaker.wait.image-version-deleted', 'version'),
    }
)

# ``(command_path, arg_name, builtin)`` triples where one option name is a
# prefix of the other.  The CLI resolves global options in a separate, earlier
# parse stage (``MainArgParser``) that only knows about globals.  Because of
# argparse prefix matching, an abbreviation a customer types for one of these
# command parameters (e.g. ``--regio`` for ``--region-name``) is silently
# captured by the prefixing global (``--region``) before the command parser
# ever sees it, with no error or warning.  These are pre-existing collisions
# that predate this audit; renaming is backwards incompatible and deferred to a
# future major version (see CLI-9380).  They are keyed by full command path so
# that the test fails on *every* newly introduced collision -- including a new
# command that reuses an already-known parameter name, or a new global -- each
# of which must be reviewed and explicitly added here.
KNOWN_PREFIX_COLLISIONS = frozenset(
    {
        ('account.disable-region', 'region-name', 'region'),
        ('account.enable-region', 'region-name', 'region'),
        ('account.get-region-opt-status', 'region-name', 'region'),
        ('account.list-regions', 'region-opt-status-contains', 'region'),
        (
            'apigateway.create-domain-name',
            'regional-certificate-arn',
            'region',
        ),
        (
            'apigateway.create-domain-name',
            'regional-certificate-name',
            'region',
        ),
        ('apigatewayv2.export-api', 'output-type', 'output'),
        (
            'appconfig.create-hosted-configuration-version',
            'version-label',
            'version',
        ),
        ('appconfig.delete-extension', 'version-number', 'version'),
        (
            'appconfig.delete-hosted-configuration-version',
            'version-number',
            'version',
        ),
        ('appconfig.get-extension', 'version-number', 'version'),
        (
            'appconfig.get-hosted-configuration-version',
            'version-number',
            'version',
        ),
        (
            'appconfig.list-hosted-configuration-versions',
            'version-label',
            'version',
        ),
        ('appconfig.update-extension', 'version-number', 'version'),
        ('appsync.create-graphql-api', 'query-depth-limit', 'query'),
        ('appsync.update-graphql-api', 'query-depth-limit', 'query'),
        ('arc-region-switch.create-plan', 'regions', 'region'),
        ('artifact.export-compliance-inquiry', 'query-identifiers', 'query'),
        (
            'artifact.put-compliance-inquiry-feedback',
            'query-identifier',
            'query',
        ),
        ('athena.batch-get-query-execution', 'query-execution-ids', 'query'),
        ('athena.create-named-query', 'query-string', 'query'),
        ('athena.create-prepared-statement', 'query-statement', 'query'),
        ('athena.get-query-execution', 'query-execution-id', 'query'),
        ('athena.get-query-results', 'query-execution-id', 'query'),
        ('athena.get-query-results', 'query-result-type', 'query'),
        ('athena.get-query-runtime-statistics', 'query-execution-id', 'query'),
        ('athena.start-query-execution', 'query-execution-context', 'query'),
        ('athena.start-query-execution', 'query-string', 'query'),
        ('athena.stop-query-execution', 'query-execution-id', 'query'),
        ('athena.update-named-query', 'query-string', 'query'),
        ('athena.update-prepared-statement', 'query-statement', 'query'),
        ('auditmanager.create-assessment-report', 'query-statement', 'query'),
        ('b2bi.create-partnership', 'profile-id', 'profile'),
        (
            'b2bi.create-starter-mapping-template',
            'output-sample-location',
            'output',
        ),
        ('b2bi.create-transformer', 'output-conversion', 'output'),
        ('b2bi.delete-profile', 'profile-id', 'profile'),
        ('b2bi.generate-mapping', 'output-file-content', 'output'),
        ('b2bi.get-profile', 'profile-id', 'profile'),
        ('b2bi.list-partnerships', 'profile-id', 'profile'),
        ('b2bi.start-transformer-job', 'output-location', 'output'),
        ('b2bi.update-profile', 'profile-id', 'profile'),
        ('b2bi.update-transformer', 'output-conversion', 'output'),
        ('backup.get-backup-plan', 'version-id', 'version'),
        (
            'bedrock-agent-runtime.generate-query',
            'query-generation-input',
            'query',
        ),
        (
            'bedrock-agent-runtime.get-document-content',
            'output-format',
            'output',
        ),
        (
            'bedrock-agentcore-control.create-online-evaluation-config',
            'output-config',
            'output',
        ),
        (
            'bedrock-agentcore-control.delete-browser-profile',
            'profile-id',
            'profile',
        ),
        (
            'bedrock-agentcore-control.get-browser-profile',
            'profile-id',
            'profile',
        ),
        (
            'bedrock-agentcore-control.get-configuration-bundle-version',
            'version-id',
            'version',
        ),
        (
            'bedrock-agentcore-control.update-online-evaluation-config',
            'output-config',
            'output',
        ),
        (
            'bedrock-agentcore.save-browser-session-profile',
            'profile-identifier',
            'profile',
        ),
        (
            'bedrock-agentcore.start-batch-evaluation',
            'output-config',
            'output',
        ),
        (
            'bedrock-agentcore.start-browser-session',
            'profile-configuration',
            'profile',
        ),
        (
            'bedrock-data-automation-runtime.invoke-data-automation',
            'output-configuration',
            'output',
        ),
        (
            'bedrock-data-automation-runtime.invoke-data-automation-async',
            'output-configuration',
            'output',
        ),
        (
            'bedrock-data-automation.invoke-blueprint-optimization-async',
            'output-configuration',
            'output',
        ),
        (
            'bedrock-data-automation.invoke-data-automation-library-ingestion-job',
            'output-configuration',
            'output',
        ),
        ('bedrock-runtime.apply-guardrail', 'output-scope', 'output'),
        ('bedrock-runtime.converse', 'output-config', 'output'),
        ('bedrock-runtime.start-async-invoke', 'output-data-config', 'output'),
        (
            'bedrock.create-advanced-prompt-optimization-job',
            'output-config',
            'output',
        ),
        (
            'bedrock.create-automated-reasoning-policy-test-case',
            'query-content',
            'query',
        ),
        ('bedrock.create-evaluation-job', 'output-data-config', 'output'),
        (
            'bedrock.create-model-customization-job',
            'output-data-config',
            'output',
        ),
        (
            'bedrock.create-model-invocation-job',
            'output-data-config',
            'output',
        ),
        (
            'bedrock.update-automated-reasoning-policy-test-case',
            'query-content',
            'query',
        ),
        ('braket.create-job', 'output-data-config', 'output'),
        ('braket.create-quantum-task', 'output-s3-bucket', 'output'),
        ('braket.create-quantum-task', 'output-s3-key-prefix', 'output'),
        ('cleanrooms.create-collaboration', 'query-log-status', 'query'),
        ('cleanrooms.create-membership', 'query-log-status', 'query'),
        (
            'cleanrooms.start-protected-query',
            'query-compute-payer-account-id',
            'query',
        ),
        ('cleanrooms.update-membership', 'query-log-status', 'query'),
        ('cleanroomsml.cancel-trained-model', 'version-identifier', 'version'),
        (
            'cleanroomsml.create-configured-audience-model',
            'output-config',
            'output',
        ),
        (
            'cleanroomsml.delete-trained-model-output',
            'version-identifier',
            'version',
        ),
        (
            'cleanroomsml.get-collaboration-trained-model',
            'version-identifier',
            'version',
        ),
        ('cleanroomsml.get-trained-model', 'version-identifier', 'version'),
        (
            'cleanroomsml.start-trained-model-export-job',
            'output-configuration',
            'output',
        ),
        (
            'cleanroomsml.start-trained-model-inference-job',
            'output-configuration',
            'output',
        ),
        (
            'cleanroomsml.update-configured-audience-model',
            'output-config',
            'output',
        ),
        ('cloudformation.activate-type', 'version-bump', 'version'),
        ('cloudformation.create-stack-instances', 'regions', 'region'),
        ('cloudformation.delete-stack-instances', 'regions', 'region'),
        ('cloudformation.deregister-type', 'version-id', 'version'),
        ('cloudformation.describe-type', 'version-id', 'version'),
        ('cloudformation.package', 'output-template-file', 'output'),
        ('cloudformation.set-type-default-version', 'version-id', 'version'),
        ('cloudformation.test-type', 'version-id', 'version'),
        ('cloudformation.update-stack-instances', 'regions', 'region'),
        ('cloudformation.update-stack-set', 'regions', 'region'),
        ('cloudsearchdomain.search', 'query-options', 'query'),
        ('cloudsearchdomain.search', 'query-parser', 'query'),
        ('cloudtrail.cancel-query', 'query-id', 'query'),
        ('cloudtrail.describe-query', 'query-alias', 'query'),
        ('cloudtrail.describe-query', 'query-id', 'query'),
        ('cloudtrail.get-query-results', 'query-id', 'query'),
        ('cloudtrail.list-queries', 'query-status', 'query'),
        (
            'cloudtrail.start-dashboard-refresh',
            'query-parameter-values',
            'query',
        ),
        ('cloudtrail.start-query', 'query-alias', 'query'),
        ('cloudtrail.start-query', 'query-parameters', 'query'),
        ('cloudtrail.start-query', 'query-statement', 'query'),
        ('cloudwatch.get-metric-widget-image', 'output-format', 'output'),
        ('cloudwatch.put-log-alarm', 'query-results-to-alarm', 'query'),
        ('cloudwatch.put-log-alarm', 'query-results-to-evaluate', 'query'),
        ('cloudwatch.put-metric-stream', 'output-format', 'output'),
        ('cloudwatchomni.create-alert', 'profile-id', 'profile'),
        ('cloudwatchomni.delete-access-profile', 'profile-id', 'profile'),
        ('cloudwatchomni.get-access-profile', 'profile-id', 'profile'),
        ('cloudwatchomni.get-telemetry-query-results', 'query-id', 'query'),
        ('cloudwatchomni.start-telemetry-query', 'query-string', 'query'),
        ('cloudwatchomni.stop-telemetry-query', 'query-id', 'query'),
        ('cloudwatchomni.update-access-profile', 'profile-id', 'profile'),
        ('cloudwatchomni.update-alert', 'profile-id', 'profile'),
        ('codeartifact.copy-package-versions', 'version-revisions', 'version'),
        ('codeartifact.copy-package-versions', 'versions', 'version'),
        ('codeartifact.delete-package-versions', 'versions', 'version'),
        (
            'codeartifact.dispose-package-versions',
            'version-revisions',
            'version',
        ),
        ('codeartifact.dispose-package-versions', 'versions', 'version'),
        (
            'codeartifact.update-package-versions-status',
            'version-revisions',
            'version',
        ),
        ('codeartifact.update-package-versions-status', 'versions', 'version'),
        ('codebuild.start-build', 'debug-session-enabled', 'debug'),
        ('codebuild.start-build-batch', 'debug-session-enabled', 'debug'),
        ('codeguruprofiler.post-agent-profile', 'profile-token', 'profile'),
        (
            'codepipeline.create-custom-action-type',
            'output-artifact-details',
            'output',
        ),
        ('codepipeline.list-action-types', 'region-filter', 'region'),
        ('codepipeline.list-rule-types', 'region-filter', 'region'),
        ('codepipeline.poll-for-jobs', 'query-param', 'query'),
        ('codepipeline.put-job-success-result', 'output-variables', 'output'),
        ('cognito-idp.create-user-pool-replica', 'region-name', 'region'),
        ('cognito-idp.delete-user-pool-replica', 'region-name', 'region'),
        ('cognito-idp.update-user-pool-replica', 'region-name', 'region'),
        (
            'comprehend.create-document-classifier',
            'output-data-config',
            'output',
        ),
        ('comprehend.create-document-classifier', 'version-name', 'version'),
        ('comprehend.create-entity-recognizer', 'version-name', 'version'),
        ('comprehend.import-model', 'version-name', 'version'),
        (
            'comprehend.start-document-classification-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-dominant-language-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-entities-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-events-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-key-phrases-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-pii-entities-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-sentiment-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-targeted-sentiment-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehend.start-topics-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehendmedical.start-entities-detection-v2-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehendmedical.start-icd10-cm-inference-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehendmedical.start-phi-detection-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehendmedical.start-rx-norm-inference-job',
            'output-data-config',
            'output',
        ),
        (
            'comprehendmedical.start-snomedct-inference-job',
            'output-data-config',
            'output',
        ),
        ('configservice.delete-stored-query', 'query-name', 'query'),
        ('configservice.get-stored-query', 'query-name', 'query'),
        ('configure.import', 'profile-prefix', 'profile'),
        ('connect.create-view-version', 'version-description', 'version'),
        (
            'connect.list-realtime-contact-analysis-segments-v2',
            'output-type',
            'output',
        ),
        (
            'connectcampaignsv2.put-profile-outbound-request-batch',
            'profile-outbound-requests',
            'profile',
        ),
        (
            'connecthealth.start-patient-insights-job',
            'output-data-config',
            'output',
        ),
        ('customer-profiles.add-profile-key', 'profile-id', 'profile'),
        (
            'customer-profiles.batch-get-calculated-attribute-for-profile',
            'profile-ids',
            'profile',
        ),
        ('customer-profiles.batch-get-profile', 'profile-ids', 'profile'),
        ('customer-profiles.create-profile', 'profile-type', 'profile'),
        ('customer-profiles.delete-profile', 'profile-id', 'profile'),
        ('customer-profiles.delete-profile-key', 'profile-id', 'profile'),
        ('customer-profiles.delete-profile-object', 'profile-id', 'profile'),
        (
            'customer-profiles.delete-profile-object',
            'profile-object-unique-key',
            'profile',
        ),
        (
            'customer-profiles.get-calculated-attribute-for-profile',
            'profile-id',
            'profile',
        ),
        (
            'customer-profiles.get-profile-history-record',
            'profile-id',
            'profile',
        ),
        (
            'customer-profiles.get-profile-recommendations',
            'profile-id',
            'profile',
        ),
        ('customer-profiles.get-segment-membership', 'profile-ids', 'profile'),
        (
            'customer-profiles.list-calculated-attributes-for-profile',
            'profile-id',
            'profile',
        ),
        (
            'customer-profiles.list-profile-history-records',
            'profile-id',
            'profile',
        ),
        ('customer-profiles.list-profile-objects', 'profile-id', 'profile'),
        ('customer-profiles.list-workflows', 'query-end-date', 'query'),
        ('customer-profiles.list-workflows', 'query-start-date', 'query'),
        (
            'customer-profiles.merge-profiles',
            'profile-ids-to-be-merged',
            'profile',
        ),
        ('customer-profiles.update-profile', 'profile-id', 'profile'),
        ('customer-profiles.update-profile', 'profile-type', 'profile'),
        ('databrew.create-profile-job', 'output-location', 'output'),
        ('databrew.create-recipe-job', 'outputs', 'output'),
        ('databrew.update-profile-job', 'output-location', 'output'),
        ('databrew.update-recipe-job', 'outputs', 'output'),
        ('dataexchange.send-api-asset', 'query-string-parameters', 'query'),
        (
            'datazone.put-environment-blueprint-configuration',
            'regional-parameters',
            'region',
        ),
        ('devicefarm.update-device-instance', 'profile-arn', 'profile'),
        ('ds.add-region', 'region-name', 'region'),
        ('ds.describe-regions', 'region-name', 'region'),
        ('ds.describe-update-directory', 'region-name', 'region'),
        ('dynamodb.list-global-tables', 'region-name', 'region'),
        ('dynamodb.query', 'query-filter', 'query'),
        ('ec2.create-capacity-manager-data-export', 'output-format', 'output'),
        ('ec2.create-launch-template', 'version-description', 'version'),
        (
            'ec2.create-launch-template-version',
            'version-description',
            'version',
        ),
        ('ec2.delete-launch-template-versions', 'versions', 'version'),
        ('ec2.describe-launch-template-versions', 'versions', 'version'),
        ('ec2.describe-regions', 'region-names', 'region'),
        ('ec2.get-spot-placement-scores', 'region-names', 'region'),
        ('ecs.register-container-instance', 'version-info', 'version'),
        ('eks.describe-cluster-versions', 'version-status', 'version'),
        (
            'elasticache.increase-node-groups-in-global-replication-group',
            'regional-configurations',
            'region',
        ),
        ('elasticbeanstalk.compose-environments', 'version-labels', 'version'),
        (
            'elasticbeanstalk.create-application-version',
            'version-label',
            'version',
        ),
        ('elasticbeanstalk.create-environment', 'version-label', 'version'),
        (
            'elasticbeanstalk.delete-application-version',
            'version-label',
            'version',
        ),
        (
            'elasticbeanstalk.describe-application-versions',
            'version-labels',
            'version',
        ),
        ('elasticbeanstalk.describe-environments', 'version-label', 'version'),
        ('elasticbeanstalk.describe-events', 'version-label', 'version'),
        (
            'elasticbeanstalk.update-application-version',
            'version-label',
            'version',
        ),
        ('elasticbeanstalk.update-environment', 'version-label', 'version'),
        (
            'elasticbeanstalk.wait.environment-exists',
            'version-label',
            'version',
        ),
        (
            'elasticbeanstalk.wait.environment-terminated',
            'version-label',
            'version',
        ),
        (
            'elasticbeanstalk.wait.environment-updated',
            'version-label',
            'version',
        ),
        ('elementalinference.associate-feed', 'outputs', 'output'),
        ('elementalinference.create-feed', 'outputs', 'output'),
        ('elementalinference.update-feed', 'outputs', 'output'),
        ('emr.create-persistent-app-ui', 'profiler-type', 'profile'),
        ('emr.start-notebook-execution', 'output-notebook-format', 'output'),
        (
            'emr.start-notebook-execution',
            'output-notebook-s3-location',
            'output',
        ),
        (
            'entityresolution.create-id-mapping-workflow',
            'output-source-config',
            'output',
        ),
        (
            'entityresolution.create-matching-workflow',
            'output-source-config',
            'output',
        ),
        (
            'entityresolution.start-id-mapping-job',
            'output-source-config',
            'output',
        ),
        (
            'entityresolution.update-id-mapping-workflow',
            'output-source-config',
            'output',
        ),
        (
            'entityresolution.update-matching-workflow',
            'output-source-config',
            'output',
        ),
        ('frauddetector.create-batch-import-job', 'output-path', 'output'),
        ('frauddetector.create-batch-prediction-job', 'output-path', 'output'),
        ('frauddetector.put-external-model', 'output-configuration', 'output'),
        (
            'gamelift.create-container-group-definition',
            'version-description',
            'version',
        ),
        (
            'gamelift.delete-container-group-definition',
            'version-count-to-retain',
            'version',
        ),
        (
            'gamelift.delete-container-group-definition',
            'version-number',
            'version',
        ),
        (
            'gamelift.describe-container-group-definition',
            'version-number',
            'version',
        ),
        (
            'gamelift.update-container-group-definition',
            'version-description',
            'version',
        ),
        (
            'gameliftstreams.export-stream-session-files',
            'output-uri',
            'output',
        ),
        ('geo-maps.get-sprites', 'color-scheme', 'color'),
        ('geo-maps.get-static-map', 'color-scheme', 'color'),
        ('geo-maps.get-style-descriptor', 'color-scheme', 'color'),
        ('geo-places.autocomplete', 'query-text', 'query'),
        ('geo-places.geocode', 'query-components', 'query'),
        ('geo-places.geocode', 'query-text', 'query'),
        ('geo-places.reverse-geocode', 'query-position', 'query'),
        ('geo-places.reverse-geocode', 'query-radius', 'query'),
        ('geo-places.search-nearby', 'query-position', 'query'),
        ('geo-places.search-nearby', 'query-radius', 'query'),
        ('geo-places.search-text', 'query-id', 'query'),
        ('geo-places.search-text', 'query-text', 'query'),
        ('geo-places.suggest', 'query-text', 'query'),
        ('glue.batch-delete-table-version', 'version-ids', 'version'),
        ('glue.batch-get-partition', 'query-session-context', 'query'),
        ('glue.delete-schema-versions', 'versions', 'version'),
        ('glue.delete-table-version', 'version-id', 'version'),
        ('glue.get-data-quality-model', 'profile-id', 'profile'),
        ('glue.get-data-quality-model-result', 'profile-id', 'profile'),
        ('glue.get-partitions', 'query-as-of-time', 'query'),
        ('glue.get-table', 'query-as-of-time', 'query'),
        ('glue.get-table-version', 'version-id', 'version'),
        ('glue.get-tables', 'query-as-of-time', 'query'),
        (
            'glue.get-unfiltered-partition-metadata',
            'query-session-context',
            'query',
        ),
        (
            'glue.get-unfiltered-partitions-metadata',
            'query-session-context',
            'query',
        ),
        (
            'glue.get-unfiltered-table-metadata',
            'query-session-context',
            'query',
        ),
        (
            'glue.list-data-quality-statistic-annotations',
            'profile-id',
            'profile',
        ),
        ('glue.list-data-quality-statistics', 'profile-id', 'profile'),
        ('glue.put-data-quality-profile-annotation', 'profile-id', 'profile'),
        ('glue.start-export-labels-task-run', 'output-s3-path', 'output'),
        (
            'glue.start-ml-labeling-set-generation-task-run',
            'output-s3-path',
            'output',
        ),
        ('glue.update-table', 'version-id', 'version'),
        ('groundstation.describe-contact-version', 'version-id', 'version'),
        ('groundstation.wait.contact-updated', 'version-id', 'version'),
        (
            'healthlake.create-data-transformation-profile',
            'profile-description',
            'profile',
        ),
        (
            'healthlake.create-data-transformation-profile',
            'profile-name',
            'profile',
        ),
        (
            'healthlake.create-fhir-datastore',
            'profile-configuration',
            'profile',
        ),
        (
            'healthlake.delete-data-transformation-profile',
            'profile-id',
            'profile',
        ),
        (
            'healthlake.get-data-transformation-profile',
            'profile-id',
            'profile',
        ),
        (
            'healthlake.get-data-transformation-profile',
            'profile-version',
            'profile',
        ),
        (
            'healthlake.list-data-transformation-profile-versions',
            'profile-id',
            'profile',
        ),
        (
            'healthlake.publish-data-transformation-profile',
            'profile-id',
            'profile',
        ),
        (
            'healthlake.restore-fhir-datastore',
            'profile-configuration',
            'profile',
        ),
        (
            'healthlake.start-data-transformation-job',
            'output-data-config',
            'output',
        ),
        ('healthlake.start-data-transformation-job', 'profile-id', 'profile'),
        ('healthlake.start-fhir-export-job', 'output-data-config', 'output'),
        ('healthlake.start-fhir-import-job', 'profile-id', 'profile'),
        (
            'healthlake.update-data-transformation-profile',
            'profile-id',
            'profile',
        ),
        (
            'healthlake.update-data-transformation-profile',
            'profile-mapping',
            'profile',
        ),
        (
            'healthlake.update-fhir-datastore',
            'profile-configuration',
            'profile',
        ),
        ('healthlake.update-profile-with-agent', 'profile-id', 'profile'),
        ('iam.delete-policy-version', 'version-id', 'version'),
        ('iam.get-policy-version', 'version-id', 'version'),
        ('iam.set-default-policy-version', 'version-id', 'version'),
        ('identitystore.create-user', 'profile-url', 'profile'),
        ('inspector-scan.scan-sbom', 'output-format', 'output'),
        ('internetmonitor.get-query-results', 'query-id', 'query'),
        ('internetmonitor.get-query-status', 'query-id', 'query'),
        ('internetmonitor.start-query', 'query-type', 'query'),
        ('internetmonitor.stop-query', 'query-id', 'query'),
        ('iot.associate-sbom-with-package-version', 'version-name', 'version'),
        ('iot.create-dynamic-thing-group', 'query-string', 'query'),
        ('iot.create-dynamic-thing-group', 'query-version', 'query'),
        ('iot.create-fleet-metric', 'query-string', 'query'),
        ('iot.create-fleet-metric', 'query-version', 'query'),
        ('iot.create-package-version', 'version-name', 'version'),
        ('iot.delete-package-version', 'version-name', 'version'),
        ('iot.delete-provisioning-template-version', 'version-id', 'version'),
        (
            'iot.describe-provisioning-template-version',
            'version-id',
            'version',
        ),
        (
            'iot.disassociate-sbom-from-package-version',
            'version-name',
            'version',
        ),
        ('iot.get-buckets-aggregation', 'query-string', 'query'),
        ('iot.get-buckets-aggregation', 'query-version', 'query'),
        ('iot.get-cardinality', 'query-string', 'query'),
        ('iot.get-cardinality', 'query-version', 'query'),
        ('iot.get-package-version', 'version-name', 'version'),
        ('iot.get-percentiles', 'query-string', 'query'),
        ('iot.get-percentiles', 'query-version', 'query'),
        ('iot.get-statistics', 'query-string', 'query'),
        ('iot.get-statistics', 'query-version', 'query'),
        ('iot.list-sbom-validation-results', 'version-name', 'version'),
        ('iot.search-index', 'query-string', 'query'),
        ('iot.search-index', 'query-version', 'query'),
        ('iot.update-dynamic-thing-group', 'query-string', 'query'),
        ('iot.update-dynamic-thing-group', 'query-version', 'query'),
        ('iot.update-fleet-metric', 'query-string', 'query'),
        ('iot.update-fleet-metric', 'query-version', 'query'),
        (
            'iot.update-package-configuration',
            'version-update-by-jobs-config',
            'version',
        ),
        ('iot.update-package-version', 'version-name', 'version'),
        ('iotsitewise.cancel-query', 'query-id', 'query'),
        ('iotsitewise.describe-query', 'query-id', 'query'),
        ('iotsitewise.execute-query', 'query-statement', 'query'),
        ('iotsitewise.get-query-results', 'query-id', 'query'),
        ('iotsitewise.start-query', 'query-statement', 'query'),
        ('iotsitewise.start-search', 'query-statement', 'query'),
        ('iottwinmaker.execute-query', 'query-statement', 'query'),
        (
            'iotwireless.start-bulk-associate-wireless-device-with-multicast-group',
            'query-string',
            'query',
        ),
        (
            'iotwireless.start-bulk-disassociate-wireless-device-from-multicast-group',
            'query-string',
            'query',
        ),
        ('kendra.create-featured-results-set', 'query-texts', 'query'),
        ('kendra.get-query-suggestions', 'query-text', 'query'),
        ('kendra.query', 'query-result-type-filter', 'query'),
        ('kendra.query', 'query-text', 'query'),
        ('kendra.retrieve', 'query-text', 'query'),
        ('kendra.submit-feedback', 'query-id', 'query'),
        ('kendra.update-featured-results-set', 'query-texts', 'query'),
        (
            'kendra.update-query-suggestions-config',
            'query-log-look-back-window-in-days',
            'query',
        ),
        ('kinesisanalytics.create-application', 'outputs', 'output'),
        ('kinesisanalytics.delete-application-output', 'output-id', 'output'),
        (
            'kinesisanalyticsv2.delete-application-output',
            'output-id',
            'output',
        ),
        ('lakeformation.get-query-state', 'query-id', 'query'),
        ('lakeformation.get-query-statistics', 'query-id', 'query'),
        ('lakeformation.get-table-objects', 'query-as-of-time', 'query'),
        (
            'lakeformation.get-temporary-glue-table-credentials',
            'query-session-context',
            'query',
        ),
        ('lakeformation.get-work-unit-results', 'query-id', 'query'),
        ('lakeformation.get-work-units', 'query-id', 'query'),
        (
            'lakeformation.start-query-planning',
            'query-planning-context',
            'query',
        ),
        ('lakeformation.start-query-planning', 'query-string', 'query'),
        ('lambda.add-layer-version-permission', 'version-number', 'version'),
        ('lambda.delete-layer-version', 'version-number', 'version'),
        ('lambda.get-layer-version', 'version-number', 'version'),
        ('lambda.get-layer-version-policy', 'version-number', 'version'),
        (
            'lambda.remove-layer-version-permission',
            'version-number',
            'version',
        ),
        ('lex-models.get-bot', 'version-or-alias', 'version'),
        ('lex-models.put-intent', 'output-contexts', 'output'),
        ('lexv2-models.create-intent', 'output-contexts', 'output'),
        ('lexv2-models.update-intent', 'output-contexts', 'output'),
        ('lightsail.update-bucket', 'versioning', 'version'),
        ('location.start-job', 'output-options', 'output'),
        ('logs.create-lookup-table', 'query-id', 'query'),
        ('logs.create-scheduled-query', 'query-language', 'query'),
        ('logs.create-scheduled-query', 'query-string', 'query'),
        ('logs.delete-query-definition', 'query-definition-id', 'query'),
        ('logs.describe-queries', 'query-language', 'query'),
        (
            'logs.describe-query-definitions',
            'query-definition-name-prefix',
            'query',
        ),
        ('logs.describe-query-definitions', 'query-language', 'query'),
        ('logs.get-query-results', 'query-id', 'query'),
        ('logs.list-log-groups-for-query', 'query-id', 'query'),
        ('logs.put-delivery-destination', 'output-format', 'output'),
        ('logs.put-query-definition', 'query-definition-id', 'query'),
        ('logs.put-query-definition', 'query-language', 'query'),
        ('logs.put-query-definition', 'query-string', 'query'),
        ('logs.start-query', 'query-language', 'query'),
        ('logs.start-query', 'query-string', 'query'),
        ('logs.stop-query', 'query-id', 'query'),
        ('logs.update-lookup-table', 'query-id', 'query'),
        ('logs.update-scheduled-query', 'query-language', 'query'),
        ('logs.update-scheduled-query', 'query-string', 'query'),
        ('machinelearning.create-batch-prediction', 'output-uri', 'output'),
        ('mediaconnect.add-bridge-outputs', 'outputs', 'output'),
        ('mediaconnect.add-flow-outputs', 'outputs', 'output'),
        ('mediaconnect.create-bridge', 'outputs', 'output'),
        ('mediaconnect.create-flow', 'outputs', 'output'),
        ('mediaconnect.create-router-input', 'region-name', 'region'),
        (
            'mediaconnect.create-router-network-interface',
            'region-name',
            'region',
        ),
        ('mediaconnect.create-router-output', 'region-name', 'region'),
        ('mediaconnect.remove-bridge-output', 'output-name', 'output'),
        ('mediaconnect.remove-flow-output', 'output-arn', 'output'),
        ('mediaconnect.update-bridge-output', 'output-name', 'output'),
        ('mediaconnect.update-flow-output', 'output-arn', 'output'),
        ('mediaconnect.update-flow-output', 'output-status', 'output'),
        (
            'mediapackagev2.create-channel',
            'output-header-configuration',
            'output',
        ),
        ('mediapackagev2.create-channel', 'output-locking-mode', 'output'),
        (
            'mediapackagev2.update-channel',
            'output-header-configuration',
            'output',
        ),
        ('mediatailor.create-channel', 'outputs', 'output'),
        ('mediatailor.update-channel', 'outputs', 'output'),
        ('medical-imaging.get-image-set', 'version-id', 'version'),
        ('medical-imaging.get-image-set-metadata', 'version-id', 'version'),
        ('medical-imaging.start-dicom-import-job', 'output-s3-uri', 'output'),
        ('migrationhuborchestrator.create-workflow-step', 'outputs', 'output'),
        ('migrationhuborchestrator.update-workflow-step', 'outputs', 'output'),
        (
            'migrationhubstrategy.start-recommendation-report-generation',
            'output-format',
            'output',
        ),
        ('mpa.delete-inactive-approval-team-version', 'version-id', 'version'),
        ('mwaa.invoke-rest-api', 'query-parameters', 'query'),
        ('neptune-graph.cancel-query', 'query-id', 'query'),
        ('neptune-graph.execute-query', 'query-string', 'query'),
        ('neptune-graph.execute-query', 'query-timeout-milliseconds', 'query'),
        ('neptune-graph.get-query', 'query-id', 'query'),
        ('neptunedata.cancel-gremlin-query', 'query-id', 'query'),
        ('neptunedata.cancel-open-cypher-query', 'query-id', 'query'),
        ('neptunedata.get-gremlin-query-status', 'query-id', 'query'),
        ('neptunedata.get-open-cypher-query-status', 'query-id', 'query'),
        (
            'networkflowmonitor.get-query-results-monitor-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.get-query-results-workload-insights-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.get-query-results-workload-insights-top-contributors-data',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.get-query-status-monitor-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.get-query-status-workload-insights-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.get-query-status-workload-insights-top-contributors-data',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.stop-query-monitor-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.stop-query-workload-insights-top-contributors',
            'query-id',
            'query',
        ),
        (
            'networkflowmonitor.stop-query-workload-insights-top-contributors-data',
            'query-id',
            'query',
        ),
        ('notifications.create-event-rule', 'regions', 'region'),
        ('notifications.update-event-rule', 'regions', 'region'),
        ('observabilityadmin.start-telemetry-evaluation', 'regions', 'region'),
        (
            'observabilityadmin.start-telemetry-evaluation-for-organization',
            'regions',
            'region',
        ),
        ('omics.create-annotation-store', 'version-name', 'version'),
        ('omics.create-annotation-store-version', 'version-name', 'version'),
        (
            'omics.create-annotation-store-version',
            'version-options',
            'version',
        ),
        ('omics.create-workflow-version', 'version-name', 'version'),
        ('omics.delete-annotation-store-versions', 'versions', 'version'),
        ('omics.delete-workflow-version', 'version-name', 'version'),
        ('omics.get-annotation-store-version', 'version-name', 'version'),
        ('omics.get-workflow-version', 'version-name', 'version'),
        ('omics.start-annotation-import-job', 'version-name', 'version'),
        ('omics.start-run', 'output-uri', 'output'),
        ('omics.update-annotation-store-version', 'version-name', 'version'),
        ('omics.update-workflow-version', 'version-name', 'version'),
        (
            'omics.wait.annotation-store-version-created',
            'version-name',
            'version',
        ),
        (
            'omics.wait.annotation-store-version-deleted',
            'version-name',
            'version',
        ),
        ('omics.wait.workflow-version-active', 'version-name', 'version'),
        (
            'pinpoint-sms-voice-v2.describe-registration-field-values',
            'version-number',
            'version',
        ),
        (
            'pinpoint-sms-voice-v2.describe-registration-versions',
            'version-numbers',
            'version',
        ),
        ('polly.start-speech-synthesis-task', 'output-format', 'output'),
        (
            'polly.start-speech-synthesis-task',
            'output-s3-bucket-name',
            'output',
        ),
        (
            'polly.start-speech-synthesis-task',
            'output-s3-key-prefix',
            'output',
        ),
        ('polly.synthesize-speech', 'output-format', 'output'),
        ('pricing.list-price-lists', 'region-code', 'region'),
        (
            'proton.notify-resource-deployment-status-change',
            'outputs',
            'output',
        ),
        ('qbusiness.get-document-content', 'output-format', 'output'),
        ('qbusiness.search-relevant-content', 'query-text', 'query'),
        ('qconnect.activate-message-template', 'version-number', 'version'),
        ('qconnect.deactivate-message-template', 'version-number', 'version'),
        ('qconnect.delete-ai-agent-version', 'version-number', 'version'),
        ('qconnect.delete-ai-guardrail-version', 'version-number', 'version'),
        ('qconnect.delete-ai-prompt-version', 'version-number', 'version'),
        ('qconnect.query-assistant', 'query-condition', 'query'),
        ('qconnect.query-assistant', 'query-input-data', 'query'),
        ('qconnect.query-assistant', 'query-text', 'query'),
        ('quicksight.create-dashboard', 'version-description', 'version'),
        ('quicksight.create-limits-profile', 'profile-name', 'profile'),
        ('quicksight.create-template', 'version-description', 'version'),
        ('quicksight.create-theme', 'version-description', 'version'),
        ('quicksight.delete-dashboard', 'version-number', 'version'),
        ('quicksight.delete-limits-profile', 'profile-id', 'profile'),
        ('quicksight.delete-template', 'version-number', 'version'),
        ('quicksight.delete-theme', 'version-number', 'version'),
        ('quicksight.describe-brand', 'version-id', 'version'),
        ('quicksight.describe-dashboard', 'version-number', 'version'),
        (
            'quicksight.describe-dashboard-definition',
            'version-number',
            'version',
        ),
        ('quicksight.describe-limits-profile', 'profile-id', 'profile'),
        ('quicksight.describe-template', 'version-number', 'version'),
        (
            'quicksight.describe-template-definition',
            'version-number',
            'version',
        ),
        ('quicksight.describe-theme', 'version-number', 'version'),
        ('quicksight.predict-qa-results', 'query-text', 'query'),
        ('quicksight.update-brand-published-version', 'version-id', 'version'),
        ('quicksight.update-dashboard', 'version-description', 'version'),
        (
            'quicksight.update-dashboard-published-version',
            'version-number',
            'version',
        ),
        ('quicksight.update-limits-profile', 'profile-id', 'profile'),
        ('quicksight.update-limits-profile', 'profile-name', 'profile'),
        ('quicksight.update-template', 'version-description', 'version'),
        ('quicksight.update-theme', 'version-description', 'version'),
        ('rds.create-db-proxy', 'debug-logging', 'debug'),
        ('rds.describe-source-regions', 'region-name', 'region'),
        ('rds.modify-db-proxy', 'debug-logging', 'debug'),
        ('rekognition.copy-project-version', 'output-config', 'output'),
        ('rekognition.copy-project-version', 'version-name', 'version'),
        ('rekognition.create-project-version', 'output-config', 'output'),
        (
            'rekognition.create-project-version',
            'version-description',
            'version',
        ),
        ('rekognition.create-project-version', 'version-name', 'version'),
        (
            'rekognition.create-stream-processor',
            'regions-of-interest',
            'region',
        ),
        ('rekognition.describe-project-versions', 'version-names', 'version'),
        ('rekognition.start-media-analysis-job', 'output-config', 'output'),
        (
            'rekognition.update-stream-processor',
            'regions-of-interest-for-update',
            'region',
        ),
        (
            'rekognition.wait.project-version-running',
            'version-names',
            'version',
        ),
        (
            'rekognition.wait.project-version-training-completed',
            'version-names',
            'version',
        ),
        ('resiliencehub.publish-app-version', 'version-name', 'version'),
        ('resiliencehubv2.create-service', 'regions', 'region'),
        ('resiliencehubv2.list-dependencies', 'query-range-end-time', 'query'),
        (
            'resiliencehubv2.list-dependencies',
            'query-range-granularity',
            'query',
        ),
        (
            'resiliencehubv2.list-dependencies',
            'query-range-start-time',
            'query',
        ),
        ('resiliencehubv2.update-service', 'regions', 'region'),
        (
            'resource-explorer-2.create-resource-explorer-setup',
            'region-list',
            'region',
        ),
        (
            'resource-explorer-2.delete-resource-explorer-setup',
            'region-list',
            'region',
        ),
        ('resource-explorer-2.list-indexes', 'regions', 'region'),
        ('resource-explorer-2.list-service-indexes', 'regions', 'region'),
        ('resource-explorer-2.search', 'query-string', 'query'),
        (
            'resourcegroupstaggingapi.get-compliance-summary',
            'region-filters',
            'region',
        ),
        ('rolesanywhere.delete-attribute-mapping', 'profile-id', 'profile'),
        ('rolesanywhere.delete-profile', 'profile-id', 'profile'),
        ('rolesanywhere.disable-profile', 'profile-id', 'profile'),
        ('rolesanywhere.enable-profile', 'profile-id', 'profile'),
        ('rolesanywhere.get-profile', 'profile-id', 'profile'),
        ('rolesanywhere.put-attribute-mapping', 'profile-id', 'profile'),
        ('rolesanywhere.update-profile', 'profile-id', 'profile'),
        ('route53.update-health-check', 'regions', 'region'),
        ('route53globalresolver.create-global-resolver', 'regions', 'region'),
        ('route53globalresolver.update-global-resolver', 'regions', 'region'),
        ('route53profiles.associate-profile', 'profile-id', 'profile'),
        (
            'route53profiles.associate-resource-to-profile',
            'profile-id',
            'profile',
        ),
        ('route53profiles.delete-profile', 'profile-id', 'profile'),
        ('route53profiles.disassociate-profile', 'profile-id', 'profile'),
        (
            'route53profiles.disassociate-resource-from-profile',
            'profile-id',
            'profile',
        ),
        ('route53profiles.get-profile', 'profile-id', 'profile'),
        (
            'route53profiles.get-profile-association',
            'profile-association-id',
            'profile',
        ),
        (
            'route53profiles.get-profile-resource-association',
            'profile-resource-association-id',
            'profile',
        ),
        ('route53profiles.list-profile-associations', 'profile-id', 'profile'),
        (
            'route53profiles.list-profile-resource-associations',
            'profile-id',
            'profile',
        ),
        (
            'route53profiles.update-profile-resource-association',
            'profile-resource-association-id',
            'profile',
        ),
        ('s3api.delete-object', 'version-id', 'version'),
        ('s3api.delete-object-annotation', 'version-id', 'version'),
        ('s3api.delete-object-tagging', 'version-id', 'version'),
        ('s3api.get-object', 'version-id', 'version'),
        ('s3api.get-object-acl', 'version-id', 'version'),
        ('s3api.get-object-annotation', 'version-id', 'version'),
        ('s3api.get-object-attributes', 'version-id', 'version'),
        ('s3api.get-object-legal-hold', 'version-id', 'version'),
        ('s3api.get-object-retention', 'version-id', 'version'),
        ('s3api.get-object-tagging', 'version-id', 'version'),
        ('s3api.head-object', 'version-id', 'version'),
        ('s3api.list-object-annotations', 'version-id', 'version'),
        ('s3api.list-object-versions', 'version-id-marker', 'version'),
        ('s3api.put-bucket-versioning', 'versioning-configuration', 'version'),
        ('s3api.put-object-acl', 'version-id', 'version'),
        ('s3api.put-object-annotation', 'version-id', 'version'),
        ('s3api.put-object-legal-hold', 'version-id', 'version'),
        ('s3api.put-object-retention', 'version-id', 'version'),
        ('s3api.put-object-tagging', 'version-id', 'version'),
        ('s3api.restore-object', 'version-id', 'version'),
        ('s3api.select-object-content', 'output-serialization', 'output'),
        ('s3api.update-object-encryption', 'version-id', 'version'),
        ('s3api.wait.object-exists', 'version-id', 'version'),
        ('s3api.wait.object-not-exists', 'version-id', 'version'),
        ('s3api.write-get-object-response', 'version-id', 'version'),
        (
            's3control.put-bucket-versioning',
            'versioning-configuration',
            'version',
        ),
        ('s3tables.delete-table', 'version-token', 'version'),
        (
            's3tables.delete-table-bucket-replication',
            'version-token',
            'version',
        ),
        ('s3tables.delete-table-replication', 'version-token', 'version'),
        ('s3tables.put-table-bucket-replication', 'version-token', 'version'),
        ('s3tables.put-table-replication', 'version-token', 'version'),
        ('s3tables.rename-table', 'version-token', 'version'),
        (
            's3tables.update-table-metadata-location',
            'version-token',
            'version',
        ),
        ('s3vectors.query-vectors', 'query-vector', 'query'),
        (
            'sagemaker-geospatial.export-earth-observation-job',
            'output-config',
            'output',
        ),
        (
            'sagemaker-geospatial.export-vector-enrichment-job',
            'output-config',
            'output',
        ),
        ('sagemaker-geospatial.get-tile', 'output-data-type', 'output'),
        ('sagemaker-geospatial.get-tile', 'output-format', 'output'),
        ('sagemaker.create-ai-benchmark-job', 'output-config', 'output'),
        ('sagemaker.create-ai-recommendation-job', 'output-config', 'output'),
        ('sagemaker.create-auto-ml-job', 'output-data-config', 'output'),
        ('sagemaker.create-auto-ml-job-v2', 'output-data-config', 'output'),
        ('sagemaker.create-compilation-job', 'output-config', 'output'),
        ('sagemaker.create-device-fleet', 'output-config', 'output'),
        ('sagemaker.create-edge-packaging-job', 'output-config', 'output'),
        ('sagemaker.create-flow-definition', 'output-config', 'output'),
        (
            'sagemaker.create-inference-recommendations-job',
            'output-config',
            'output',
        ),
        ('sagemaker.create-labeling-job', 'output-config', 'output'),
        ('sagemaker.create-model-card-export-job', 'output-config', 'output'),
        ('sagemaker.create-optimization-job', 'output-config', 'output'),
        ('sagemaker.create-training-job', 'debug-hook-config', 'debug'),
        (
            'sagemaker.create-training-job',
            'debug-rule-configurations',
            'debug',
        ),
        ('sagemaker.create-training-job', 'output-data-config', 'output'),
        ('sagemaker.create-training-job', 'profiler-config', 'profile'),
        (
            'sagemaker.create-training-job',
            'profiler-rule-configurations',
            'profile',
        ),
        ('sagemaker.create-trial-component', 'output-artifacts', 'output'),
        ('sagemaker.delete-image-version', 'version-number', 'version'),
        ('sagemaker.describe-image-version', 'version-number', 'version'),
        ('sagemaker.list-aliases', 'version-number', 'version'),
        (
            'sagemaker.send-pipeline-execution-step-success',
            'output-parameters',
            'output',
        ),
        ('sagemaker.update-device-fleet', 'output-config', 'output'),
        ('sagemaker.update-image-version', 'version-number', 'version'),
        ('sagemaker.update-training-job', 'profiler-config', 'profile'),
        (
            'sagemaker.update-training-job',
            'profiler-rule-configurations',
            'profile',
        ),
        ('sagemaker.update-trial-component', 'output-artifacts', 'output'),
        (
            'sagemaker.update-trial-component',
            'output-artifacts-to-remove',
            'output',
        ),
        ('secretsmanager.get-secret-value', 'version-id', 'version'),
        ('secretsmanager.get-secret-value', 'version-stage', 'version'),
        ('secretsmanager.put-secret-value', 'version-stages', 'version'),
        (
            'secretsmanager.update-secret-version-stage',
            'version-stage',
            'version',
        ),
        ('securityhub.create-aggregator-v2', 'region-linking-mode', 'region'),
        (
            'securityhub.create-finding-aggregator',
            'region-linking-mode',
            'region',
        ),
        ('securityhub.create-finding-aggregator', 'regions', 'region'),
        ('securityhub.update-aggregator-v2', 'region-linking-mode', 'region'),
        (
            'securityhub.update-finding-aggregator',
            'region-linking-mode',
            'region',
        ),
        ('securityhub.update-finding-aggregator', 'regions', 'region'),
        ('securitylake.delete-data-lake', 'regions', 'region'),
        ('securitylake.list-data-lake-exceptions', 'regions', 'region'),
        ('securitylake.list-data-lakes', 'regions', 'region'),
        ('securitylake.list-log-sources', 'regions', 'region'),
        (
            'servicecatalog.get-provisioned-product-outputs',
            'output-keys',
            'output',
        ),
        (
            'servicecatalog.notify-provision-product-engine-workflow-result',
            'outputs',
            'output',
        ),
        (
            'servicecatalog.notify-update-provisioned-product-engine-workflow-result',
            'outputs',
            'output',
        ),
        ('servicediscovery.discover-instances', 'query-parameters', 'query'),
        (
            'signer-data.get-revocation-status',
            'profile-version-arn',
            'profile',
        ),
        ('signer.add-profile-permission', 'profile-name', 'profile'),
        ('signer.add-profile-permission', 'profile-version', 'profile'),
        ('signer.cancel-signing-profile', 'profile-name', 'profile'),
        ('signer.get-revocation-status', 'profile-version-arn', 'profile'),
        ('signer.get-signing-profile', 'profile-name', 'profile'),
        ('signer.get-signing-profile', 'profile-owner', 'profile'),
        ('signer.list-profile-permissions', 'profile-name', 'profile'),
        ('signer.put-signing-profile', 'profile-name', 'profile'),
        ('signer.remove-profile-permission', 'profile-name', 'profile'),
        ('signer.revoke-signing-profile', 'profile-name', 'profile'),
        ('signer.revoke-signing-profile', 'profile-version', 'profile'),
        ('signer.sign-payload', 'profile-name', 'profile'),
        ('signer.sign-payload', 'profile-owner', 'profile'),
        ('signer.start-signing-job', 'profile-name', 'profile'),
        ('signer.start-signing-job', 'profile-owner', 'profile'),
        ('ssm-incidents.create-replication-set', 'regions', 'region'),
        ('ssm.create-association', 'output-location', 'output'),
        ('ssm.create-document', 'version-name', 'version'),
        ('ssm.delete-document', 'version-name', 'version'),
        ('ssm.describe-document', 'version-name', 'version'),
        ('ssm.get-document', 'version-name', 'version'),
        ('ssm.send-command', 'output-s3-bucket-name', 'output'),
        ('ssm.send-command', 'output-s3-key-prefix', 'output'),
        ('ssm.send-command', 'output-s3-region', 'output'),
        ('ssm.update-association', 'output-location', 'output'),
        ('ssm.update-document', 'version-name', 'version'),
        ('sso-admin.add-region', 'region-name', 'region'),
        ('sso-admin.describe-region', 'region-name', 'region'),
        ('sso-admin.remove-region', 'region-name', 'region'),
        (
            'stepfunctions.create-state-machine',
            'version-description',
            'version',
        ),
        (
            'stepfunctions.update-state-machine',
            'version-description',
            'version',
        ),
        ('textract.create-adapter-version', 'output-config', 'output'),
        ('textract.start-document-analysis', 'output-config', 'output'),
        ('textract.start-document-text-detection', 'output-config', 'output'),
        ('textract.start-expense-analysis', 'output-config', 'output'),
        ('textract.start-lending-analysis', 'output-config', 'output'),
        ('timestream-query.cancel-query', 'query-id', 'query'),
        ('timestream-query.create-scheduled-query', 'query-string', 'query'),
        (
            'timestream-query.execute-scheduled-query',
            'query-insights',
            'query',
        ),
        ('timestream-query.prepare-query', 'query-string', 'query'),
        ('timestream-query.query', 'query-insights', 'query'),
        ('timestream-query.query', 'query-string', 'query'),
        ('timestream-query.update-account-settings', 'query-compute', 'query'),
        (
            'timestream-query.update-account-settings',
            'query-pricing-model',
            'query',
        ),
        (
            'transcribe.start-call-analytics-job',
            'output-encryption-kms-key-id',
            'output',
        ),
        ('transcribe.start-call-analytics-job', 'output-location', 'output'),
        (
            'transcribe.start-medical-scribe-job',
            'output-bucket-name',
            'output',
        ),
        (
            'transcribe.start-medical-scribe-job',
            'output-encryption-kms-key-id',
            'output',
        ),
        (
            'transcribe.start-medical-transcription-job',
            'output-bucket-name',
            'output',
        ),
        (
            'transcribe.start-medical-transcription-job',
            'output-encryption-kms-key-id',
            'output',
        ),
        ('transcribe.start-medical-transcription-job', 'output-key', 'output'),
        ('transcribe.start-transcription-job', 'output-bucket-name', 'output'),
        (
            'transcribe.start-transcription-job',
            'output-encryption-kms-key-id',
            'output',
        ),
        ('transcribe.start-transcription-job', 'output-key', 'output'),
        ('transfer.create-profile', 'profile-type', 'profile'),
        ('transfer.delete-profile', 'profile-id', 'profile'),
        ('transfer.describe-profile', 'profile-id', 'profile'),
        ('transfer.list-profiles', 'profile-type', 'profile'),
        (
            'transfer.start-directory-listing',
            'output-directory-path',
            'output',
        ),
        ('transfer.update-profile', 'profile-id', 'profile'),
        (
            'translate.start-text-translation-job',
            'output-data-config',
            'output',
        ),
        (
            'trustedadvisor.list-organization-recommendation-resources',
            'region-code',
            'region',
        ),
        (
            'trustedadvisor.list-recommendation-resources',
            'region-code',
            'region',
        ),
        (
            'voice-id.start-fraudster-registration-job',
            'output-data-config',
            'output',
        ),
        (
            'voice-id.start-speaker-enrollment-job',
            'output-data-config',
            'output',
        ),
        ('wafv2.describe-managed-rule-group', 'version-name', 'version'),
        (
            'wafv2.put-managed-rule-set-versions',
            'versions-to-publish',
            'version',
        ),
        (
            'wafv2.update-managed-rule-set-version-expiry-date',
            'version-to-expire',
            'version',
        ),
        ('wellarchitected.associate-profiles', 'profile-arns', 'profile'),
        ('wellarchitected.create-agent-context', 'profile-arn', 'profile'),
        ('wellarchitected.create-agent-goal', 'profile-arn', 'profile'),
        ('wellarchitected.create-profile', 'profile-description', 'profile'),
        ('wellarchitected.create-profile', 'profile-name', 'profile'),
        ('wellarchitected.create-profile', 'profile-questions', 'profile'),
        ('wellarchitected.create-profile-share', 'profile-arn', 'profile'),
        ('wellarchitected.create-workload', 'profile-arns', 'profile'),
        ('wellarchitected.delete-agent-context', 'profile-arn', 'profile'),
        ('wellarchitected.delete-agent-goal', 'profile-arn', 'profile'),
        ('wellarchitected.delete-agent-profile', 'profile-arn', 'profile'),
        ('wellarchitected.delete-profile', 'profile-arn', 'profile'),
        ('wellarchitected.delete-profile-share', 'profile-arn', 'profile'),
        ('wellarchitected.disassociate-profiles', 'profile-arns', 'profile'),
        ('wellarchitected.get-agent-context', 'profile-arn', 'profile'),
        ('wellarchitected.get-agent-goal', 'profile-arn', 'profile'),
        ('wellarchitected.get-agent-profile', 'profile-arn', 'profile'),
        (
            'wellarchitected.get-agent-recommendation-generation',
            'profile-arn',
            'profile',
        ),
        ('wellarchitected.get-profile', 'profile-arn', 'profile'),
        ('wellarchitected.get-profile', 'profile-version', 'profile'),
        ('wellarchitected.list-agent-contexts', 'profile-arn', 'profile'),
        ('wellarchitected.list-agent-goals', 'profile-arn', 'profile'),
        (
            'wellarchitected.list-agent-recommendation-generations',
            'profile-arn',
            'profile',
        ),
        (
            'wellarchitected.list-agent-recommendations',
            'profile-arn',
            'profile',
        ),
        ('wellarchitected.list-profile-shares', 'profile-arn', 'profile'),
        ('wellarchitected.list-profiles', 'profile-name-prefix', 'profile'),
        ('wellarchitected.list-profiles', 'profile-owner-type', 'profile'),
        (
            'wellarchitected.list-share-invitations',
            'profile-name-prefix',
            'profile',
        ),
        (
            'wellarchitected.start-agent-recommendation-generation',
            'profile-arn',
            'profile',
        ),
        ('wellarchitected.update-agent-context', 'profile-arn', 'profile'),
        ('wellarchitected.update-agent-goal', 'profile-arn', 'profile'),
        ('wellarchitected.update-agent-profile', 'profile-arn', 'profile'),
        ('wellarchitected.update-profile', 'profile-arn', 'profile'),
        ('wellarchitected.update-profile', 'profile-description', 'profile'),
        ('wellarchitected.update-profile', 'profile-questions', 'profile'),
        ('wellarchitected.upgrade-profile-version', 'profile-arn', 'profile'),
        ('wisdom.query-assistant', 'query-text', 'query'),
        ('workdocs.abort-document-version-upload', 'version-id', 'version'),
        ('workdocs.create-comment', 'version-id', 'version'),
        ('workdocs.create-custom-metadata', 'version-id', 'version'),
        ('workdocs.delete-comment', 'version-id', 'version'),
        ('workdocs.delete-custom-metadata', 'version-id', 'version'),
        ('workdocs.delete-document-version', 'version-id', 'version'),
        ('workdocs.describe-comments', 'version-id', 'version'),
        ('workdocs.get-document-version', 'version-id', 'version'),
        ('workdocs.search-resources', 'query-scopes', 'query'),
        ('workdocs.search-resources', 'query-text', 'query'),
        ('workdocs.update-document-version', 'version-id', 'version'),
        ('workdocs.update-document-version', 'version-status', 'version'),
    }
)


def _walk_command_tree(command_path, command_obj):
    """Yield ``(command_path, arg_table, obj)`` for a command and every
    descendant.

    The CLI command tree has a variable depth.  Services expose operations
    (depth 2), but customizations inject deeper commands as well -- for example
    ``aws <service> wait <waiter>`` (depth 3) -- and some of those commands are
    not backed by an ``OperationModel``.  We recurse the entire tree and audit
    every command that has arguments, regardless of depth or type, so nothing
    is left unaudited.
    """
    help_command = command_obj.create_help_command()
    arg_table = getattr(help_command, 'arg_table', None) or {}
    yield command_path, arg_table, getattr(help_command, 'obj', None)
    command_table = getattr(help_command, 'command_table', None) or {}
    for sub_name, sub_command in command_table.items():
        # ``help`` is a synthetic command present in every command table; it
        # isn't a real subcommand and recursing into it adds no coverage.
        if sub_name == 'help':
            continue
        yield from _walk_command_tree(
            f'{command_path}.{sub_name}', sub_command
        )


def _generate_command_tests():
    driver = create_clidriver()
    help_command = driver.create_help_command()
    builtins = set(help_command.arg_table.keys())
    for command_name, command_obj in list(help_command.command_table.items()):
        if command_name == 'help':
            continue
        for command_path, arg_table, obj in _walk_command_tree(
            command_name, command_obj
        ):
            if not arg_table:
                continue
            if isinstance(obj, OperationModel):
                service_name = obj.service_model.service_name
                operation_name = obj.name
            else:
                service_name = command_path.split('.', 1)[0]
                operation_name = ''
            yield (
                command_path,
                service_name,
                operation_name,
                arg_table,
                builtins,
            )


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "command_path, service_name, operation_name, arg_table, builtins",
    _generate_command_tests(),
)
def test_no_shadowed_builtins(
    command_path,
    service_name,
    operation_name,
    arg_table,
    builtins,
    record_property,
):
    """Verify no command params are shadowed or prefixed by a builtin.

    The CLI resolves global (top level) options in an earlier parse stage than
    command parameters, and argparse expands unambiguous prefixes of option
    names.  Together this means a command parameter can be silently shadowed by
    a global in two ways, with no error shown to the customer:

    * **Exact shadow** -- a command defines an option with the same name as a
      global (e.g. ``--version``).  The global always wins, so the command's
      option can never be reached.

    * **Prefix capture** -- one option name is a prefix of the other, so an
      abbreviation the customer types is captured by the global before the
      command parser sees it.  This is bidirectional:

        - A command parameter that is a prefix of a global (``--end`` /
          ``--endpoint-url``) is itself an abbreviation of that global and is
          eaten entirely.
        - A global that is a prefix of a command parameter (``--region`` /
          ``--region-name``) captures every abbreviation up to the divergence
          point, so ``--regio`` silently sets the global instead of the
          command parameter.

    The reverse direction also guards against introducing a new global that
    shadows existing command parameters (e.g. adding a global ``--version``
    when commands already define a ``--version-*`` parameter).

    We walk the entire command tree (every depth, including customization
    injected commands that are not backed by an ``OperationModel``) and
    aggregate all failures into a single assertion.  Pre-existing collisions
    are grandfathered by full command path via the allowlists above, so the
    test fails on every newly introduced collision.
    """
    errors = []
    for arg_name in arg_table:
        for builtin in builtins:
            if arg_name == builtin:
                if (command_path, arg_name) in KNOWN_EXACT_SHADOWS:
                    continue
                errors.append(
                    'Exact shadow of a top level option: '
                    f'{command_path} (--{arg_name})'
                )
            elif arg_name.startswith(builtin) or builtin.startswith(arg_name):
                if (
                    command_path,
                    arg_name,
                    builtin,
                ) in KNOWN_PREFIX_COLLISIONS:
                    continue
                errors.append(
                    'Prefix collision with a top level option: '
                    f'{command_path} --{arg_name} vs builtin --{builtin}'
                )
    if errors:
        # Store the service and operation in PyTest custom properties.
        record_property('aws_service', service_name)
        record_property('aws_operation', operation_name)
        raise AssertionError('\n' + '\n'.join(errors))
