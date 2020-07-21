from awscli.customizations.codeartifact.login import CodeArtifactLogin


def register_codeartifact_commands(event_emitter):
    event_emitter.register(
        'building-command-table.codeartifact', inject_commands
    )


def inject_commands(command_table, session, **kwargs):
    command_table['login'] = CodeArtifactLogin(session)
