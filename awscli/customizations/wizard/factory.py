# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.wizard.ui.layout import WizardLayoutFactory
from awscli.customizations.wizard import core, ui
from awscli.customizations.wizard.app import (
    WizardAppRunner, WizardApp, WizardValues, WizardTraverser,
)
from awscli.customizations.configure.writer import ConfigFileWriter


def create_default_executor(api_invoker, shared_config):
    return core.Executor(
        step_handlers={
            core.APICallExecutorStep.NAME: core.APICallExecutorStep(
                api_invoker),
            core.SharedConfigExecutorStep.NAME: core.SharedConfigExecutorStep(
                shared_config),
            core.DefineVariableStep.NAME: core.DefineVariableStep(),
            core.MergeDictStep.NAME: core.MergeDictStep(),
            core.LoadDataStep.NAME: core.LoadDataStep(),
            core.DumpDataStep.NAME: core.DumpDataStep(),
        }
    )


def create_default_wizard_v1_runner(session):
    api_invoker = core.APIInvoker(session=session)
    shared_config = core.SharedConfigAPI(session=session,
                                         config_writer=ConfigFileWriter())
    planner = core.Planner(
        step_handlers={
            core.StaticStep.NAME: core.StaticStep(),
            core.PromptStep.NAME: core.PromptStep(ui.UIPrompter()),
            core.YesNoPrompt.NAME: core.YesNoPrompt(ui.UIPrompter()),
            core.FilePromptStep.NAME: core.FilePromptStep(
                ui.UIFilePrompter(ui.FileCompleter())),
            core.TemplateStep.NAME: core.TemplateStep(),
            core.APICallStep.NAME: core.APICallStep(api_invoker=api_invoker),
            core.SharedConfigStep.NAME: core.SharedConfigStep(
                config_api=shared_config),
        }
    )
    executor = create_default_executor(api_invoker, shared_config)
    runner = core.Runner(planner, executor)
    return runner


def create_default_wizard_v2_runner(session):
    return WizardAppRunner(session=session, app_factory=create_wizard_app)


def create_wizard_app(definition, session, output=None):
    api_invoker = core.APIInvoker(session=session)
    shared_config = core.SharedConfigAPI(session=session,
                                         config_writer=ConfigFileWriter())
    layout = WizardLayoutFactory().create_wizard_layout(definition)
    values = WizardValues(
        definition,
        value_retrieval_steps={
            core.APICallStep.NAME: core.APICallStep(api_invoker=api_invoker),
            core.SharedConfigStep.NAME: core.SharedConfigStep(
                config_api=shared_config),
            core.TemplateStep.NAME: core.TemplateStep(),
        },
        exception_handler=layout.error_bar.display_error
    )
    executor = create_default_executor(api_invoker, shared_config)
    traverser = WizardTraverser(definition, values, executor)
    return WizardApp(
        layout=layout, values=values, traverser=traverser,
        executor=executor, output=output
    )
