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

import argparse
import datetime
import json
import mock

from awscli.customizations import opsworks
from awscli.testutils import unittest


class TestOpsWorksBase(unittest.TestCase):
    def setUp(self):
        self.mock_session = mock.Mock()
        self.register = opsworks.OpsWorksRegister(self.mock_session)

        # stop the clock while testing
        self.datetime_patcher = mock.patch.object(
            opsworks.datetime, "datetime",
            mock.Mock(wraps=datetime.datetime)
        )
        mocked_datetime = self.datetime_patcher.start()
        mocked_datetime.utcnow.return_value = datetime.datetime(
            2013, 8, 9, 23, 42)

    def tearDown(self):
        self.datetime_patcher.stop()


class TestOpsWorksRegister(TestOpsWorksBase):
    """Tests for functionality independent of the infrastructure class."""

    def _build_args(self, **kwargs):
        return argparse.Namespace(**dict({
            "hostname": None,
            "private_ip": None,
            "public_ip": None,
            "local": False,
            "username": None,
            "private_key": None,
            "ssh": None,
            "target": None,
        }, **kwargs))

    def test_create_clients_simple(self):
        """Should create clients without additional parameters by default."""

        self.register._create_clients(
            self._build_args(), argparse.Namespace())
        self.mock_session.create_client.assert_has_calls([
            mock.call("iam"),
            mock.call("opsworks"),
        ])

    def test_create_clients_with_region(self):
        """Should pass region names to OpsWorks, but not to IAM clients."""

        self.register._create_clients(
            self._build_args(), argparse.Namespace(region="mars-east-1"))
        self.mock_session.create_client.assert_has_calls([
            mock.call("iam"),
            mock.call("opsworks", region_name="mars-east-1"),
        ])

    def test_create_clients_with_opsworks_endpoint_url(self):
        """Should pass endpoints to OpsWorks, but not to IAM clients."""

        self.register._create_clients(
            self._build_args(), argparse.Namespace(endpoint_url="http://xxx/"))
        self.mock_session.create_client.assert_has_calls([
            mock.call("iam"),
            mock.call("opsworks", endpoint_url="http://xxx/"),
        ])

    @mock.patch.object(opsworks, "platform")
    def test_prevalidate_arguments_invalid_hostnames(self, mock_platform):
        """Should only accept valid hostnames."""

        mock_platform.system.return_value = "Linux"
        self.register.prevalidate_arguments(
            self._build_args(
                infrastructure_class="on-premises",
                hostname=None,
                local=True))
        self.register.prevalidate_arguments(
            self._build_args(
                infrastructure_class="on-premises",
                hostname="good-hostname",
                local=True))
        self.register.prevalidate_arguments(
            self._build_args(
                infrastructure_class="on-premises",
                hostname="AlsoAGoodHostname456", local=True))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    infrastructure_class="on-premises",
                    hostname="-bad-hostname",
                    local=True))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    infrastructure_class="on-premises",
                    hostname="f.q.d.n",
                    local=True))

    @mock.patch.object(opsworks, "platform")
    def test_prevalidate_arguments_local_vs_remote(self, mock_platform):
        """Shouldn't allow local and remote mode at the same time."""

        mock_platform.system.return_value = "Linux"
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(self._build_args(
                infrastructure_class="on-premises",
                hostname=None, target=None, local=False))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(self._build_args(
                infrastructure_class="on-premises",
                hostname=None, target="HOSTNAME", local=True))
        self.register.prevalidate_arguments(self._build_args(
            infrastructure_class="on-premises",
            hostname=None, target="HOSTNAME", local=False))
        self.register.prevalidate_arguments(self._build_args(
            infrastructure_class="on-premises",
            hostname=None, target=None, local=True))

        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(self._build_args(
                infrastructure_class="ec2",
                hostname=None, target=None, local=False))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(self._build_args(
                infrastructure_class="ec2",
                hostname=None, target="HOSTNAME", local=True))
        self.register.prevalidate_arguments(self._build_args(
            infrastructure_class="ec2",
            hostname=None, target="HOSTNAME", local=False))
        self.register.prevalidate_arguments(self._build_args(
            infrastructure_class="ec2",
            hostname=None, target=None, local=True))

    @mock.patch.object(opsworks, "platform")
    def test_prevalidate_arguments_local_linux_only(self, mock_platform):
        """Shouldn't allow local and remote mode at the same time."""

        mock_platform.system.return_value = "Linux"
        self.register.prevalidate_arguments(self._build_args(
            infrastructure_class="on-premises", target=None, local=True))
        with self.assertRaises(ValueError):
            mock_platform.system.return_value = "Windows"
            self.register.prevalidate_arguments(self._build_args(
                infrastructure_class="on-premises", target=None, local=True))

    def test_prevalidate_arguments_ssh_override(self):
        """Should not allow --override-ssh and other SSH options."""

        self.register.prevalidate_arguments(self._build_args(
            ssh="telnet", infrastructure_class="ec2", target="i-12345678"
        ))
        self.register.prevalidate_arguments(
            self._build_args(
                username="root", private_key="id_rsa",
                infrastructure_class="ec2", target="1.2.3.4"))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    ssh="telnet", username="root", infrastructure_class="ec2",
                    target="1.2.3.4"))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    ssh="telnet", private_key="id_rsa",
                    infrastructure_class="ec2", target="1.2.3.4"))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    ssh="telnet", username="root", private_key="id_rsa",
                    infrastructure_class="ec2", target="1.2.3.4"))

    def test_create_iam_entities_simple(self):
        """Basic IAM side-effects.

        Should create a group with a user, and an access key."""

        with mock.patch.object(self.register, "iam", create=True) as mock_iam:
            self.register._stack = dict(
                StackId="STACKID", Name="STACKNAME", Arn="ARN")
            self.register._name_for_iam = "HOSTNAME"

            self.register.create_iam_entities()

            mock_iam.create_group.assert_any_call(
                Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-HOSTNAME")
            mock_iam.add_user_to_group.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME",
                GroupName="OpsWorks-STACKID")
            mock_iam.create_access_key.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME")

    def test_create_iam_entities_group_exists(self):
        """Should reuse an existing group."""

        with mock.patch.object(self.register, "iam", create=True) as mock_iam:
            self.register._stack = dict(
                StackId="STACKID", Name="STACKNAME", Arn="ARN")
            self.register._name_for_iam = "HOSTNAME"
            mock_iam.create_group.side_effect = opsworks.ClientError(
                "EntityAlreadyExists", None, None, None, None)

            self.register.create_iam_entities()

            mock_iam.create_group.assert_any_call(
                Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-HOSTNAME")
            mock_iam.add_user_to_group.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME",
                GroupName="OpsWorks-STACKID")
            mock_iam.create_access_key.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME")

    def test_create_iam_entities_user_exists(self):
        """Should use an alternate username if the preferred one is taken."""

        with mock.patch.object(self.register, "iam", create=True) as mock_iam:
            self.register._stack = dict(
                StackId="STACKID", Name="STACKNAME", Arn="ARN")
            self.register._name_for_iam = "HOSTNAME"
            mock_iam.create_user = mock.Mock(
                side_effect=[
                    opsworks.ClientError(
                        "EntityAlreadyExists", None, None, None, None),
                    opsworks.ClientError(
                        "EntityAlreadyExists", None, None, None, None),
                    None
                ])

            self.register.create_iam_entities()

            mock_iam.create_group.assert_any_call(
                Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-HOSTNAME")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/",
                UserName="OpsWorks-STACKNAME-HOSTNAME+1")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/",
                UserName="OpsWorks-STACKNAME-HOSTNAME+2")
            mock_iam.add_user_to_group.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME+2",
                GroupName="OpsWorks-STACKID")
            mock_iam.create_access_key.assert_any_call(
                UserName="OpsWorks-STACKNAME-HOSTNAME+2")

    def test_create_iam_entities_long_names(self):
        """Should shorten IAM entity names to a valid size."""

        long_hostname = "hostname1.very-long-domain-name.within.company.tld"
        shortened_username = \
            "OpsWorks-long-stack-...ork-as-well-hostname1.v...company.tld"

        with mock.patch.object(self.register, "iam", create=True) as mock_iam:
            self.register._stack = dict(
                StackId="STACKID", Name="long stack names should work as well",
                Arn="ARN")
            self.register._name_for_iam = long_hostname

            self.register.create_iam_entities()

            mock_iam.create_group.assert_any_call(
                Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
            mock_iam.create_user.assert_any_call(
                Path="/AWS/OpsWorks/",
                UserName=shortened_username)
            mock_iam.add_user_to_group.assert_any_call(
                UserName=shortened_username,
                GroupName="OpsWorks-STACKID")
            mock_iam.create_access_key.assert_any_call(
                UserName=shortened_username)

    def test_validate_unique_hostname(self):
        """Should detect duplicate host names in the stack early."""

        self.register._stack = {"StackId": "STACKID"}
        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_opsworks.describe_instances.return_value = {
                "Instances": [dict(Hostname="duplicated-hostname")]
            }
            self.register.validate_arguments(
                mock.Mock(hostname="good-hostname"))
            with self.assertRaises(ValueError):
                self.register.validate_arguments(
                    mock.Mock(hostname="duplicated-hostname"))
            with self.assertRaises(ValueError):
                self.register.validate_arguments(
                    mock.Mock(hostname="DUPliCATED-HOSTNAME"))

    @mock.patch.object(opsworks, "tempfile")
    @mock.patch.object(opsworks, "platform")
    @mock.patch.object(opsworks, "subprocess")
    @mock.patch.object(opsworks, "os")
    def test_ssh_windows(
            self, mock_os, mock_subprocess, mock_platform, mock_tempfile):
        """Should use plink on Windows correctly."""

        mock_platform.system.return_value = "Windows"
        self.register._use_address = "ip"
        mock_file = mock.Mock()
        mock_tempfile.NamedTemporaryFile.return_value = mock_file
        mock_file.name = "tmpfilename"

        self.register.ssh(self._build_args(), "script")
        mock_subprocess.check_call.assert_called_with(
            'plink "ip" -m "tmpfilename"', shell=True)

        self.register.ssh(self._build_args(username="foo"), "script")
        mock_subprocess.check_call.assert_called_with(
            'plink -l "foo" "ip" -m "tmpfilename"', shell=True)

        self.register.ssh(self._build_args(private_key="bar"), "script")
        mock_subprocess.check_call.assert_called_with(
            'plink -i "bar" "ip" -m "tmpfilename"', shell=True)

        self.register.ssh(
            self._build_args(username="foo", private_key="bar"),
            "script")
        mock_subprocess.check_call.assert_called_with(
            'plink -l "foo" -i "bar" "ip" -m "tmpfilename"', shell=True)

        self.register.ssh(self._build_args(ssh="plink -agent ip -m"), "script")
        mock_subprocess.check_call.assert_called_with(
            'plink -agent ip -m "tmpfilename"', shell=True)

    @mock.patch.object(opsworks, "platform")
    @mock.patch.object(opsworks, "subprocess")
    def test_ssh_nix(self, mock_subprocess, mock_platform):
        """Should use ssh on non-windows correctly."""

        mock_platform.system.return_value = "Linux"
        self.register._use_address = "ip"

        self.register.ssh(self._build_args(), "script")
        mock_subprocess.check_call.assert_called_with(
            ["ssh", "-tt", "ip", "/bin/sh -c script"])

        self.register.ssh(self._build_args(username="foo"), "script")
        mock_subprocess.check_call.assert_called_with(
            ["ssh", "-tt", "-l", "foo", "ip", "/bin/sh -c script"])

        self.register.ssh(self._build_args(private_key="bar"), "script")
        mock_subprocess.check_call.assert_called_with(
            ["ssh", "-tt", "-i", "bar", "ip", "/bin/sh -c script"])

        self.register.ssh(self._build_args(username="foo", private_key="bar"),
                          "script")
        mock_subprocess.check_call.assert_called_with(
            ["ssh", "-tt", "-l", "foo", "-i", "bar", "ip", "/bin/sh -c script"]
        )
        self.register.ssh(self._build_args(ssh="ssh -k -l foo 1.2.3.4"),
                          "script")
        mock_subprocess.check_call.assert_called_with(
            ["ssh", "-k", "-l", "foo", "1.2.3.4", "/bin/sh -c script"])

    def test_iam_policy_document(self):
        self.assertEqual(
            json.loads(self.register._iam_policy_document("arn::foo")),
            {
                "Statement": [
                    {
                        "Action": "opsworks:RegisterInstance",
                        "Effect": "Allow",
                        "Resource": "arn::foo",
                    }
                ],
                "Version": "2012-10-17"
            }
        )
        self.assertEqual(
            json.loads(self.register._iam_policy_document(
                "arn::foo", datetime.timedelta(minutes=5)
            )), {
                "Statement": [{
                    "Action": "opsworks:RegisterInstance",
                    "Effect": "Allow",
                    "Resource": "arn::foo",
                    "Condition": {
                        "DateLessThan": {
                            "aws:CurrentTime": "2013-08-09T23:47:00Z"
                        }
                    }
                }],
                "Version": "2012-10-17"
            }
        )

    @mock.patch.object(opsworks, "platform")
    @mock.patch.object(opsworks, "subprocess")
    def test_setup_target_machine_remote_nix(
            self, mock_subprocess, mock_platform):
        """Should setup a remote machine from a non-Windows host correctly."""

        mock_platform.system.return_value = "Linux"
        args = self._build_args(
            infrastructure_class="ec2", hostname="HOSTNAME", local=False
        )
        self.register._stack = {"StackId": "STACKID"}
        self.register._prov_params = {
            "AgentInstallerUrl": "URL",
            "Parameters": {"assets_download_bucket": "xxx"}
        }
        self.register.access_key = {
            "AccessKeyId": "AKIAXXX",
            "SecretAccessKey": "foobarbaz"
        }
        self.register._use_address = "ip"
        self.register._use_hostname = "HOSTNAME"

        self.register.setup_target_machine(args)

        cmd = mock_subprocess.check_call.call_args[0][0]
        self.assertEqual(cmd[0], "ssh")
        self.assertEqual(cmd[1], "-tt")
        self.assertEqual(cmd[2], "ip")
        self.assertRegexpMatches(cmd[3], r"/bin/sh -c ")

    @mock.patch.object(opsworks, "platform")
    @mock.patch.object(opsworks, "subprocess")
    def test_setup_target_machine_remote_windows(
            self, mock_subprocess, mock_platform):
        """Should setup a remote machine from a Windows host correctly."""

        mock_platform.system.return_value = "Windows"
        args = self._build_args(
            infrastructure_class="ec2", hostname="HOSTNAME", local=False
        )
        self.register._stack = {"StackId": "STACKID"}
        self.register._prov_params = {
            "AgentInstallerUrl": "URL",
            "Parameters": {"assets_download_bucket": "xxx"}
        }
        self.register.access_key = {
            "AccessKeyId": "AKIAXXX",
            "SecretAccessKey": "foobarbaz"
        }
        self.register._use_address = "ip"
        self.register._use_hostname = "HOSTNAME"

        self.register.setup_target_machine(args)

        cmd = mock_subprocess.check_call.call_args[0][0]
        self.assertRegexpMatches(cmd, r'^plink ".*" -m ".*"$')

    @mock.patch.object(opsworks, "subprocess")
    def test_setup_target_machine_local(self, mock_subprocess):
        """Should setup the local machine correctly."""

        args = self._build_args(
            infrastructure_class="ec2", local=True
        )
        self.register._stack = {"StackId": "STACKID"}
        self.register._prov_params = {
            "AgentInstallerUrl": "URL",
            "Parameters": {"assets_download_bucket": "xxx"}
        }
        self.register.access_key = {
            "AccessKeyId": "AKIAXXX",
            "SecretAccessKey": "foobarbaz"
        }
        self.register._use_hostname = "HOSTNAME"

        self.register.setup_target_machine(args)

        cmd = mock_subprocess.check_call.call_args[0][0]
        self.assertEqual(cmd[0], "/bin/sh")
        self.assertEqual(cmd[1], "-c")

    def test_pre_config_document_simple(self):
        """Should produce a simple preconfiguration file."""

        self.register._stack = {"StackId": "Foo"}
        self.register._prov_params = {
            "Parameters": {"foo": "Bar", "bar": "Baz"}}
        self.register.access_key = {
            "AccessKeyId": "Bar", "SecretAccessKey": "Baz"}
        self.register._use_hostname = None

        pre_config = self.register._pre_config_document(
            mock.Mock(private_ip=None, public_ip=None)
        )

        self.assertEqual(
            pre_config, {
                "access_key_id": "Bar",
                "bar": "Baz",
                "foo": "Bar",
                "import": False,
                "secret_access_key": "Baz",
                "stack_id": "Foo",
            }
        )

    def test_pre_config_document_full(self):
        """Should produce a complex preconfiguration file."""

        self.register._stack = {"StackId": "Foo"}
        self.register._prov_params = {
            "Parameters": {"foo": "Bar", "bar": "Baz"}}
        self.register.access_key = {
            "AccessKeyId": "Bar", "SecretAccessKey": "Baz"}
        self.register._use_hostname = "HOSTNAME"

        pre_config = self.register._pre_config_document(
            mock.Mock(private_ip="PRIVATEIP", public_ip="PUBLICIP"),
        )

        self.assertEqual(
            pre_config, {
                "access_key_id": "Bar",
                "bar": "Baz",
                "foo": "Bar",
                "hostname": "HOSTNAME",
                "import": False,
                "private_ip": "PRIVATEIP",
                "public_ip": "PUBLICIP",
                "secret_access_key": "Baz",
                "stack_id": "Foo",
            }
        )


class TestOpsWorksRegisterEc2(TestOpsWorksBase):
    """Tests for functionality specific to EC2 instances."""

    def _build_args(self, **kwargs):
        return argparse.Namespace(**dict({
            "hostname": None,
            "infrastructure_class": "ec2",
            "private_ip": None,
            "public_ip": None,
            "local": False,
            "username": None,
            "private_key": None,
            "ssh": None,
            "target": None,
        }, **kwargs))

    @mock.patch.object(opsworks, "subprocess")
    def test_run_main_remote(self, mock_subprocess):
        """Flow test w/ all the expected side-effects for a remote instance."""

        args = self._build_args(stack_id="STACKID", target="i-12345678",
                                local=False)
        parsed_globals = argparse.Namespace()
        mock_ec2 = mock.Mock()
        mock_iam = mock.Mock()
        mock_opsworks = mock.Mock()
        self.mock_session.create_client.side_effect = lambda name, **_: \
            dict(ec2=mock_ec2, iam=mock_iam, opsworks=mock_opsworks)[name]

        mock_opsworks.describe_stacks.return_value = {
            "Stacks": [{
                "Arn": "ARN",
                "Name": "STACKNAME",
                "StackId": "STACKID",
                "Region": "mars-east-1",
            }]
        }
        mock_opsworks.describe_stack_provisioning_parameters.return_value = {
            "AgentInstallerUrl": "URL",
            "Parameters": {
                "assets_download_bucket": "xxx"
            }
        }
        mock_opsworks.describe_instances.return_value = {
            "Instances": []
        }
        mock_ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "PublicIpAddress": "192.0.2.42"
                }]
            }]
        }
        mock_iam.create_access_key.return_value = {
            "AccessKey":
                {"AccessKeyId": "AKIAXXX", "SecretAccessKey": "foobarbaz"}
        }

        self.register._run_main(args, parsed_globals)

        mock_iam.create_user.assert_called_with(
            Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-i-12345678")
        mock_iam.create_group.assert_called_with(
            Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
        mock_iam.add_user_to_group.assert_called_with(
            UserName="OpsWorks-STACKNAME-i-12345678",
            GroupName="OpsWorks-STACKID")
        mock_iam.create_access_key.assert_called_with(
            UserName="OpsWorks-STACKNAME-i-12345678")
        self.assertTrue(mock_subprocess.check_call.calls)

    @mock.patch.object(opsworks, "urlopen")
    @mock.patch.object(opsworks, "subprocess")
    @mock.patch.object(opsworks, "socket")
    @mock.patch.object(opsworks, "platform")
    def test_run_main_local(
            self, mock_platform, mock_socket, mock_subprocess, mock_urlopen):
        """Flow test w/ all the expected side-effects for a local instance."""

        args = self._build_args(stack_id="STACKID", target=None,
                                local=True)
        parsed_globals = argparse.Namespace()
        mock_ec2 = mock.Mock()
        mock_iam = mock.Mock()
        mock_opsworks = mock.Mock()
        mock_platform.system.return_value = "Linux"
        self.mock_session.create_client.side_effect = lambda name, **_: \
            dict(ec2=mock_ec2, iam=mock_iam, opsworks=mock_opsworks)[name]

        mock_opsworks.describe_stacks.return_value = {
            "Stacks": [{
                "Arn": "ARN",
                "Name": "STACKNAME",
                "StackId": "STACKID",
                "Region": "mars-east-1",
            }]
        }
        mock_opsworks.describe_stack_provisioning_parameters.return_value = {
            "AgentInstallerUrl": "URL",
            "Parameters": {
                "assets_download_bucket": "xxx"
            }
        }
        mock_opsworks.describe_instances.return_value = {
            "Instances": []
        }
        mock_iam.create_access_key.return_value = {
            "AccessKey":
                {"AccessKeyId": "AKIAXXX", "SecretAccessKey": "foobarbaz"}
        }
        mock_socket.gethostname.return_value = "HOSTNAME"
        mock_urlopen.return_value.read.return_value = \
            '{"region": "mars-east-1"}'

        self.register._run_main(args, parsed_globals)

        mock_iam.create_user.assert_called_with(
            Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-HOSTNAME")
        mock_iam.create_group.assert_called_with(
            Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
        mock_iam.add_user_to_group.assert_called_with(
            UserName="OpsWorks-STACKNAME-HOSTNAME",
            GroupName="OpsWorks-STACKID")
        mock_iam.create_access_key.assert_called_with(
            UserName="OpsWorks-STACKNAME-HOSTNAME")
        self.assertTrue(mock_subprocess.check_call.calls)

    def test_prevalidate_arguments_no_ips_for_ec2(self):
        """Shouldn't allow overriding IP addresses for EC2."""

        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(
                    target="target", private_ip="private-ip"))
        with self.assertRaises(ValueError):
            self.register.prevalidate_arguments(
                self._build_args(target="target", public_ip="public-ip"))

    @mock.patch.object(opsworks, "urlopen")
    def test_validate_same_region(self, mock_urlopen):
        """Should ensure that the local instance is in the correct region."""

        self.register._stack = {"Region": "mars-east-1"}

        mock_urlopen.return_value.read.return_value = \
            '{"region": "mars-east-1"}'
        self.register.validate_arguments(
            self._build_args(hostname=None, local=True))

        with self.assertRaises(ValueError):
            mock_urlopen.return_value.read.return_value = \
                '{"region": "mars-west-1"}'
            self.register.validate_arguments(
                self._build_args(hostname=None, local=True))

    def test_retrieve_stack_ec2(self):
        """Should retrieve an EC2 stack and the matching instance."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                    }]
                }, {
                    "Instances": [{
                        "InstanceId": "i-9abcdef0",
                        "VpcId": "vpc-123456"
                    }]
                }
                ]
            }
            self.register.retrieve_stack(self._build_args(
                stack_id="STACKID", target="i-12345678"
            ))
            mock_ec2.describe_instances.assert_called_with(
                InstanceIds=["i-12345678"], Filters=[]
            )
            self.assertEqual(
                self.register._ec2_instance["InstanceId"],
                "i-12345678")

    def test_retrieve_stack_vpc(self):
        """Should retrieve an VPC stack and the matching instance."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                    "VpcId": "vpc-123456",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                    }]
                }]
            }
            self.register.retrieve_stack(self._build_args(
                stack_id="STACKID", target="i-12345678"
            ))
            mock_ec2.describe_instances.assert_called_with(
                InstanceIds=["i-12345678"],
                Filters=[{
                    "Name": "vpc-id",
                    "Values": ["vpc-123456"]
                }])
            self.assertEqual(
                self.register._ec2_instance["InstanceId"],
                "i-12345678")

    def test_retrieve_stack_ec2_instance_id(self):
        """Should find an EC2 instance by instance ID."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                    }]
                }]
            }
            self.register.retrieve_stack(self._build_args(
                stack_id="STACKID", target="i-12345678"
            ))
            mock_ec2.describe_instances.assert_called_with(
                InstanceIds=["i-12345678"], Filters=[]
            )
            self.assertEqual(
                self.register._ec2_instance["InstanceId"],
                "i-12345678")

    def test_retrieve_stack_target_ip_address(self):
        """Should find an EC2 instance by IP address."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                        "PrivateIpAddress": "1.2.3.4"
                    }, {
                        "InstanceId": "i-9abcdef0",
                        "PrivateIpAddress": "1.2.3.5"
                    }]
                }]
            }
            self.register.retrieve_stack(self._build_args(
                stack_id="STACKID", target="1.2.3.4"
            ))
            mock_ec2.describe_instances.assert_called_with(Filters=[])
            self.assertEqual(
                self.register._ec2_instance["InstanceId"],
                "i-12345678")

    def test_retrieve_stack_target_name(self):
        """Should find an EC2 instance by name."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                        "PrivateIpAddress": "1.2.3.4"
                    }]
                }]
            }
            self.register.retrieve_stack(self._build_args(
                stack_id="STACKID", target="db-master"
            ))
            mock_ec2.describe_instances.assert_called_with(
                Filters=[{"Name": "tag:Name", "Values": ["db-master"]}]
            )
            self.assertEqual(
                self.register._ec2_instance["InstanceId"],
                "i-12345678")

    def test_retrieve_stack_target_none(self):
        """Should complain if it cannot find matching instances."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": []
            }
            with self.assertRaises(ValueError):
                self.register.retrieve_stack(
                    self._build_args(
                        stack_id="STACKID", target="some-instance"))

    def test_retrieve_stack_target_too_many(self):
        """Should complain if it finds too many matching instances."""

        with mock.patch.object(
                self.register, "opsworks", create=True) as mock_opsworks:
            mock_ec2 = mock.Mock()
            self.mock_session.create_client.return_value = mock_ec2
            mock_opsworks.describe_stacks.return_value = {
                "Stacks": [{
                    "StackId": "STACKID",
                    "Region": "mars-east-1",
                }]
            }
            mock_ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345678",
                        "PrivateIpAddress": "1.2.3.4"
                    }, {
                        "InstanceId": "i-9abcdef0",
                        "PrivateIpAddress": "1.2.3.5"
                    }]
                }]
            }
            with self.assertRaises(ValueError):
                self.register.retrieve_stack(self._build_args(
                    stack_id="STACKID", target="some-instance"
                ))

    def test_determine_details_simple(self):
        """Should determine names and address for a basic EC2 instance."""

        self.register._ec2_instance = {
            "PublicIpAddress": "192.0.2.42"
        }
        self.register._use_address = None
        self.register.determine_details(self._build_args(
            target="i-12345678"
        ))
        self.assertEqual(self.register._use_address, "192.0.2.42")
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "i-12345678")

    def test_determine_details_with_hostname(self):
        """Should determine names and address with a hostname override."""

        self.register._ec2_instance = {
            "PublicIpAddress": "192.0.2.42"
        }
        self.register._use_address = None
        self.register.determine_details(self._build_args(
            infrastructure_class="ec2",
            hostname="prettyhostname"
        ))
        self.assertEqual(self.register._use_address, "192.0.2.42")
        self.assertEqual(self.register._use_hostname, "prettyhostname")
        self.assertEqual(self.register._name_for_iam, "prettyhostname")

    def test_determine_details_private_ip_only(self):
        """Should determine names and address for a EC2 instance without a
        public IP address."""

        self.register._ec2_instance = {
            "PrivateIpAddress": "192.0.2.42"
        }
        self.register._use_address = None
        self.register.determine_details(self._build_args(
            target="i-12345678"
        ))
        self.assertEqual(self.register._use_address, "192.0.2.42")
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "i-12345678")

    @mock.patch.object(opsworks, "socket")
    def test_determine_details_local_simple(self, mock_socket):
        """Should determine names and address for the local EC2 instance."""

        mock_socket.gethostname.return_value = "HOSTNAME"
        self.register._use_address = None
        self.register.determine_details(self._build_args(
            hostname=None, local=True
        ))
        self.assertEqual(self.register._use_address, None)
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "HOSTNAME")

    def test_determine_details_local_with_hostname(self):
        """Should determine names and address for the local EC2 instance with
        a hostname override."""

        self.register._use_address = None
        self.register.determine_details(self._build_args(
            hostname="prettyhostname", local=True
        ))
        self.assertEqual(self.register._use_address, None)
        self.assertEqual(self.register._use_hostname, "prettyhostname")
        self.assertEqual(self.register._name_for_iam, "prettyhostname")

    def test_determine_details_given_address(self):
        """Should use a given address."""

        self.register._use_address = "192.0.2.42"
        self.register.determine_details(self._build_args(
            target="192.0.2.42"
        ))
        self.assertEqual(self.register._use_address, "192.0.2.42")
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "192.0.2.42")


