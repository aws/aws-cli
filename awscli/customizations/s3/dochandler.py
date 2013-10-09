import os

from bcdoc.clidocs import CLIDocumentEventHandler

import awscli


class S3DocumentEventHandler(CLIDocumentEventHandler):
    """
    This is the document handler for both the service, s3, and
    the commands. It is the basis for the help command and generating docs.
    """
    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        command = help_command.obj
        doc.style.h1(command._name)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        command = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(command.documentation)
        if help_command.obj._name == 's3':
            doc_dir = os.path.join(
                os.path.dirname(os.path.abspath(awscli.__file__)),
                'examples', help_command.event_class.lower())
            # The file is named '_concepts.rst' so that it doesn't
            # collide with any s3 commands, in the rare chance we
            # create a subcommand called "concepts".
            doc_path = os.path.join(doc_dir, '_concepts.rst')
            if os.path.isfile(doc_path):
                help_command.doc.style.h2('Important Concepts')
                fp = open(doc_path)
                for line in fp.readlines():
                    help_command.doc.write(line)

    def doc_synopsis_start(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            command = help_command.obj
            doc.style.h2('Synopsis')
            doc.style.start_codeblock()
            doc.writeln('%s %s' % (command._name, command.usage))

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        option_str = argument._name
        if 'nargs' in argument.options:
            if argument.options['nargs'] == '+':
                option_str += " <value> [<value>...]"
            else:
                for i in range(argument.options['nargs']):
                    option_str += " <value>"
        doc.writeln('[--%s]' % option_str)

    def doc_synopsis_end(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            doc.style.end_codeblock()

    def doc_options_start(self, help_command, **kwargs):
        if help_command.obj._name != 's3':
            doc = help_command.doc
            doc.style.h2('Options')
            if len(help_command.arg_table) == 0:
                doc.write('*None*\n')

    def doc_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        doc.write('``--%s``\n' % argument._name)
        doc.style.indent()
        doc.include_doc_string(argument.documentation)
        doc.style.dedent()
        doc.style.new_paragraph()

    def doc_subitems_start(self, help_command, **kwargs):
        if help_command.command_table:
            doc = help_command.doc
            doc.style.h2('Available Commands')
            doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        doc.style.tocitem(command_name)



