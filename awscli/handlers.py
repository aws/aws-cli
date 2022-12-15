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
"""Builtin CLI extensions.

This is a collection of built in CLI extensions that can be automatically
registered with the event system.

"""
from awscli.argprocess import ParamShorthandParser
from awscli.paramfile import register_uri_param_handler
from awscli.customizations import datapipeline
from awscli.customizations.addexamples import add_examples
from awscli.customizations.argrename import register_arg_renames
from awscli.customizations.assumerole import register_assume_role_provider
from awscli.customizations.awslambda import register_lambda_create_function
from awscli.customizations.cliinputjson import register_cli_input_json
from awscli.customizations.cloudformation import initialize as cloudformation_init
from awscli.customizations.cloudfront import register as register_cloudfront
from awscli.customizations.cloudsearch import initialize as cloudsearch_init
from awscli.customizations.cloudsearchdomain import register_cloudsearchdomain
from awscli.customizations.cloudtrail import initialize as cloudtrail_init
from awscli.customizations.codeartifact import register_codeartifact_commands
from awscli.customizations.codecommit import initialize as codecommit_init
from awscli.customizations.codedeploy.codedeploy import initialize as \
    codedeploy_init
from awscli.customizations.configservice.getstatus import register_get_status
from awscli.customizations.configservice.putconfigurationrecorder import \
    register_modify_put_configuration_recorder
from awscli.customizations.configservice.rename_cmd import \
    register_rename_config
from awscli.customizations.configservice.subscribe import register_subscribe
from awscli.customizations.configure.configure import register_configure_cmd
from awscli.customizations.history import register_history_mode
from awscli.customizations.history import register_history_commands
from awscli.customizations.ec2.addcount import register_count_events
from awscli.customizations.ec2.bundleinstance import register_bundleinstance
from awscli.customizations.ec2.decryptpassword import ec2_add_priv_launch_key
from awscli.customizations.ec2.protocolarg import register_protocol_args
from awscli.customizations.ec2.runinstances import register_runinstances
from awscli.customizations.ec2.secgroupsimplify import register_secgroup
from awscli.customizations.ec2.paginate import register_ec2_page_size_injector
from awscli.customizations.ecr import register_ecr_commands
from awscli.customizations.ecr_public import register_ecr_public_commands
from awscli.customizations.emr.emr import emr_initialize
from awscli.customizations.emrcontainers import \
    initialize as emrcontainers_initialize
from awscli.customizations.eks import initialize as eks_initialize
from awscli.customizations.ecs import initialize as ecs_initialize
from awscli.customizations.gamelift import register_gamelift_commands
from awscli.customizations.generatecliskeleton import \
    register_generate_cli_skeleton
from awscli.customizations.globalargs import register_parse_global_args
from awscli.customizations.iamvirtmfa import IAMVMFAWrapper
from awscli.customizations.iot import register_create_keys_and_cert_arguments
from awscli.customizations.iot import register_create_keys_from_csr_arguments
from awscli.customizations.iot_data import register_custom_endpoint_note
from awscli.customizations.kms import register_fix_kms_create_grant_docs
from awscli.customizations.dlm.dlm import dlm_initialize
from awscli.customizations.opsworks import initialize as opsworks_init
from awscli.customizations.paginate import register_pagination
from awscli.customizations.preview import register_preview_commands
from awscli.customizations.putmetricdata import register_put_metric_data
from awscli.customizations.rds import register_rds_modify_split
from awscli.customizations.rds import register_add_generate_db_auth_token
from awscli.customizations.rekognition import register_rekognition_detect_labels
from awscli.customizations.removals import register_removals
from awscli.customizations.route53 import register_create_hosted_zone_doc_fix
from awscli.customizations.s3.s3 import s3_plugin_initialize
from awscli.customizations.s3errormsg import register_s3_error_msg
from awscli.customizations.scalarparse import register_scalar_parser
from awscli.customizations.sessendemail import register_ses_send_email
from awscli.customizations.streamingoutputarg import add_streaming_output_arg
from awscli.customizations.translate import register_translate_import_terminology
from awscli.customizations.toplevelbool import register_bool_params
from awscli.customizations.waiters import register_add_waiters
from awscli.customizations.opsworkscm import register_alias_opsworks_cm
from awscli.customizations.mturk import register_alias_mturk_command
from awscli.customizations.sagemaker import register_alias_sagemaker_runtime_command
from awscli.customizations.servicecatalog import register_servicecatalog_commands
from awscli.customizations.s3events import register_event_stream_arg
from awscli.customizations.sessionmanager import register_ssm_session
from awscli.customizations.sms_voice import register_sms_voice_hide
from awscli.customizations.dynamodb import register_dynamodb_paginator_fix
from awscli.customizations.overridesslcommonname import register_override_ssl_common_name
from awscli.customizations.kinesis import \
    register_kinesis_list_streams_pagination_backcompat


