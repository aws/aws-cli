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
from awscli.argprocess import ParamShorthand
from awscli.errorhandler import ErrorHandler
from awscli.customizations.streamingoutputarg import add_streaming_output_arg
from awscli.customizations.addexamples import add_examples
from awscli.customizations.removals import register_removals
from awscli.customizations.ec2addcount import ec2_add_count
from awscli.customizations.paginate import unify_paging_params
from awscli.customizations.ec2decryptpassword import ec2_add_priv_launch_key
from awscli.customizations.ec2secgroupsimplify import register_secgroup
from awscli.customizations.preview import register_preview_commands
from awscli.customizations.ec2bundleinstance import register_bundleinstance
from awscli.customizations.s3.s3 import s3_plugin_initialize
from awscli.customizations.ec2runinstances import register_runinstances
from awscli.customizations.rds import register_rds_modify_split
from awscli.customizations.putmetricdata import register_put_metric_data
from awscli.customizations.sessendemail import register_ses_send_email
from awscli.customizations.iamvirtmfa import IAMVMFAWrapper
from awscli.customizations.argrename import register_arg_renames
from awscli.customizations.dryrundocs import register_dryrun_docs
from awscli.customizations.route53resourceid import register_resource_id
from awscli.customizations.configure import register_configure_cmd
from awscli.customizations.cloudtrail import initialize as cloudtrail_init


def awscli_initialize(event_handlers):
    param_shorthand = ParamShorthand()
    event_handlers.register('process-cli-arg', param_shorthand)
    error_handler = ErrorHandler()
    event_handlers.register('after-call.*.*', error_handler)
    # The following will get fired for every option we are
    # documenting.  It will attempt to add an example_fn on to
    # the parameter object if the parameter supports shorthand
    # syntax.  The documentation event handlers will then use
    # the examplefn to generate the sample shorthand syntax
    # in the docs.  Registering here should ensure that this
    # handler gets called first but it still feels a bit brittle.
    event_handlers.register('doc-option-example.*.*.*',
                            param_shorthand.add_example_fn)
    event_handlers.register('doc-examples.*.*',
                            add_examples)
    event_handlers.register('building-argument-table.s3api.*',
                            add_streaming_output_arg)
    event_handlers.register('building-argument-table.ec2.run-instances',
                            ec2_add_count)
    event_handlers.register('building-argument-table',
                            unify_paging_params)
    event_handlers.register('building-argument-table.ec2.get-password-data',
                            ec2_add_priv_launch_key)
    register_secgroup(event_handlers)
    register_bundleinstance(event_handlers)
    s3_plugin_initialize(event_handlers)
    register_runinstances(event_handlers)
    register_removals(event_handlers)
    register_preview_commands(event_handlers)
    register_rds_modify_split(event_handlers)
    register_put_metric_data(event_handlers)
    register_ses_send_email(event_handlers)
    IAMVMFAWrapper(event_handlers)
    register_arg_renames(event_handlers)
    register_dryrun_docs(event_handlers)
    register_resource_id(event_handlers)
    register_configure_cmd(event_handlers)
    cloudtrail_init(event_handlers)