class TestOpsWorksRegisterOnPremises(TestOpsWorksBase):
    """Tests for functionality specific to on-premises instances."""

    def _build_args(self, **kwargs):
        return argparse.Namespace(**dict({
            "hostname": None,
            "infrastructure_class": "on-premises",
            "private_ip": None,
            "public_ip": None,
            "local": False,
            "username": None,
            "private_key": None,
            "ssh": None,
            "target": None,
        }, **kwargs))

    @mock.patch.object(opsworks, "subprocess")
    def test_run_main(self, mock_subprocess):
        """Flow test w/ all the expected side-effects for a remote instance."""

        args = self._build_args(stack_id="STACKID", target="HOSTNAME",
                                local=False, ssh=None, hostname=None,
                                private_ip=None, public_ip=None)
        parsed_globals = argparse.Namespace()
        mock_ec2 = mock.Mock()
        mock_iam = mock.Mock()
        mock_opsworks = mock.Mock()
        self.mock_session.create_client.side_effect = lambda name, **_: \
            dict(ec2=mock_ec2, iam=mock_iam, opsworks=mock_opsworks)[name]

        mock_opsworks.describe_stacks.return_value = {
            "Stacks": [{
                "Arn": "ARN",
                "Name": "STACKNAME",
                "StackId": "STACKID",
                "Region": "mars-east-1",
            }]
        }
        mock_opsworks.describe_stack_provisioning_parameters.return_value = {
            "AgentInstallerUrl": "URL",
            "Parameters": {
                "assets_download_bucket": "xxx"
            }
        }
        mock_opsworks.describe_instances.return_value = {
            "Instances": []
        }
        mock_iam.create_access_key.return_value = {
            "AccessKey":
            {"AccessKeyId": "AKIAXXX", "SecretAccessKey": "foobarbaz"}}

        self.register._run_main(args, parsed_globals)

        mock_iam.create_user.assert_called_with(
            Path="/AWS/OpsWorks/", UserName="OpsWorks-STACKNAME-HOSTNAME")
        mock_iam.create_group.assert_called_with(
            Path="/AWS/OpsWorks/", GroupName="OpsWorks-STACKID")
        mock_iam.add_user_to_group.assert_called_with(
            UserName="OpsWorks-STACKNAME-HOSTNAME",
            GroupName="OpsWorks-STACKID")
        mock_iam.create_access_key.assert_called_with(
            UserName="OpsWorks-STACKNAME-HOSTNAME")
        self.assertTrue(mock_subprocess.check_call.calls)

    def test_determine_details_simple(self):
        """Should determine names and address for a basic instance."""

        self.register._use_address = None
        self.register.determine_details(self._build_args(
            infrastructure_class="on-premises",
            target="HOSTNAME", hostname=None, local=False
        ))
        self.assertEqual(self.register._use_address, "HOSTNAME")
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "HOSTNAME")

    def test_determine_details_with_hostname(self):
        """Should determine names and address with a hostname override."""

        self.register._use_address = None
        self.register.determine_details(self._build_args(
            infrastructure_class="on-premises",
            target="HOSTNAME", hostname="prettyhostname", local=False
        ))
        self.assertEqual(self.register._use_address, "HOSTNAME")
        self.assertEqual(self.register._use_hostname, "prettyhostname")
        self.assertEqual(self.register._name_for_iam, "prettyhostname")

    @mock.patch.object(opsworks, "socket")
    def test_determine_details_local_simple(self, mock_socket):
        """Should determine names and address for the local instance."""

        mock_socket.gethostname.return_value = "HOSTNAME"
        self.register._use_address = None
        self.register.determine_details(self._build_args(
            infrastructure_class="on-premises",
            hostname=None, local=True
        ))
        self.assertEqual(self.register._use_address, None)
        self.assertEqual(self.register._use_hostname, None)
        self.assertEqual(self.register._name_for_iam, "HOSTNAME")

    def test_determine_details_local_with_hostname(self):
        """Should determine names and address for the local instance with a
        hostname override."""

        self.register._use_address = None
        self.register.determine_details(self._build_args(
            infrastructure_class="on-premises",
            hostname="prettyhostname", local=True
        ))
        self.assertEqual(self.register._use_address, None)
        self.assertEqual(self.register._use_hostname, "prettyhostname")
        self.assertEqual(self.register._name_for_iam, "prettyhostname")