def awscli_initialize(event_handlers):
    event_handlers.register('session-initialized', register_uri_param_handler)
    param_shorthand = ParamShorthandParser()
    event_handlers.register('process-cli-arg', param_shorthand)
    # The s3 error message needs to registered before the
    # generic error handler.
    register_s3_error_msg(event_handlers)
#    # The following will get fired for every option we are
#    # documenting.  It will attempt to add an example_fn on to
#    # the parameter object if the parameter supports shorthand
#    # syntax.  The documentation event handlers will then use
#    # the examplefn to generate the sample shorthand syntax
#    # in the docs.  Registering here should ensure that this
#    # handler gets called first but it still feels a bit brittle.
#    event_handlers.register('doc-option-example.*.*.*',
#                            param_shorthand.add_example_fn)
    event_handlers.register('doc-examples.*.*',
                            add_examples)
    register_cli_input_json(event_handlers)
    event_handlers.register('building-argument-table.*',
                            add_streaming_output_arg)
    register_count_events(event_handlers)
    event_handlers.register('building-argument-table.ec2.get-password-data',
                            ec2_add_priv_launch_key)
    register_parse_global_args(event_handlers)
    register_pagination(event_handlers)
    register_secgroup(event_handlers)
    register_bundleinstance(event_handlers)
    s3_plugin_initialize(event_handlers)
    register_runinstances(event_handlers)
    register_removals(event_handlers)
    register_preview_commands(event_handlers)
    register_rds_modify_split(event_handlers)
    register_rekognition_detect_labels(event_handlers)
    register_add_generate_db_auth_token(event_handlers)
    register_put_metric_data(event_handlers)
    register_ses_send_email(event_handlers)
    IAMVMFAWrapper(event_handlers)
    register_arg_renames(event_handlers)
    register_configure_cmd(event_handlers)
    cloudtrail_init(event_handlers)
    register_ecr_commands(event_handlers)
    register_ecr_public_commands(event_handlers)
    register_bool_params(event_handlers)
    register_protocol_args(event_handlers)
    datapipeline.register_customizations(event_handlers)
    cloudsearch_init(event_handlers)
    emr_initialize(event_handlers)
    emrcontainers_initialize(event_handlers)
    eks_initialize(event_handlers)
    ecs_initialize(event_handlers)
    register_cloudsearchdomain(event_handlers)
    register_generate_cli_skeleton(event_handlers)
    register_assume_role_provider(event_handlers)
    register_add_waiters(event_handlers)
    codedeploy_init(event_handlers)
    register_subscribe(event_handlers)
    register_get_status(event_handlers)
    register_rename_config(event_handlers)
    register_scalar_parser(event_handlers)
    opsworks_init(event_handlers)
    register_lambda_create_function(event_handlers)
    register_fix_kms_create_grant_docs(event_handlers)
    register_create_hosted_zone_doc_fix(event_handlers)
    register_modify_put_configuration_recorder(event_handlers)
    register_codeartifact_commands(event_handlers)
    codecommit_init(event_handlers)
    register_custom_endpoint_note(event_handlers)
    event_handlers.register(
        'building-argument-table.iot.create-keys-and-certificate',
        register_create_keys_and_cert_arguments)
    event_handlers.register(
        'building-argument-table.iot.create-certificate-from-csr',
        register_create_keys_from_csr_arguments)
    register_cloudfront(event_handlers)
    register_gamelift_commands(event_handlers)
    register_ec2_page_size_injector(event_handlers)
    cloudformation_init(event_handlers)
    register_alias_opsworks_cm(event_handlers)
    register_alias_mturk_command(event_handlers)
    register_alias_sagemaker_runtime_command(event_handlers)
    register_servicecatalog_commands(event_handlers)
    register_translate_import_terminology(event_handlers)
    register_history_mode(event_handlers)
    register_history_commands(event_handlers)
    register_event_stream_arg(event_handlers)
    dlm_initialize(event_handlers)
    register_ssm_session(event_handlers)
    register_sms_voice_hide(event_handlers)
    register_dynamodb_paginator_fix(event_handlers)
    register_override_ssl_common_name(event_handlers)
    register_kinesis_list_streams_pagination_backcompat(event_handlers)
