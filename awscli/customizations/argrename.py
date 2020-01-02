# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
"""

from awscli.customizations import utils


ARGUMENT_RENAMES = {
    # Mapping of original arg to renamed arg.
    # The key is <service>.<operation>.argname
    # The first part of the key is used for event registration
    # so if you wanted to rename something for an entire service you
    # could say 'ec2.*.dry-run': 'renamed-arg-name', or if you wanted
    # to rename across all services you could say '*.*.dry-run': 'new-name'.
    'ec2.create-image.no-no-reboot': 'reboot',
    'ec2.*.no-egress': 'ingress',
    'ec2.*.no-disable-api-termination': 'enable-api-termination',
    'opsworks.*.region': 'stack-region',
    'elastictranscoder.*.output': 'job-output',
    'swf.register-activity-type.version': 'activity-version',
    'swf.register-workflow-type.version': 'workflow-version',
    'datapipeline.*.query': 'objects-query',
    'datapipeline.get-pipeline-definition.version': 'pipeline-version',
    'emr.*.job-flow-ids': 'cluster-ids',
    'emr.*.job-flow-id': 'cluster-id',
    'cloudsearchdomain.search.query': 'search-query',
    'cloudsearchdomain.suggest.query': 'suggest-query',
    'sns.subscribe.endpoint': 'notification-endpoint',
    'deploy.*.s-3-location': 's3-location',
    'deploy.*.ec-2-tag-filters': 'ec2-tag-filters',
    'codepipeline.get-pipeline.version': 'pipeline-version',
    'codepipeline.create-custom-action-type.version': 'action-version',
    'codepipeline.delete-custom-action-type.version': 'action-version',
    'kinesisanalytics.add-application-output.output': 'application-output',
    'kinesisanalyticsv2.add-application-output.output': 'application-output',
    'route53.delete-traffic-policy.version': 'traffic-policy-version',
    'route53.get-traffic-policy.version': 'traffic-policy-version',
    'route53.update-traffic-policy-comment.version': 'traffic-policy-version',
    'gamelift.create-build.version': 'build-version',
    'gamelift.update-build.version': 'build-version',
    'gamelift.create-script.version': 'script-version',
    'gamelift.update-script.version': 'script-version',
    'route53domains.view-billing.start': 'start-time',
    'route53domains.view-billing.end': 'end-time',
    'apigateway.create-rest-api.version': 'api-version',
    'apigatewayv2.create-api.version': 'api-version',
    'apigatewayv2.update-api.version': 'api-version',
    'pinpoint.get-campaign-version.version': 'campaign-version',
    'pinpoint.get-segment-version.version': 'segment-version',
    'pinpoint.delete-email-template.version': 'template-version',
    'pinpoint.delete-push-template.version': 'template-version',
    'pinpoint.delete-sms-template.version': 'template-version',
    'pinpoint.delete-voice-template.version': 'template-version',
    'pinpoint.get-email-template.version': 'template-version',
    'pinpoint.get-push-template.version': 'template-version',
    'pinpoint.get-sms-template.version': 'template-version',
    'pinpoint.get-voice-template.version': 'template-version',
    'pinpoint.update-email-template.version': 'template-version',
    'pinpoint.update-push-template.version': 'template-version',
    'pinpoint.update-sms-template.version': 'template-version',
    'pinpoint.update-voice-template.version': 'template-version',
    'stepfunctions.send-task-success.output': 'task-output',
    'clouddirectory.publish-schema.version': 'schema-version',
    'mturk.list-qualification-types.query': 'types-query',
    'workdocs.create-notification-subscription.endpoint':
        'notification-endpoint',
    'workdocs.describe-users.query': 'user-query',
    'lex-models.delete-bot.version': 'bot-version',
    'lex-models.delete-intent.version': 'intent-version',
    'lex-models.delete-slot-type.version': 'slot-type-version',
    'lex-models.get-intent.version': 'intent-version',
    'lex-models.get-slot-type.version': 'slot-type-version',
    'lex-models.delete-bot-version.version': 'bot-version',
    'lex-models.delete-intent-version.version': 'intent-version',
    'lex-models.delete-slot-type-version.version': 'slot-type-version',
    'lex-models.get-export.version': 'resource-version',
    'mobile.create-project.region': 'project-region',
    'rekognition.create-stream-processor.output': 'stream-processor-output',
    'eks.create-cluster.version': 'kubernetes-version',
    'eks.update-cluster-version.version': 'kubernetes-version',
    'eks.create-nodegroup.version': 'kubernetes-version',
    'eks.update-nodegroup-version.version': 'kubernetes-version',
    'schemas.*.version': 'schema-version',
}


def register_arg_renames(cli):
    for original, new_name in ARGUMENT_RENAMES.items():
        event_portion, original_arg_name = original.rsplit('.', 1)
        cli.register('building-argument-table.%s' % event_portion,
                     rename_arg(original_arg_name, new_name))


def rename_arg(original_arg_name, new_name):
    def _rename_arg(argument_table, **kwargs):
        if original_arg_name in argument_table:
            utils.rename_argument(argument_table, original_arg_name, new_name)
    return _rename_arg
