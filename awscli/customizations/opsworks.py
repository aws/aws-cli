# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime
import json
import logging
import os
import platform
import re
import shlex
import socket
import subprocess
import tempfile
import textwrap

from botocore.exceptions import ClientError

from awscli.compat import shlex_quote, urlopen, ensure_text_type
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import create_client_from_parsed_globals


LOG = logging.getLogger(__name__)

IAM_USER_POLICY_NAME = "OpsWorks-Instance"
IAM_USER_POLICY_TIMEOUT = datetime.timedelta(minutes=15)
IAM_PATH = '/AWS/OpsWorks/'

HOSTNAME_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$", re.I)
INSTANCE_ID_RE = re.compile(r"^i-[0-9a-f]+$")
IP_ADDRESS_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

IDENTITY_URL = \
    "http://169.254.169.254/latest/dynamic/instance-identity/document"

REMOTE_SCRIPT = """
set -e
umask 007
AGENT_TMP_DIR=$(mktemp -d /tmp/opsworks-agent-installer.XXXXXXXXXXXXXXXX)
curl --retry 5 -L %(agent_installer_url)s | tar xz -C $AGENT_TMP_DIR
cat >$AGENT_TMP_DIR/opsworks-agent-installer/preconfig <<EOF
%(preconfig)s
EOF
exec sudo /bin/sh -c "\
OPSWORKS_ASSETS_DOWNLOAD_BUCKET=%(assets_download_bucket)s \
$AGENT_TMP_DIR/opsworks-agent-installer/boot-registration; \
rm -rf $AGENT_TMP_DIR"
""".lstrip()


def initialize(cli):
    cli.register('building-command-table.opsworks', inject_commands)


def inject_commands(command_table, session, **kwargs):
    command_table['register'] = OpsWorksRegister(session)


