import os

from sphinx.application import Sphinx

#!/usr/bin/env python
"""Generate apache rewrite rules for cross linking.

Example CLI:

^/goto/aws-cli/acm-2015-12-08/AddTagsToCertificate

will redirect to

https://docs.aws.amazon.com/cli/latest/reference/acm/add-tags-to-certificate.html

Usage
=====

Make sure you're in a venv with the correct versions of the AWS CLI v2 installed. 
It will be imported directly to generate the crosslinking.

This is a Sphinx extension that gets run after all document updates have been 
executed and before the cleanup phase.
"""
import awscli.clidriver

import awscli.botocore.session


class CrossLinkGenerator(object):
    # Subclasses must set these values:

    # The name of the tool (boto3, aws-cli), this is what's
    # used in the goto links: /goto/{toolname}/{operation}
    TOOL_NAME = None
    # The base url for your SDK service reference.  This page
    # is used as a fallback for goto links for unknown service
    # uids and for the "catch all" regex for the tool.
    FALLBACK_BASE = None
    # The url used for an specific service.  This value
    # must have one string placeholder value where the
    # service_name can be placed.
    SERVICE_BASE = None

    def __init__(self):
        # Cache of service -> operation names
        # The operation names are not xformed(), they're
        # exactly as they're spelled in the API reference.
        self._service_operations = {}
        # Mapping of service name to boto3 class name.
        self._service_class_names = {}
        # Mapping of uid -> service_name
        self._uid_mapping = {}
        self._generate_mappings()

    def _generate_mappings(self):
        raise NotImplementedError("_generate_mappings")

    def _generate_cross_link(self, service_name, operation_name):
        raise NotImplementedError("_generate_cross_link")

    def generate_cross_link(self, link):
        parts = link.split('/')
        if len(parts) < 4:
            return None
        tool_name = parts[2]
        if tool_name != self.TOOL_NAME:
            return None
        if self._is_catchall_regex(parts):
            return self.FALLBACK_BASE
        uid = parts[3]
        if uid not in self._uid_mapping:
            return self.FALLBACK_BASE
        service_name = self._uid_mapping[uid]
        if self._is_service_catchall_regex(parts):
            return self.SERVICE_BASE % service_name
        # At this point we know this is a valid cross link
        # for an operation we probably know about, so we can
        # defer to the template method.
        return self._generate_cross_link(
            service_name=service_name,
            operation_name=parts[-1],
        )

    def _is_catchall_regex(self, parts):
        # This is the catch all regex used as a safety net
        # for any requests to our tool that we don't understand.
        # For example: /goto/aws-cli/(.*)
        return len(parts) == 4 and parts[-1] == '(.*)'

    def _is_service_catchall_regex(self, parts):
        # This is the catch all regex used for requests to a
        # known service for an unknown operation/shape.
        # For example: /goto/aws-cli/xray-2016-04-12/(.*)
        return len(parts) == 5 and parts[-1] == '(.*)'


# TODO maybe just remove the parent class since that's unnecessary abstraction
# in the context of this repo
class AWSCLICrossLinkGenerator(CrossLinkGenerator):
    # TODO swap for v2 links
    TOOL_NAME = 'aws-cli'
    BASE_URL = 'https://docs.aws.amazon.com/cli/latest/reference'
    FALLBACK_BASE = (
        'https://docs.aws.amazon.com/cli/latest/reference/index.html'
    )
    SERVICE_BASE = (
        'https://docs.aws.amazon.com/cli/latest/reference/%s/index.html'
    )

    def __init__(self):
        self._driver = awscli.clidriver.create_clidriver()
        self._service_operations = {}
        super(AWSCLICrossLinkGenerator, self).__init__()

    def _generate_mappings(self):
        # TODO verify correctness against v2
        command_table = self._driver.create_help_command().command_table
        for name, command in command_table.items():
            if hasattr(command, '_UNDOCUMENTED'):
                continue
            if not hasattr(command, 'service_model'):
                continue
            uid = command.service_model.metadata.get('uid')
            if uid is None:
                continue
            self._uid_mapping[uid] = name
            ops_table = command.create_help_command().command_table
            mapping = {}
            for op_name, op_command in ops_table.items():
                op_help = op_command.create_help_command()
                mapping[op_help.obj.name] = op_name
            self._service_operations[name] = mapping

    def _generate_cross_link(self, service_name, operation_name):
        if operation_name not in self._service_operations[service_name]:
            return self.SERVICE_BASE % service_name
        return '%s/%s/%s.html' % (
            self.BASE_URL, service_name,
            self._service_operations[service_name][operation_name]
        )


