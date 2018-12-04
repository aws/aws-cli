
from awscli.customizations.emr.createcluster import CreateCluster
from awscli.customizations.emr.exceptions import InvalidBooleanConfigError
from awscli.customizations.emr.ssh import Get
from awscli.customizations.emr.ssh import Put
from awscli.customizations.emr.ssh import SSH
from awscli.customizations.emr.ssh import Socks
from awscli.testutils import BaseAWSHelpOutputTest
import mock
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


INSTANCE_GROUPS_ARG = (
    'InstanceGroupType=MASTER,Name=MASTER,'
    'InstanceCount=1,InstanceType=m1.large ')

CREATE_CLUSTER_CMD = (
    "emr create-cluster --ami-version 3.1.0 --instance-groups %s" %
    INSTANCE_GROUPS_ARG)

DEFAULT_CONFIGS = {
    'service_role': 'my_default_emr_role',
    'instance_profile': 'my_default_ec2_role',
    'log_uri': 's3://my_default_logs',
    'enable_debugging': 'True',
    'key_name': 'my_default_key',
    'key_pair_file': '/home/my_default_key_pair.pem'
}

DEBUG_FALSE_CONFIGS = {
    'enable_debugging': 'False'
}

BAD_BOOLEAN_VALUE_CONFIGS = {
    'enable_debugging': 'False1'
}

BAD_CONFIGS = {
    'service_role1': 'my_default_emr_role',
    'instance_profiile': 'my_default_ec2_role',
    'log_uri_': 's3://my_default_logs',
    'enable_debugging*': 'True',
    'keyname': 'my_default_key',
    'key_pairrr_file': '/home/my_default_key_pair.pem'
}

TEST_CLUSTER_ID = "j-227H3PFKLBOBP"
TEST_SRC_PATH = "/home/my_src"

SSH_CMD = ('emr ssh --cluster-id %s' % TEST_CLUSTER_ID)
SOCKS_CMD = ('emr socks --cluster-id %s' % TEST_CLUSTER_ID)
GET_CMD = ('emr get --cluster-id %s --src %s' % (TEST_CLUSTER_ID,
                                                 TEST_SRC_PATH))
PUT_CMD = ('emr put --cluster-id %s --src %s' % (TEST_CLUSTER_ID,
                                                 TEST_SRC_PATH))

CREATE_DEFAULT_ROLES_CMD = 'emr create-default-roles'


class TestCreateCluster(BaseAWSCommandParamsTest):

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_with_configs(self, mock_run_main_command):
        self.set_configs(DEFAULT_CONFIGS)
        self._run_cmd_w_mock(mock_run_main_command, CREATE_CLUSTER_CMD)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_args_for_default_configs(parsed_args)

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_with_configs_and_other_ec2_attributes(self,
                                                   mock_run_main_command):
        self.set_configs(DEFAULT_CONFIGS)
        cmd = CREATE_CLUSTER_CMD \
            + ' --ec2-attributes AvailabilityZone=us-east-1e'
        self._run_cmd_w_mock(mock_run_main_command, cmd)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_args_for_default_configs(parsed_args)

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_enable_debugging_false(self, mock_run_main_command):
        self.set_configs(DEBUG_FALSE_CONFIGS)
        self._run_cmd_w_mock(mock_run_main_command, CREATE_CLUSTER_CMD)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_enable_debugging(parsed_args, False)

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_with_bad_configs(self, mock_run_main_command):
        self.set_configs(BAD_CONFIGS)
        self._run_cmd_w_mock(mock_run_main_command, CREATE_CLUSTER_CMD)
        parsed_args = mock_run_main_command.call_args[0][0]
        self.assertFalse(getattr(parsed_args, 'service_role', None))
        self.assertFalse(getattr(parsed_args, 'log_uri', None))
        self.assertFalse(parsed_args.enable_debugging)
        self.assertFalse(parsed_args.no_enable_debugging)
        self.assertFalse(getattr(parsed_args, 'ec2-attributes', None))

    def test_with_bad_boolean_value(self):
        self.set_configs(BAD_BOOLEAN_VALUE_CONFIGS)
        cmd = CREATE_CLUSTER_CMD
        expect_error_msg = ("\n%s\n" % InvalidBooleanConfigError.fmt.format(
            config_value='False1', config_key='enable_debugging',
            profile_var_name='default'))
        result = self.run_cmd(cmd, 255)
        self.assertEquals(expect_error_msg, result[1])

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_ignore_role_configs_when_use_default_roles(self,
                                                        mock_run_main_command):
        self.set_configs(DEFAULT_CONFIGS)
        cmd = CREATE_CLUSTER_CMD + '--use-default-roles'
        self._run_cmd_w_mock(mock_run_main_command, cmd)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_enable_debugging(parsed_args, True)
        self._assert_log_uri(parsed_args, 's3://my_default_logs')
        self._assert_ec2_attributes(parsed_args, 'my_default_key')

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_with_configs_and_overriding_options(self, mock_run_main_command):
        self.set_configs(DEFAULT_CONFIGS)
        cmd = CREATE_CLUSTER_CMD + \
            ' --service-role my_emr_role --log-uri s3://my_logs' \
            ' --ec2-attributes KeyName=my_key,' \
            'InstanceProfile=my_ec2_role --no-enable-debugging'
        self._run_cmd_w_mock(mock_run_main_command, cmd)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_enable_debugging(parsed_args, False)
        self._assert_log_uri(parsed_args, 's3://my_logs')
        self._assert_service_role(parsed_args, 'my_emr_role')
        self._assert_ec2_attributes(parsed_args, 'my_key', 'my_ec2_role')

    @mock.patch.object(CreateCluster, '_run_main_command')
    def test_with_configs_and_overriding_ec2_attributes(self,
                                                        mock_run_main_command):
        self.set_configs(DEFAULT_CONFIGS)
        cmd = CREATE_CLUSTER_CMD \
            + ' --ec2-attributes AvailabilityZone=us-east-1e,'\
            'KeyName=my_key'
        self._run_cmd_w_mock(mock_run_main_command, cmd)
        parsed_args = mock_run_main_command.call_args[0][0]
        self._assert_enable_debugging(parsed_args, True)
        self._assert_log_uri(parsed_args, 's3://my_default_logs')
        self._assert_service_role(parsed_args, 'my_default_emr_role')
        self._assert_ec2_attributes(
            parsed_args, 'my_key', 'my_default_ec2_role')

    def _run_cmd_w_mock(self, mock_run_main_command, cmd, return_value=0):
        mock_run_main_command.return_value = return_value
        self.run_cmd(cmd, return_value)

    def _assert_args_for_default_configs(self, parsed_args):
        self._assert_enable_debugging(parsed_args, True)
        self._assert_log_uri(parsed_args, 's3://my_default_logs')
        self._assert_service_role(parsed_args, 'my_default_emr_role')
        self._assert_ec2_attributes(
            parsed_args, 'my_default_key', 'my_default_ec2_role')

    def _assert_enable_debugging(self, parsed_args, value):
        if value:
            self.assertTrue(parsed_args.enable_debugging)
            self.assertFalse(parsed_args.no_enable_debugging)
        else:
            self.assertFalse(parsed_args.enable_debugging)
            self.assertTrue(parsed_args.no_enable_debugging)

    def _assert_ec2_attributes(self, parsed_args, key_name=None,
                               instance_profile=None):
        if key_name:
            self.assertEqual(
                parsed_args.ec2_attributes['KeyName'], key_name)
        if instance_profile:
            self.assertEqual(
                parsed_args.ec2_attributes['InstanceProfile'],
                instance_profile)

    def _assert_log_uri(self, parsed_args, value):
        self.assertEqual(parsed_args.log_uri, value)

    def _assert_service_role(self, parsed_args, value):
        self.assertEqual(parsed_args.service_role, value)