class OpsWorksRegister(BasicCommand):
    NAME = "register"
    DESCRIPTION = textwrap.dedent("""
        Registers an EC2 instance or machine with AWS OpsWorks.

        Registering a machine using this command will install the AWS OpsWorks
        agent on the target machine and register it with an existing OpsWorks
        stack.
    """).strip()

    ARG_TABLE = [
        {'name': 'stack-id', 'required': True,
         'help_text': """A stack ID. The instance will be registered with the
                         given stack."""},
        {'name': 'infrastructure-class', 'required': True,
         'choices': ['ec2', 'on-premises'],
         'help_text': """Specifies whether to register an EC2 instance (`ec2`)
                         or an on-premises instance (`on-premises`)."""},
        {'name': 'override-hostname', 'dest': 'hostname',
         'help_text': """The instance hostname. If not provided, the current
                         hostname of the machine will be used."""},
        {'name': 'override-private-ip', 'dest': 'private_ip',
         'help_text': """An IP address. If you set this parameter, the given IP
                         address will be used as the private IP address within
                         OpsWorks.  Otherwise the private IP address will be
                         determined automatically. Not to be used with EC2
                         instances."""},
        {'name': 'override-public-ip', 'dest': 'public_ip',
         'help_text': """An IP address. If you set this parameter, the given IP
                         address will be used as the public IP address within
                         OpsWorks.  Otherwise the public IP address will be
                         determined automatically. Not to be used with EC2
                         instances."""},
        {'name': 'override-ssh', 'dest': 'ssh',
         'help_text': """If you set this parameter, the given command will be
                         used to connect to the machine."""},
        {'name': 'ssh-username', 'dest': 'username',
         'help_text': """If provided, this username will be used to connect to
                         the host."""},
        {'name': 'ssh-private-key', 'dest': 'private_key',
         'help_text': """If provided, the given private key file will be used
                         to connect to the machine."""},
        {'name': 'local', 'action': 'store_true',
         'help_text': """If given, instead of a remote machine, the local
                         machine will be imported. Cannot be used together
                         with `target`."""},
        {'name': 'use-instance-profile', 'action': 'store_true',
         'help_text': """Use the instance profile instead of creating an IAM
                         user."""},
        {'name': 'target', 'positional_arg': True, 'nargs': '?',
         'synopsis': '[<target>]',
         'help_text': """Either the EC2 instance ID or the hostname of the
                         instance or machine to be registered with OpsWorks.
                         Cannot be used together with `--local`."""},
    ]

    def __init__(self, session):
        super(OpsWorksRegister, self).__init__(session)
        self._stack = None
        self._ec2_instance = None
        self._prov_params = None
        self._use_address = None
        self._use_hostname = None
        self._name_for_iam = None
        self.access_key = None

    def _create_clients(self, args, parsed_globals):
        self.iam = self._session.create_client('iam')
        self.opsworks = create_client_from_parsed_globals(
            self._session, 'opsworks', parsed_globals)

    def _run_main(self, args, parsed_globals):
        self._create_clients(args, parsed_globals)

        self.prevalidate_arguments(args)
        self.retrieve_stack(args)
        self.validate_arguments(args)
        self.determine_details(args)
        self.create_iam_entities(args)
        self.setup_target_machine(args)

    def prevalidate_arguments(self, args):
        """
        Validates command line arguments before doing anything else.
        """
        if not args.target and not args.local:
            raise ValueError("One of target or --local is required.")
        elif args.target and args.local:
            raise ValueError(
                "Arguments target and --local are mutually exclusive.")

        if args.local and platform.system() != 'Linux':
            raise ValueError(
                "Non-Linux instances are not supported by AWS OpsWorks.")

        if args.ssh and (args.username or args.private_key):
            raise ValueError(
                "Argument --override-ssh cannot be used together with "
                "--ssh-username or --ssh-private-key.")

        if args.infrastructure_class == 'ec2':
            if args.private_ip:
                raise ValueError(
                    "--override-private-ip is not supported for EC2.")
            if args.public_ip:
                raise ValueError(
                    "--override-public-ip is not supported for EC2.")

        if args.infrastructure_class == 'on-premises' and \
                args.use_instance_profile:
            raise ValueError(
                "--use-instance-profile is only supported for EC2.")

        if args.hostname:
            if not HOSTNAME_RE.match(args.hostname):
                raise ValueError(
                    "Invalid hostname: '%s'. Hostnames must consist of "
                    "letters, digits and dashes only and must not start or "
                    "end with a dash." % args.hostname)

    def retrieve_stack(self, args):
        """
        Retrieves the stack from the API, thereby ensures that it exists.

        Provides `self._stack`, `self._prov_params`, `self._use_address`, and
        `self._ec2_instance`.
        """

        LOG.debug("Retrieving stack and provisioning parameters")
        self._stack = self.opsworks.describe_stacks(
            StackIds=[args.stack_id]
        )['Stacks'][0]
        self._prov_params = \
            self.opsworks.describe_stack_provisioning_parameters(
                StackId=self._stack['StackId']
            )

        if args.infrastructure_class == 'ec2' and not args.local:
            LOG.debug("Retrieving EC2 instance information")
            ec2 = self._session.create_client(
                'ec2', region_name=self._stack['Region'])

            # `desc_args` are arguments for the describe_instances call,
            # whereas `conditions` is a list of lambdas for further filtering
            # on the results of the call.
            desc_args = {'Filters': []}
            conditions = []

            # make sure that the platforms (EC2/VPC) and VPC IDs of the stack
            # and the instance match
            if 'VpcId' in self._stack:
                desc_args['Filters'].append(
                    {'Name': 'vpc-id', 'Values': [self._stack['VpcId']]}
                )
            else:
                # Cannot search for non-VPC instances directly, thus filter
                # afterwards
                conditions.append(lambda instance: 'VpcId' not in instance)

            # target may be an instance ID, an IP address, or a name
            if INSTANCE_ID_RE.match(args.target):
                desc_args['InstanceIds'] = [args.target]
            elif IP_ADDRESS_RE.match(args.target):
                # Cannot search for either private or public IP at the same
                # time, thus filter afterwards
                conditions.append(
                    lambda instance:
                        instance.get('PrivateIpAddress') == args.target or
                        instance.get('PublicIpAddress') == args.target)
                # also use the given address to connect
                self._use_address = args.target
            else:
                # names are tags
                desc_args['Filters'].append(
                    {'Name': 'tag:Name', 'Values': [args.target]}
                )

            # find all matching instances
            instances = [
                i
                for r in ec2.describe_instances(**desc_args)['Reservations']
                for i in r['Instances']
                if all(c(i) for c in conditions)
            ]

            if not instances:
                raise ValueError(
                    "Did not find any instance matching %s." % args.target)
            elif len(instances) > 1:
                raise ValueError(
                    "Found multiple instances matching %s: %s." % (
                        args.target,
                        ", ".join(i['InstanceId'] for i in instances)))

            self._ec2_instance = instances[0]

    def validate_arguments(self, args):
        """
        Validates command line arguments using the retrieved information.
        """

        if args.hostname:
            instances = self.opsworks.describe_instances(
                StackId=self._stack['StackId']
            )['Instances']
            if any(args.hostname.lower() == instance['Hostname']
                   for instance in instances):
                raise ValueError(
                    "Invalid hostname: '%s'. Hostnames must be unique within "
                    "a stack." % args.hostname)

        if args.infrastructure_class == 'ec2' and args.local:
            # make sure the regions match
            region = json.loads(
                ensure_text_type(urlopen(IDENTITY_URL).read()))['region']
            if region != self._stack['Region']:
                raise ValueError(
                    "The stack's and the instance's region must match.")

    def determine_details(self, args):
        """
        Determine details (like the address to connect to and the hostname to
        use) from the given arguments and the retrieved data.

        Provides `self._use_address` (if not provided already),
        `self._use_hostname` and `self._name_for_iam`.
        """

        # determine the address to connect to
        if not self._use_address:
            if args.local:
                pass
            elif args.infrastructure_class == 'ec2':
                if 'PublicIpAddress' in self._ec2_instance:
                    self._use_address = self._ec2_instance['PublicIpAddress']
                elif 'PrivateIpAddress' in self._ec2_instance:
                    LOG.warn(
                        "Instance does not have a public IP address. Trying "
                        "to use the private address to connect.")
                    self._use_address = self._ec2_instance['PrivateIpAddress']
                else:
                    # Should never happen
                    raise ValueError(
                        "The instance does not seem to have an IP address.")
            elif args.infrastructure_class == 'on-premises':
                self._use_address = args.target

        # determine the names to use
        if args.hostname:
            self._use_hostname = args.hostname
            self._name_for_iam = args.hostname
        elif args.local:
            self._use_hostname = None
            self._name_for_iam = socket.gethostname()
        else:
            self._use_hostname = None
            self._name_for_iam = args.target

    def create_iam_entities(self, args):
        """
        Creates an IAM group, user and corresponding credentials.

        Provides `self.access_key`.
        """

        if args.use_instance_profile:
            LOG.debug("Skipping IAM entity creation")
            self.access_key = None
            return

        LOG.debug("Creating the IAM group if necessary")
        group_name = "OpsWorks-%s" % clean_for_iam(self._stack['StackId'])
        try:
            self.iam.create_group(GroupName=group_name, Path=IAM_PATH)
            LOG.debug("Created IAM group %s", group_name)
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'EntityAlreadyExists':
                LOG.debug("IAM group %s exists, continuing", group_name)
                # group already exists, good
                pass
            else:
                raise

        # create the IAM user, trying alternatives if it already exists
        LOG.debug("Creating an IAM user")
        base_username = "OpsWorks-%s-%s" % (
            shorten_name(clean_for_iam(self._stack['Name']), 25),
            shorten_name(clean_for_iam(self._name_for_iam), 25)
        )
        for try_ in range(20):
            username = base_username + ("+%s" % try_ if try_ else "")
            try:
                self.iam.create_user(UserName=username, Path=IAM_PATH)
            except ClientError as e:
                if e.response.get('Error', {}).get('Code') == 'EntityAlreadyExists':
                    LOG.debug(
                        "IAM user %s already exists, trying another name",
                        username
                    )
                    # user already exists, try the next one
                    pass
                else:
                    raise
            else:
                LOG.debug("Created IAM user %s", username)
                break
        else:
            raise ValueError("Couldn't find an unused IAM user name.")

        LOG.debug("Adding the user to the group and attaching a policy")
        self.iam.add_user_to_group(GroupName=group_name, UserName=username)
        self.iam.put_user_policy(
            PolicyName=IAM_USER_POLICY_NAME,
            PolicyDocument=self._iam_policy_document(
                self._stack['Arn'], IAM_USER_POLICY_TIMEOUT),
            UserName=username
        )

        LOG.debug("Creating an access key")
        self.access_key = self.iam.create_access_key(
            UserName=username
        )['AccessKey']

    def setup_target_machine(self, args):
        """
        Setups the target machine by copying over the credentials and starting
        the installation process.
        """

        remote_script = REMOTE_SCRIPT % {
            'agent_installer_url':
                self._prov_params['AgentInstallerUrl'],
            'preconfig':
                self._to_ruby_yaml(self._pre_config_document(args)),
            'assets_download_bucket':
                self._prov_params['Parameters']['assets_download_bucket']
        }

        if args.local:
            LOG.debug("Running the installer locally")
            subprocess.check_call(["/bin/sh", "-c", remote_script])
        else:
            LOG.debug("Connecting to the target machine to run the installer.")
            self.ssh(args, remote_script)

    def ssh(self, args, remote_script):
        """
        Runs a (sh) script on a remote machine via SSH.
        """

        if platform.system() == 'Windows':
            try:
                script_file = tempfile.NamedTemporaryFile("wt", delete=False)
                script_file.write(remote_script)
                script_file.close()
                if args.ssh:
                    call = args.ssh
                else:
                    call = 'plink'
                    if args.username:
                        call += ' -l "%s"' % args.username
                    if args.private_key:
                        call += ' -i "%s"' % args.private_key
                    call += ' "%s"' % self._use_address
                    call += ' -m'
                call += ' "%s"' % script_file.name

                subprocess.check_call(call, shell=True)
            finally:
                os.remove(script_file.name)
        else:
            if args.ssh:
                call = shlex.split(str(args.ssh))
            else:
                call = ['ssh', '-tt']
                if args.username:
                    call.extend(['-l', args.username])
                if args.private_key:
                    call.extend(['-i', args.private_key])
                call.append(self._use_address)

            remote_call = ["/bin/sh", "-c", remote_script]
            call.append(" ".join(shlex_quote(word) for word in remote_call))
            subprocess.check_call(call)

    def _pre_config_document(self, args):
        parameters = dict(
            stack_id=self._stack['StackId'],
            **self._prov_params["Parameters"]
        )
        if self.access_key:
            parameters['access_key_id'] = self.access_key['AccessKeyId']
            parameters['secret_access_key'] = \
                self.access_key['SecretAccessKey']
        if self._use_hostname:
            parameters['hostname'] = self._use_hostname
        if args.private_ip:
            parameters['private_ip'] = args.private_ip
        if args.public_ip:
            parameters['public_ip'] = args.public_ip
        parameters['import'] = args.infrastructure_class == 'ec2'
        LOG.debug("Using pre-config: %r", parameters)
        return parameters

    @staticmethod
    def _iam_policy_document(arn, timeout=None):
        statement = {
            "Action": "opsworks:RegisterInstance",
            "Effect": "Allow",
            "Resource": arn,
        }
        if timeout is not None:
            valid_until = datetime.datetime.utcnow() + timeout
            statement["Condition"] = {
                "DateLessThan": {
                    "aws:CurrentTime":
                        valid_until.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }
        policy_document = {
            "Statement": [statement],
            "Version": "2012-10-17"
        }
        return json.dumps(policy_document)

    @staticmethod
    def _to_ruby_yaml(parameters):
        return "\n".join(":%s: %s" % (k, json.dumps(v))
                         for k, v in sorted(parameters.items()))


def clean_for_iam(name):
    """
    Cleans a name to fit IAM's naming requirements.
    """

    return re.sub(r'[^A-Za-z0-9+=,.@_-]+', '-', name)


def shorten_name(name, max_length):
    """
    Shortens a name to the given number of characters.
    """

    if len(name) <= max_length:
        return name
    q, r = divmod(max_length - 3, 2)
    return name[:q + r] + "..." + name[-q:]
