from awscli.customizations.wizard import core, ui
from awscli.customizations.configure.writer import ConfigFileWriter


def create_default_wizard_runner(session):
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
    executor = core.Executor(
        step_handlers={
            core.APICallExecutorStep.NAME: core.APICallExecutorStep(
                api_invoker),
            core.SharedConfigExecutorStep.NAME: core.SharedConfigExecutorStep(
                shared_config),
            core.DefineVariableStep.NAME: core.DefineVariableStep(),
            core.MergeDictStep.NAME: core.MergeDictStep(),
        }
    )
    runner = core.Runner(planner, executor)
    return runner
