from awscli.customizations.logs.startlivetail import StartLiveTailCommand


def register_logs_commands(cli):
    cli.register('building-command-table.logs', inject_start_live_tail_command)


def inject_start_live_tail_command(command_table, session, **kwargs):
    command_table['start-live-tail'] = StartLiveTailCommand(session)