class TestOpsWorksHelpers(unittest.TestCase):
    """Tests for helper functions."""

    def test_clean_for_iam(self):
        """Should sanitize strings for IAM."""

        self.assertEqual(opsworks.clean_for_iam("foobar"), "foobar")
        self.assertEqual(opsworks.clean_for_iam("foo bar 123"), "foo-bar-123")
        self.assertEqual(opsworks.clean_for_iam("baz&@%#^*$bar"), "baz-@-bar")

    def test_shorten_name(self):
        """Should shorten strings by introducing ellipses."""

        # short
        self.assertEqual(opsworks.shorten_name("1234", 5), "1234")
        self.assertEqual(opsworks.shorten_name("12345", 5), "12345")
        # odd number of characters
        self.assertEqual(opsworks.shorten_name("123456789", 5), "1...9")
        self.assertEqual(opsworks.shorten_name("123456789", 6), "12...9")
        self.assertEqual(opsworks.shorten_name("123456789", 7), "12...89")
        self.assertEqual(opsworks.shorten_name("123456789", 8), "123...89")
        self.assertEqual(opsworks.shorten_name("123456789", 9), "123456789")
        self.assertEqual(opsworks.shorten_name("123456789", 10), "123456789")
        # even number of characters
        self.assertEqual(opsworks.shorten_name("1234567890", 5), "1...0")
        self.assertEqual(opsworks.shorten_name("1234567890", 6), "12...0")
        self.assertEqual(opsworks.shorten_name("1234567890", 7), "12...90")
        self.assertEqual(opsworks.shorten_name("1234567890", 8), "123...90")
        self.assertEqual(opsworks.shorten_name("1234567890", 9), "123...890")
        self.assertEqual(opsworks.shorten_name("1234567890", 10), "1234567890")
        self.assertEqual(opsworks.shorten_name("1234567890", 11), "1234567890")