def create_goto_links_iter(session):
    for service_name in session.get_available_services():
        m = session.get_service_model(service_name)
        uid = m.metadata.get('uid')
        if uid is None:
            continue
        for operation_name in m.operation_names:
            yield '/goto/{toolname}/%s/%s' % (uid, operation_name)
        # We also want to yield a catch all link for the service.
        yield '/goto/{toolname}/%s/(.*)' % uid
    # And a catch all for the entire tool.
    yield '/goto/{toolname}/(.*)'


def create_rewrite_rule(incoming_link, redirect):
    # Given an incoming_link (/goto/aws-cli/...) and the
    # URL it should redirect to, generate the actual
    # rewrite rule.
    return 'RewriteRule ^%s$ %s [L,R,NE]\n' % (incoming_link, redirect)


def generate_all_cross_links(session, out_file):
    # links_iter: Generator of crosslinks to generate
    linker = AWSCLICrossLinkGenerator()
    # This gives us a list of tuples of
    # (goto_link, redirect_link)
    crosslinks = generate_tool_cross_links(session, linker)
    # From there we need to convert that to the actual Rewrite rules.
    lines = generate_conf_for_crosslinks(linker, crosslinks)
    out_file.writelines(lines)


def generate_conf_for_crosslinks(linker, crosslinks):
    # These first two lines are saying that if the URL
    # does not match the regex '/goto/(toolname)', then
    # we should skip all the RewriteRules associated with
    # that toolname.
    # The way RewriteCond works is that if the condition
    # evalutes to true, the immediately next RewriteRule
    # is triggered.
    lines = [
        'RewriteCond %%{REQUEST_URI} !^\/goto\/%s\/.*$\n' % linker.TOOL_NAME,
        # The S=12345 means skip the next 12345 lines.  This
        # rule is only triggered if the RewriteCond above
        # evaluates to true.  Think of this as a fancy GOTO.
        'RewriteRule ".*" "-" [S=%s]\n' % len(crosslinks)
    ]
    for goto_link, redirect in crosslinks:
        lines.append(create_rewrite_rule(goto_link, redirect))
    return lines


# TODO can we remove the dependence on botocore session ?
# or at least use the vendored botocore session
def generate_tool_cross_links(session, linker):
    crosslinks = []
    for link_template in create_goto_links_iter(session):
        link_str = link_template.format(toolname=linker.TOOL_NAME)
        result = linker.generate_cross_link(link_str)
        if result is not None:
            crosslinks.append((link_str, result))
    return crosslinks


def generate_crosslinks(app: Sphinx):
    session = awscli.botocore.session.get_session()
    out_path = os.path.join(os.path.abspath('.'), 'package.redirects.conf')
    with open(out_path, 'w') as out_file:
        generate_all_cross_links(session, out_file)

    # Sphinx expects us to return an iterable of pages we want to create using
    # their template/context system. We return an empty list since this extension
    # does not create HTML pages via this system.
    return []


def setup(app: Sphinx):
    # hook into the html-collect-pages event to guarantee all
    # document writing/modification has been completed before
    # generating crosslinks.
    app.connect('html-collect-pages', generate_crosslinks)

    # TODO double check the returns from sphinx extensions
    return {
        'version': '0.1',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }