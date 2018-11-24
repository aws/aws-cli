from awscli.customizations.wizard import core, ui
from awscli.customizations.configure.writer import ConfigFileWriter


def create_default_wizard_runner(session):
    api_invoker = core.APIInvoker(session=session)
    shared_config = core.SharedConfigAPI(session=session,
                                         config_writer=ConfigFileWriter())
    planner = core.Planner(
        step_handlers={
            'static': core.StaticStep(),
            'prompt': core.PromptStep(ui.UIPrompter()),
            'fileprompt': core.FilePromptStep(
                ui.UIFilePrompter(ui.FileCompleter())),
            'template': core.TemplateStep(),
            'apicall': core.APICallStep(api_invoker=api_invoker),
            'sharedconfig': core.SharedConfigStep(config_api=shared_config),
        }
    )
    executor = core.Executor(
        step_handlers={
            'apicall': core.APICallExecutorStep(api_invoker),
            'sharedconfig': core.SharedConfigExecutorStep(shared_config),
        }
    )
    runner = core.Runner(planner, executor)
    return runner

