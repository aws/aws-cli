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
"""
This customization adds the following scalar parameters to the
authorize operations:

* --protocol: tcp | udp | icmp or any protocol number
* --port:  A single integer or a range (min-max). You can specify ``all``
  to mean all ports (for example, port range 0-65535)
* --source-group: Either the source security group ID or name.
* --cidr -  The CIDR range. Cannot be used when specifying a source or
  destination security group.
"""

from awscli.arguments import CustomArgument


def _add_params(argument_table, **kwargs):
    arg = ProtocolArgument('protocol',
                           help_text=PROTOCOL_DOCS)
    argument_table['protocol'] = arg
    argument_table['ip-protocol']._UNDOCUMENTED = True

    arg = PortArgument('port', help_text=PORT_DOCS)
    argument_table['port'] = arg
    # Port handles both the from-port and to-port,
    # we need to not document both args.
    argument_table['from-port']._UNDOCUMENTED = True
    argument_table['to-port']._UNDOCUMENTED = True

    arg = CidrArgument('cidr', help_text=CIDR_DOCS)
    argument_table['cidr'] = arg
    argument_table['cidr-ip']._UNDOCUMENTED = True

    arg = SourceGroupArgument('source-group',
                              help_text=SOURCEGROUP_DOCS)
    argument_table['source-group'] = arg
    argument_table['source-security-group-name']._UNDOCUMENTED = True

    arg = GroupOwnerArgument('group-owner',
                             help_text=GROUPOWNER_DOCS)
    argument_table['group-owner'] = arg
    argument_table['source-security-group-owner-id']._UNDOCUMENTED = True


def _check_args(parsed_args, **kwargs):
    # This function checks the parsed args.  If the user specified
    # the --ip-permissions option with any of the scalar options we
    # raise an error.
    arg_dict = vars(parsed_args)
    if arg_dict['ip_permissions']:
        for key in ('protocol', 'port', 'cidr',
                    'source_group', 'group_owner'):
            if arg_dict[key]:
                msg = ('The --%s option is not compatible '
                       'with the --ip-permissions option ') % key
                raise ValueError(msg)


def _add_docs(help_command, **kwargs):
    doc = help_command.doc
    doc.style.new_paragraph()
    doc.style.start_note()
    msg = ('To specify multiple rules in a single command '
           'use the <code>--ip-permissions</code> option')
    doc.include_doc_string(msg)
    doc.style.end_note()


EVENTS = [
    ('building-argument-table.ec2.authorize-security-group-ingress',
     _add_params),
    ('building-argument-table.ec2.authorize-security-group-egress',
     _add_params),
    ('building-argument-table.ec2.revoke-security-group-ingress', _add_params),
    ('building-argument-table.ec2.revoke-security-group-egress', _add_params),
    ('operation-args-parsed.ec2.authorize-security-group-ingress',
     _check_args),
    ('operation-args-parsed.ec2.authorize-security-group-egress', _check_args),
    ('operation-args-parsed.ec2.revoke-security-group-ingress', _check_args),
    ('operation-args-parsed.ec2.revoke-security-group-egress', _check_args),
    ('doc-description.ec2.authorize-security-group-ingress', _add_docs),
    ('doc-description.ec2.authorize-security-group-egress', _add_docs),
    ('doc-description.ec2.revoke-security-group-ingress', _add_docs),
    ('doc-description.ec2.revoke-security-groupdoc-ingress', _add_docs),
]
PROTOCOL_DOCS = ('<p>The IP protocol: <code>tcp</code> | '
                 '<code>udp</code> | <code>icmp</code></p> '
                 '<p>(VPC only) Use <code>all</code> to specify all protocols.</p>'
                 '<p>If this argument is provided without also providing the '
                 '<code>port</code> argument, then it will be applied to all '
                 'ports for the specified protocol.</p>')
PORT_DOCS = ('<p>For TCP or UDP: The range of ports to allow.'
             '  A single integer or a range (<code>min-max</code>).</p>'
             '<p>For ICMP: A single integer or a range (<code>type-code</code>)'
             ' representing the ICMP type'
             ' number and the ICMP code number respectively.'
             ' A value of -1 indicates all ICMP codes for'
             ' all ICMP types. A value of -1 just for <code>type</code>'
             ' indicates all ICMP codes for the specified ICMP type.</p>')
CIDR_DOCS = '<p>The CIDR IP range.</p>'
SOURCEGROUP_DOCS = ('<p>The name or ID of the source security group.</p>')
GROUPOWNER_DOCS = ('<p>The AWS account ID that owns the source security '
                   'group. Cannot be used when specifying a CIDR IP '
                   'address.</p>')


def register_secgroup(event_handler):
    for event, handler in EVENTS:
        event_handler.register(event, handler)


def _build_ip_permissions(params, key, value):
    if 'IpPermissions' not in params:
        params['IpPermissions'] = [{}]
    if key == 'CidrIp':
        if 'IpRanges' not in params['ip_permissions'][0]:
            params['IpPermissions'][0]['IpRanges'] = []
        params['IpPermissions'][0]['IpRanges'].append(value)
    elif key in ('GroupId', 'GroupName', 'UserId'):
        if 'UserIdGroupPairs' not in params['IpPermissions'][0]:
            params['IpPermissions'][0]['UserIdGroupPairs'] = [{}]
        params['IpPermissions'][0]['UserIdGroupPairs'][0][key] = value
    else:
        params['IpPermissions'][0][key] = value


class ProtocolArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            try:
                int_value = int(value)
                if (int_value < 0 or int_value > 255) and int_value != -1:
                    msg = ('protocol numbers must be in the range 0-255 '
                           'or -1 to specify all protocols')
                    raise ValueError(msg)
            except ValueError:
                if value not in ('tcp', 'udp', 'icmp', 'all'):
                    msg = ('protocol parameter should be one of: '
                           'tcp|udp|icmp|all or any valid protocol number.')
                    raise ValueError(msg)
                if value == 'all':
                    value = '-1'
            _build_ip_permissions(parameters, 'IpProtocol', value)


class PortArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            try:
                if value == '-1' or value == 'all':
                    fromstr = '-1'
                    tostr = '-1'
                elif '-' in value:
                    # We can get away with simple logic here because
                    # argparse will not allow values such as
                    # "-1-8", and these aren't actually valid
                    # values any from from/to ports.
                    fromstr, tostr = value.split('-', 1)
                else:
                    fromstr, tostr = (value, value)
                _build_ip_permissions(parameters, 'FromPort', int(fromstr))
                _build_ip_permissions(parameters, 'ToPort', int(tostr))
            except ValueError:
                msg = ('port parameter should be of the '
                       'form <from[-to]> (e.g. 22 or 22-25)')
                raise ValueError(msg)


class CidrArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            value = [{'CidrIp': value}]
            _build_ip_permissions(parameters, 'IpRanges', value)


class SourceGroupArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            if value.startswith('sg-'):
                _build_ip_permissions(parameters, 'GroupId', value)
            else:
                _build_ip_permissions(parameters, 'GroupName', value)


class GroupOwnerArgument(CustomArgument):

    def add_to_params(self, parameters, value):
        if value:
            _build_ip_permissions(parameters, 'UserId', value)
