import os
import sys
import argparse
from bcdoc.mangen import gen_man


def do_operation(session, args):
    service = session.get_service(args.service)
    operation = service.get_operation(args.operation)
    gen_man(session, operation=operation)


def do_service(session, args):
    service = session.get_service(args.service)
    gen_man(session, service=service)


def do_provider(session, args):
    cli_data = get_cli_data(session, provider_name=args.provider)
    gen_man(session, provider=args.provider, cli_data=cli_data)


def get_cli_data(session, provider_name):
    cli_data = session.get_data('cli')
    for option in cli_data['options']:
        if option.startswith('--'):
            option_data = cli_data['options'][option]
            if 'choices' in option_data:
                choices = option_data['choices']
                if not isinstance(choices, list):
                    choices_path = choices.format(provider=provider_name)
                    choices = session.get_data(choices_path)
                    option_data['choices'] = choices
    return cli_data