class TestSSHBasedCommands(BaseAWSCommandParamsTest):

    @mock.patch.object(SSH, '_run_main_command')
    def test_ssh_with_configs(self, mock_run_main_command):
        self._test_cmd_with_configs(mock_run_main_command, SSH_CMD)

    @mock.patch.object(Socks, '_run_main_command')
    def test_socks_with_configs(self, mock_run_main_command):
        self._test_cmd_with_configs(mock_run_main_command, SOCKS_CMD)

    @mock.patch.object(Get, '_run_main_command')
    def test_get_with_configs(self, mock_run_main_command):
        self._test_cmd_with_configs(mock_run_main_command, GET_CMD)

    @mock.patch.object(Put, '_run_main_command')
    def test_put_with_configs(self, mock_run_main_command):
        self._test_cmd_with_configs(mock_run_main_command, PUT_CMD)

    @mock.patch.object(SSH, '_run_main_command')
    def test_ssh_with_configs_and_overriding_key(self, mock_run_main_command):
        cmd = SSH_CMD + " --key-pair-file /home/my_key_pair.pem"
        self._test_cmd_with_configs(mock_run_main_command, cmd,
                                    '/home/my_key_pair.pem')

    def _test_cmd_with_configs(self, mock_run_main_command, cmd,
                               key_pair_file_to_assert=''
                               '/home/my_default_key_pair.pem'):
        self.set_configs(DEFAULT_CONFIGS)
        mock_run_main_command.return_value = 0
        self.run_cmd(cmd, 0)
        call_args = mock_run_main_command.call_args
        self.assertEqual(
            call_args[0][0].key_pair_file, key_pair_file_to_assert)


class TestHelpOutput(BaseAWSHelpOutputTest):

    def test_not_override_required_options(self):
        scoped_config = self.session.get_scoped_config()
        scoped_config['emr'] = DEFAULT_CONFIGS
        self.driver.main(['emr', 'ssh', 'help'])
        self.assert_contains('--key-pair-file <value>')
        self.assert_not_contains('[--key-pair-file <value>]')


class TestCreateDefaultRoles(BaseAWSCommandParamsTest):

    def test_roles_updated_if_not_present(self):
        self.run_cmd(CREATE_DEFAULT_ROLES_CMD, expected_rc=0)

        call_args_list = self.mock_update_config.call_args_list

        keys = [x[0][0] for x in call_args_list]
        self.assertTrue('instance_profile' in keys)
        self.assertTrue('service_role' in keys)

    def test_roles_not_updated_if_present(self):
        self.set_configs(DEFAULT_CONFIGS)
        self.run_cmd(CREATE_DEFAULT_ROLES_CMD, expected_rc=0)

        call_args_list = self.mock_update_config.call_args_list

        self.assertFalse(call_args_list)

if __name__ == "__main__":
    unittest.main()
