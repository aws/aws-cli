# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Maps event patterns to initializer entries.

At runtime, the LazyInitEmitter triggers entries on demand:
before emitting event X, it finds entries whose event patterns
match X, calls each init function at most once (passing the
event_handlers emitter), then proceeds with normal event dispatch.

Entry format:
   (module, fn_name)    call fn(event_handlers)
"""

from __future__ import annotations

import enum


class CommandTableOp(enum.Enum):
    """Valid operation types for MAIN_COMMAND_TABLE_OPS entries."""

    ADD = 'add'
    RENAME = 'rename'


PLUGIN_REGISTRY = {
    'after-call.data-pipeline.GetPipelineDefinition': [
        ('awscli.customizations.datapipeline', 'register_customizations')
    ],
    'after-call.ecs.CreateExpressGatewayService': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'after-call.ecs.DeleteExpressGatewayService': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'after-call.ecs.UpdateExpressGatewayService': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'after-call.iam.CreateVirtualMFADevice': [
        ('awscli.customizations.iamvirtmfa', 'IAMVMFAWrapper')
    ],
    'after-call.s3': [
        ('awscli.customizations.s3errormsg', 'register_s3_error_msg')
    ],
    'before-building-argument-table-parser.ecs.create-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'before-building-argument-table-parser.ecs.delete-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'before-building-argument-table-parser.ecs.update-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'before-building-argument-table-parser.emr.*': [
        ('awscli.customizations.emr.emr', 'emr_initialize')
    ],
    'before-parameter-build.ec2.BundleInstance': [
        ('awscli.customizations.ec2.bundleinstance', 'register_bundleinstance')
    ],
    'before-parameter-build.ec2.CreateNetworkAclEntry': [
        ('awscli.customizations.ec2.protocolarg', 'register_protocol_args')
    ],
    'before-parameter-build.ec2.ReplaceNetworkAclEntry': [
        ('awscli.customizations.ec2.protocolarg', 'register_protocol_args')
    ],
    'before-parameter-build.ec2.RunInstances': [
        ('awscli.customizations.ec2.addcount', 'register_count_events'),
        ('awscli.customizations.ec2.runinstances', 'register_runinstances'),
    ],
    'before-sign.agenttoolkit.*': [
        (
            'awscli.customizations.agenttoolkit',
            'register_agent_toolkit_commands',
        )
    ],
    'building-argument-table': [
        ('awscli.customizations.cliinput', 'register_cli_input_args'),
        ('awscli.customizations.paginate', 'register_pagination'),
        (
            'awscli.customizations.generatecliskeleton',
            'register_generate_cli_skeleton',
        ),
    ],
    'building-argument-table.*': [
        (
            'awscli.customizations.streamingoutputarg',
            'register_streaming_output_arg',
        )
    ],
    'building-argument-table.agent-toolkit.*.name': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.search-skills.query': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.apigateway.create-rest-api': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.apigatewayv2.create-api': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.apigatewayv2.update-api': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.clouddirectory.publish-schema': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.cloudfront.create-distribution': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'building-argument-table.cloudfront.create-invalidation': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'building-argument-table.cloudfront.update-distribution': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'building-argument-table.cloudsearch.define-expression': [
        ('awscli.customizations.cloudsearch', 'initialize')
    ],
    'building-argument-table.cloudsearch.define-index-field': [
        ('awscli.customizations.cloudsearch', 'initialize')
    ],
    'building-argument-table.cloudsearchdomain.search': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.cloudsearchdomain.suggest': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.cloudwatch.put-metric-data': [
        ('awscli.customizations.putmetricdata', 'register_put_metric_data')
    ],
    'building-argument-table.codepipeline.create-custom-action-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.codepipeline.delete-custom-action-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.codepipeline.get-action-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.codepipeline.get-pipeline': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.configservice.put-configuration-recorder': [
        (
            'awscli.customizations.configservice.putconfigurationrecorder',
            'register_modify_put_configuration_recorder',
        )
    ],
    'building-argument-table.controltower.create-landing-zone': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.controltower.update-landing-zone': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.datapipeline.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.datapipeline.activate-pipeline': [
        ('awscli.customizations.datapipeline', 'register_customizations')
    ],
    'building-argument-table.datapipeline.get-pipeline-definition': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.datapipeline.put-pipeline-definition': [
        ('awscli.customizations.datapipeline', 'register_customizations')
    ],
    'building-argument-table.deploy.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.deploy.create-deployment': [
        ('awscli.customizations.codedeploy.codedeploy', 'register_codedeploy')
    ],
    'building-argument-table.deploy.get-application-revision': [
        ('awscli.customizations.codedeploy.codedeploy', 'register_codedeploy')
    ],
    'building-argument-table.deploy.register-application-revision': [
        ('awscli.customizations.codedeploy.codedeploy', 'register_codedeploy')
    ],
    'building-argument-table.ec2.*': [
        ('awscli.customizations.argrename', 'register_arg_renames'),
        ('awscli.customizations.toplevelbool', 'register_bool_params'),
    ],
    'building-argument-table.ec2.authorize-security-group-egress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'building-argument-table.ec2.authorize-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'building-argument-table.ec2.bundle-instance': [
        ('awscli.customizations.ec2.bundleinstance', 'register_bundleinstance')
    ],
    'building-argument-table.ec2.create-image': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.ec2.get-password-data': [
        (
            'awscli.customizations.ec2.decryptpassword',
            'register_ec2_add_priv_launch_key',
        )
    ],
    'building-argument-table.ec2.revoke-security-group-egress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'building-argument-table.ec2.revoke-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'building-argument-table.ec2.run-instances': [
        ('awscli.customizations.ec2.addcount', 'register_count_events'),
        ('awscli.customizations.ec2.runinstances', 'register_runinstances'),
    ],
    'building-argument-table.ecs.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.ecs.create-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'building-argument-table.ecs.delete-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'building-argument-table.ecs.execute-command': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.ecs.update-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'building-argument-table.eks.create-cluster': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.eks.create-nodegroup': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.eks.update-cluster-components-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.eks.update-cluster-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.eks.update-nodegroup-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.elasticache.create-replication-group': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.emr.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.emr.add-tags': [
        ('awscli.customizations.emr.emr', 'emr_initialize')
    ],
    'building-argument-table.emr.list-clusters': [
        ('awscli.customizations.emr.emr', 'emr_initialize')
    ],
    'building-argument-table.gamelift.create-build': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.gamelift.create-script': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.gamelift.update-build': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.gamelift.update-script': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.glue.get-unfiltered-partition-metadata': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.glue.get-unfiltered-partitions-metadata': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.glue.get-unfiltered-table-metadata': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.iam.create-virtual-mfa-device': [
        ('awscli.customizations.iamvirtmfa', 'IAMVMFAWrapper')
    ],
    'building-argument-table.iot.create-certificate-from-csr': [
        ('awscli.customizations.iot', 'register_iot_create_keys_from_csr')
    ],
    'building-argument-table.iot.create-keys-and-certificate': [
        ('awscli.customizations.iot', 'register_iot_create_keys_and_cert_args')
    ],
    'building-argument-table.iotwireless.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.kinesis.list-streams': [
        (
            'awscli.customizations.kinesis',
            'register_kinesis_list_streams_pagination_backcompat',
        )
    ],
    'building-argument-table.kinesisanalytics.add-application-output': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.kinesisanalyticsv2.add-application-output': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lambda.create-function': [
        ('awscli.customizations.awslambda', 'register_lambda_create_function')
    ],
    'building-argument-table.lambda.publish-layer-version': [
        ('awscli.customizations.awslambda', 'register_lambda_create_function')
    ],
    'building-argument-table.lambda.update-function-code': [
        ('awscli.customizations.awslambda', 'register_lambda_create_function')
    ],
    'building-argument-table.lex-models.delete-bot': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.delete-bot-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.delete-intent': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.delete-intent-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.delete-slot-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.delete-slot-type-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.get-export': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.get-intent': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.lex-models.get-slot-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.license-manager.delete-grant': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.license-manager.get-grant': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.license-manager.get-license': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.mgn.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.mturk.list-qualification-types': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.delete-email-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.delete-in-app-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.delete-push-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.delete-sms-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.delete-voice-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-campaign-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-email-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-in-app-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-push-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-segment-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-sms-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.get-voice-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.update-email-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.update-in-app-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.update-push-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.update-sms-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.pinpoint.update-voice-template': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.quicksight.start-asset-bundle-import-job': [
        (
            'awscli.customizations.quicksight',
            'register_quicksight_asset_bundle_customizations',
        )
    ],
    'building-argument-table.rds.add-option-to-option-group': [
        ('awscli.customizations.rds', 'register_rds_modify_split')
    ],
    'building-argument-table.rds.remove-option-from-option-group': [
        ('awscli.customizations.rds', 'register_rds_modify_split')
    ],
    'building-argument-table.rekognition.*': [
        (
            'awscli.customizations.rekognition',
            'register_rekognition_detect_labels',
        )
    ],
    'building-argument-table.rekognition.compare-faces': [
        (
            'awscli.customizations.rekognition',
            'register_rekognition_detect_labels',
        )
    ],
    'building-argument-table.rekognition.create-stream-processor': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.route53.delete-traffic-policy': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.route53.get-traffic-policy': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.route53.update-traffic-policy-comment': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.route53domains.view-billing': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.s3api.select-object-content': [
        ('awscli.customizations.s3events', 'register_event_stream_arg')
    ],
    'building-argument-table.sagemaker.delete-image-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.sagemaker.describe-image-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.sagemaker.list-aliases': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.sagemaker.update-image-version': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.schemas.*': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.ses.send-email': [
        ('awscli.customizations.sessendemail', 'register_ses_send_email')
    ],
    'building-argument-table.sns.subscribe': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.stepfunctions.send-task-success': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.swf.register-activity-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.swf.register-workflow-type': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.translate.import-terminology': [
        (
            'awscli.customizations.translate',
            'register_translate_import_terminology',
        )
    ],
    'building-argument-table.translate.translate-document': [
        (
            'awscli.customizations.translate',
            'register_translate_import_terminology',
        )
    ],
    'building-argument-table.workdocs.create-notification-subscription': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-argument-table.workdocs.describe-users': [
        ('awscli.customizations.argrename', 'register_arg_renames')
    ],
    'building-command-table': [
        ('awscli.customizations.waiters', 'register_add_waiters'),
        ('awscli.alias', 'register_alias_commands'),
    ],
    'building-command-table.agent-toolkit': [
        (
            'awscli.customizations.agenttoolkit',
            'register_agent_toolkit_commands',
        )
    ],
    'building-command-table.bedrock-agent-runtime': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.bedrock-agentcore': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.bedrock-runtime': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.cli-dev': [
        ('awscli.customizations.wizard.commands', 'register_wizard_commands')
    ],
    'building-command-table.cloudformation': [
        ('awscli.customizations.cloudformation', 'initialize')
    ],
    'building-command-table.cloudfront': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'building-command-table.cloudtrail': [
        ('awscli.customizations.cloudtrail', 'initialize')
    ],
    'building-command-table.cloudwatch': [
        ('awscli.customizations.cloudwatch', 'register_rename_otel_commands')
    ],
    'building-command-table.codeartifact': [
        (
            'awscli.customizations.codeartifact',
            'register_codeartifact_commands',
        )
    ],
    'building-command-table.codecommit': [
        ('awscli.customizations.codecommit', 'initialize')
    ],
    'building-command-table.configservice': [
        (
            'awscli.customizations.configservice.subscribe',
            'register_subscribe',
        ),
        (
            'awscli.customizations.configservice.getstatus',
            'register_get_status',
        ),
    ],
    'building-command-table.configure': [
        ('awscli.customizations.wizard.commands', 'register_wizard_commands')
    ],
    'building-command-table.connecthealth': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.datapipeline': [
        ('awscli.customizations.datapipeline', 'register_customizations')
    ],
    'building-command-table.deploy': [
        ('awscli.customizations.codedeploy.codedeploy', 'register_codedeploy')
    ],
    'building-command-table.devops-agent': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.dlm': [
        ('awscli.customizations.dlm.dlm', 'dlm_initialize')
    ],
    'building-command-table.dsql': [
        ('awscli.customizations.dsql', 'register_dsql_customizations')
    ],
    'building-command-table.dynamodb': [
        ('awscli.customizations.wizard.commands', 'register_wizard_commands')
    ],
    'building-command-table.ec2': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.ec2-instance-connect': [
        (
            'awscli.customizations.ec2instanceconnect',
            'register_ec2_instance_connect_commands',
        )
    ],
    'building-command-table.ecr': [
        ('awscli.customizations.ecr', 'register_ecr_commands')
    ],
    'building-command-table.ecr-public': [
        ('awscli.customizations.ecr_public', 'register_ecr_public_commands')
    ],
    'building-command-table.ecs': [
        ('awscli.customizations.ecs', 'initialize')
    ],
    'building-command-table.eks': [
        ('awscli.customizations.eks', 'initialize')
    ],
    'building-command-table.emr': [
        ('awscli.customizations.removals', 'register_removals'),
        ('awscli.customizations.emr.emr', 'emr_initialize'),
    ],
    'building-command-table.emr-containers': [
        ('awscli.customizations.emrcontainers', 'initialize')
    ],
    'building-command-table.events': [
        ('awscli.customizations.wizard.commands', 'register_wizard_commands')
    ],
    'building-command-table.gamelift': [
        ('awscli.customizations.gamelift', 'register_gamelift_commands')
    ],
    'building-command-table.iam': [
        ('awscli.customizations.wizard.commands', 'register_wizard_commands')
    ],
    'building-command-table.iotsitewise': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.kinesis': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.lambda': [
        ('awscli.customizations.removals', 'register_removals'),
        ('awscli.customizations.wizard.commands', 'register_wizard_commands'),
    ],
    'building-command-table.lexv2-runtime': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.lightsail': [
        ('awscli.customizations.lightsail', 'initialize')
    ],
    'building-command-table.logs': [
        ('awscli.customizations.removals', 'register_removals'),
        ('awscli.customizations.logs', 'register_logs_commands'),
    ],
    'building-command-table.main': [
        ('awscli.customizations.s3.s3', 'register_s3_main'),
        ('awscli.customizations.dynamodb.ddb', 'register_ddb'),
        (
            'awscli.customizations.configure.configure',
            'register_configure_cmd',
        ),
        (
            'awscli.customizations.codedeploy.codedeploy',
            'register_rename_codedeploy',
        ),
        (
            'awscli.customizations.configservice.rename_cmd',
            'register_rename_config',
        ),
        ('awscli.customizations.history', 'register_history_commands'),
        ('awscli.customizations.devcommands', 'register_dev_commands'),
        ('awscli.customizations.login', 'register_login_cmds'),
    ],
    'building-command-table.polly': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.qbusiness': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.rds': [
        ('awscli.customizations.rds', 'register_rds_modify_split'),
        ('awscli.customizations.rds', 'register_add_generate_db_auth_token'),
    ],
    'building-command-table.s3_sync': [
        ('awscli.customizations.s3.s3', 'register_s3_sync_strategies')
    ],
    'building-command-table.sagemaker-runtime': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.servicecatalog': [
        (
            'awscli.customizations.servicecatalog',
            'register_servicecatalog_commands',
        )
    ],
    'building-command-table.ses': [
        ('awscli.customizations.removals', 'register_removals')
    ],
    'building-command-table.ssm': [
        ('awscli.customizations.sessionmanager', 'register_ssm_session')
    ],
    'building-command-table.sso': [
        ('awscli.customizations.sso', 'register_sso_commands')
    ],
    'calling-command.cloudsearchdomain': [
        (
            'awscli.customizations.cloudsearchdomain',
            'register_cloudsearchdomain',
        )
    ],
    'calling-command.dynamodb.*': [
        (
            'awscli.customizations.dynamodb.paginatorfix',
            'register_dynamodb_paginator_fix',
        )
    ],
    'calling-command.ec2.describe-snapshots': [
        (
            'awscli.customizations.ec2.paginate',
            'register_ec2_page_size_injector',
        )
    ],
    'calling-command.ec2.describe-volumes': [
        (
            'awscli.customizations.ec2.paginate',
            'register_ec2_page_size_injector',
        )
    ],
    'doc-description': [
        ('awscli.customizations.paginate', 'register_pagination')
    ],
    'doc-description.ec2.authorize-security-group-egress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'doc-description.ec2.authorize-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'doc-description.ec2.revoke-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'doc-description.ec2.revoke-security-groupdoc-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'doc-description.iot-data': [
        ('awscli.customizations.iot_data', 'register_custom_endpoint_note')
    ],
    'doc-examples.*.*': [
        ('awscli.customizations.addexamples', 'register_docs_add_examples')
    ],
    'doc-option.route53.create-hosted-zone.hosted-zone-config': [
        (
            'awscli.customizations.route53',
            'register_create_hosted_zone_doc_fix',
        )
    ],
    'doc-output.datapipeline.get-pipeline-definition': [
        ('awscli.customizations.datapipeline', 'register_customizations')
    ],
    'doc-output.s3api': [
        ('awscli.customizations.s3events', 'register_document_expires_string')
    ],
    'doc-output.s3api.select-object-content': [
        ('awscli.customizations.s3events', 'register_event_stream_arg')
    ],
    'doc-title.kms.create-grant': [
        ('awscli.customizations.kms', 'register_fix_kms_create_grant_docs')
    ],
    'operation-args-parsed.cloudfront.create-distribution': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'operation-args-parsed.cloudfront.create-invalidation': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'operation-args-parsed.cloudfront.update-distribution': [
        ('awscli.customizations.cloudfront', 'register')
    ],
    'operation-args-parsed.cloudwatch.put-metric-data': [
        ('awscli.customizations.putmetricdata', 'register_put_metric_data')
    ],
    'operation-args-parsed.ec2.authorize-security-group-egress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'operation-args-parsed.ec2.authorize-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'operation-args-parsed.ec2.bundle-instance': [
        ('awscli.customizations.ec2.bundleinstance', 'register_bundleinstance')
    ],
    'operation-args-parsed.ec2.revoke-security-group-egress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'operation-args-parsed.ec2.revoke-security-group-ingress': [
        ('awscli.customizations.ec2.secgroupsimplify', 'register_secgroup')
    ],
    'operation-args-parsed.ec2.run-instances': [
        ('awscli.customizations.ec2.runinstances', 'register_runinstances')
    ],
    'operation-args-parsed.ecs.create-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'operation-args-parsed.ecs.delete-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'operation-args-parsed.ecs.update-express-gateway-service': [
        (
            'awscli.customizations.ecs.monitormutatinggatewayservice',
            'register_monitor_mutating_gateway_service',
        )
    ],
    'operation-args-parsed.kinesis.list-streams': [
        (
            'awscli.customizations.kinesis',
            'register_kinesis_list_streams_pagination_backcompat',
        )
    ],
    'operation-args-parsed.ses.send-email': [
        ('awscli.customizations.sessendemail', 'register_ses_send_email')
    ],
    'process-cli-arg': [
        ('awscli.argprocess', 'register_param_shorthand_parser')
    ],
    'process-cli-arg.lambda.update-function-code': [
        ('awscli.customizations.awslambda', 'register_lambda_create_function')
    ],
    'session-initialized': [
        ('awscli.paramfile', 'register_init_uri_param_handler'),
        (
            'awscli.customizations.binaryformat',
            'register_init_binary_formatter',
        ),
        ('awscli.clidriver', 'register_no_pager_handler'),
        ('awscli.customizations.assumerole', 'register_assume_role_provider'),
        ('awscli.customizations.timestampformat', 'register_timestamp_format'),
        ('awscli.customizations.history', 'register_history_mode'),
        ('awscli.customizations.sso', 'register_sso_commands'),
    ],
    'top-level-args-parsed': [
        ('awscli.customizations.globalargs', 'register_parse_global_args'),
        ('awscli.customizations.cloudfront', 'register'),
    ],
}

# Declarative model of changes made to the command table by plugins
# that register against building-command-table.main.
#
# At runtime, plugins listed in building-command-table.main above
# are NOT called as init functions. Instead, these pre-computed
# operations are applied directly, allowing added commands to be
# wrapped in LazyCommand and deferring heavy module imports until
# the command is actually invoked.
#
# Entry formats:
#   (CommandTableOp.RENAME, old_name, new_name)
#   (CommandTableOp.ADD, cmd_name, cmd_module, cmd_class)

MAIN_COMMAND_TABLE_OPS: list[
    tuple[CommandTableOp, str, str] | tuple[CommandTableOp, str, str, str]
] = [
    (CommandTableOp.RENAME, 's3', 's3api'),
    (CommandTableOp.ADD, 's3', 'awscli.customizations.s3.s3', 'S3'),
    (CommandTableOp.ADD, 'ddb', 'awscli.customizations.dynamodb.ddb', 'DDB'),
    (
        CommandTableOp.ADD,
        'configure',
        'awscli.customizations.configure.configure',
        'ConfigureCommand',
    ),
    (CommandTableOp.RENAME, 'codedeploy', 'deploy'),
    (CommandTableOp.RENAME, 'config', 'configservice'),
    (
        CommandTableOp.ADD,
        'history',
        'awscli.customizations.history',
        'HistoryCommand',
    ),
    (
        CommandTableOp.ADD,
        'cli-dev',
        'awscli.customizations.devcommands',
        'CLIDevCommand',
    ),
    (
        CommandTableOp.ADD,
        'login',
        'awscli.customizations.login.login',
        'LoginCommand',
    ),
    (
        CommandTableOp.ADD,
        'logout',
        'awscli.customizations.login.logout',
        'LogoutCommand',
    ),
    (
        CommandTableOp.RENAME,
        'agenttoolkit',
        'agent-toolkit',
    ),
]
