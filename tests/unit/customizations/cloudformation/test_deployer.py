import mock
import botocore.session

from mock import patch, Mock, MagicMock
from botocore.stub import Stubber
from awscli.testutils import unittest
from awscli.customizations.cloudformation.deployer import Deployer, ChangeSetResult
from awscli.customizations.cloudformation import exceptions


class TestDeployer(unittest.TestCase):

    def setUp(self):
        client = botocore.session.get_session().create_client('cloudformation',
                                                              region_name="us-east-1")
        self.stub_client = Stubber(client)

        self.changeset_prefix = "some-changeset-prefix"
        self.deployer = Deployer(client, self.changeset_prefix)

    def test_has_stack_success(self):
        stack_name = "stack_name"

        expected_params = {
            "StackName": stack_name
        }

        response = {
            "Stacks": [
                make_stack_obj(stack_name)
            ]
        }

        self.stub_client.add_response('describe_stacks', response,
                                      expected_params)

        with self.stub_client:
            response = self.deployer.has_stack(stack_name)
            self.assertTrue(response)

    def test_has_stack_no_stack(self):
        stack_name = "stack_name"
        expected_params = {
            "StackName": stack_name
        }

        # Response contains NO stack
        no_stack_response = {
            "Stacks": []
        }
        self.stub_client.add_response('describe_stacks', no_stack_response,
                                      expected_params)
        with self.stub_client:
            response = self.deployer.has_stack(stack_name)
            self.assertFalse(response)

        # Response is a ClientError with a message that the stack does not exist
        self.stub_client.add_client_error('describe_stacks', "ClientError",
                                          "Stack with id {0} does not exist"
                                          .format(stack_name))
        with self.stub_client:
            response = self.deployer.has_stack(stack_name)
            self.assertFalse(response)

    def test_has_stack_review_in_progress(self):
        stack_name = "stack_name"
        expected_params = {
            "StackName": stack_name
        }

        # Response contains NO stack
        review_in_progress_response = {
            "Stacks": [make_stack_obj(stack_name, "REVIEW_IN_PROGRESS")]
        }
        self.stub_client.add_response('describe_stacks',
                                      review_in_progress_response,
                                      expected_params)
        with self.stub_client:
            response = self.deployer.has_stack(stack_name)
            self.assertFalse(response)

    def test_has_stack_exception(self):
        self.stub_client.add_client_error('describe_stacks', "ValidationError",
                                          "Service is bad")
        with self.stub_client:
            with self.assertRaises(botocore.exceptions.ClientError):
                self.deployer.has_stack("stack_name")

    def test_create_changeset_success(self):
        stack_name = "stack_name"
        template = "template"
        parameters = [
            {"ParameterKey": "Key1", "ParameterValue": "Value"},
            {"ParameterKey": "Key2", "UsePreviousValue": True},
            {"ParameterKey": "Key3", "UsePreviousValue": False},
        ]
        # Parameters that Use Previous Value will be removed on stack creation
        # to either force CloudFormation to use the Default value, or ask user to specify a parameter
        filtered_parameters = [
            {"ParameterKey": "Key1", "ParameterValue": "Value"},
            {"ParameterKey": "Key3", "UsePreviousValue": False},
        ]
        capabilities = ["capabilities"]
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]

        # Case 1: Stack DOES NOT exist
        self.deployer.has_stack = Mock()
        self.deployer.has_stack.return_value = False

        expected_params = {
            "ChangeSetName": botocore.stub.ANY,
            "StackName": stack_name,
            "TemplateBody": template,
            "ChangeSetType": "CREATE",
            "Parameters": filtered_parameters,
            "Capabilities": capabilities,
            "Description": botocore.stub.ANY,
            "RoleARN": role_arn,
            "NotificationARNs": notification_arns
        }

        response = {
            "Id": "changeset ID"
        }

        self.stub_client.add_response("create_change_set", response,
                                      expected_params)
        with self.stub_client:
            result = self.deployer.create_changeset(
                    stack_name, template, parameters, capabilities, role_arn,
                    notification_arns)
            self.assertEquals(response["Id"], result.changeset_id)
            self.assertEquals("CREATE", result.changeset_type)

        # Case 2: Stack exists. We are updating it
        self.deployer.has_stack.return_value = True
        expected_params["ChangeSetType"] = "UPDATE"
        expected_params["Parameters"] = parameters
        self.stub_client.add_response("create_change_set", response,
                                      expected_params)
        with self.stub_client:
            result = self.deployer.create_changeset(
                    stack_name, template, parameters, capabilities, role_arn,
                    notification_arns)
            self.assertEquals(response["Id"], result.changeset_id)
            self.assertEquals("UPDATE", result.changeset_type)

    def test_create_changeset_exception(self):
        stack_name = "stack_name"
        template = "template"
        parameters = [{"ParameterKey": "Key1", "ParameterValue": "Value",
                       "UsePreviousValue": True}]
        capabilities = ["capabilities"]
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]

        self.deployer.has_stack = Mock()
        self.deployer.has_stack.return_value = False

        self.stub_client.add_client_error(
                'create_change_set', "Somethign is wrong", "Service is bad")
        with self.stub_client:
            with self.assertRaises(botocore.exceptions.ClientError):
                self.deployer.create_changeset(stack_name, template, parameters,
                capabilities, role_arn, notification_arns)

    def test_execute_changeset(self):
        stack_name = "stack_name"
        changeset_id = "changeset_id"

        expected_params = {
            "ChangeSetName": changeset_id,
            "StackName": stack_name
        }

        self.stub_client.add_response("execute_change_set", {}, expected_params)
        with self.stub_client:
            self.deployer.execute_changeset(changeset_id, stack_name)

    def test_execute_changeset_exception(self):
        stack_name = "stack_name"
        changeset_id = "changeset_id"

        self.stub_client.add_client_error(
                'execute_change_set', "Somethign is wrong", "Service is bad")
        with self.stub_client:
            with self.assertRaises(botocore.exceptions.ClientError):
                self.deployer.execute_changeset(changeset_id, stack_name)

    def test_create_and_wait_for_changeset_successful(self):
        stack_name = "stack_name"
        template = "template"
        parameters = [{"ParameterKey": "Key1", "ParameterValue": "Value",
                       "UsePreviousValue": True}]
        capabilities = ["capabilities"]
        changeset_id = "changeset id"
        changeset_type = "changeset type"
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]

        self.deployer.create_changeset = Mock()
        self.deployer.create_changeset.return_value = ChangeSetResult(changeset_id, changeset_type)

        self.deployer.wait_for_changeset = Mock()

        result = self.deployer.create_and_wait_for_changeset(
                stack_name, template, parameters, capabilities, role_arn,
                notification_arns)
        self.assertEquals(result.changeset_id, changeset_id)
        self.assertEquals(result.changeset_type, changeset_type)

    def test_create_and_wait_for_changeset_error_waiting_for_changeset(self):
        stack_name = "stack_name"
        template = "template"
        parameters = [{"ParameterKey": "Key1", "ParameterValue": "Value",
                       "UsePreviousValue": True}]
        capabilities = ["capabilities"]
        changeset_id = "changeset id"
        changeset_type = "changeset type"
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]

        self.deployer.create_changeset = Mock()
        self.deployer.create_changeset.return_value = ChangeSetResult(changeset_id, changeset_type)

        self.deployer.wait_for_changeset = Mock()
        self.deployer.wait_for_changeset.side_effect = RuntimeError

        with self.assertRaises(RuntimeError):
            result = self.deployer.create_and_wait_for_changeset(
                    stack_name, template, parameters, capabilities, role_arn,
                    notification_arns)

    def test_wait_for_changeset_no_changes(self):
        stack_name = "stack_name"
        changeset_id = "changeset-id"

        mock_client = Mock()
        mock_deployer = Deployer(mock_client)
        mock_waiter = Mock()
        mock_client.get_waiter.return_value = mock_waiter

        response = {
            "Status": "FAILED",
            "StatusReason": "No updates are to be performed"
        }

        waiter_error = botocore.exceptions.WaiterError(name="name",
                                                       reason="reason",
                                                       last_response=response)
        mock_waiter.wait.side_effect = waiter_error

        with self.assertRaises(exceptions.ChangeEmptyError):
            mock_deployer.wait_for_changeset(changeset_id, stack_name)

        mock_waiter.wait.assert_called_once_with(ChangeSetName=changeset_id,
                                                 StackName=stack_name)

        mock_client.get_waiter.assert_called_once_with(
                "change_set_create_complete")

    def test_wait_for_changeset_failed_to_create_changeset(self):
        stack_name = "stack_name"
        changeset_id = "changeset-id"

        mock_client = Mock()
        mock_deployer = Deployer(mock_client)
        mock_waiter = Mock()
        mock_client.get_waiter.return_value = mock_waiter

        response = {
            "Status": "FAILED",
            "StatusReason": "some reason"
        }

        waiter_error = botocore.exceptions.WaiterError(name="name",
                                                       reason="reason",
                                                       last_response=response)
        mock_waiter.wait.side_effect = waiter_error

        with self.assertRaises(RuntimeError):
            mock_deployer.wait_for_changeset(changeset_id, stack_name)

        mock_waiter.wait.assert_called_once_with(ChangeSetName=changeset_id,
                                            StackName=stack_name)

        mock_client.get_waiter.assert_called_once_with(
                "change_set_create_complete")

    def test_wait_for_execute_no_changes(self):
        stack_name = "stack_name"
        changeset_type = "CREATE"

        mock_client = Mock()
        mock_deployer = Deployer(mock_client)
        mock_waiter = Mock()
        mock_client.get_waiter.return_value = mock_waiter

        waiter_error = botocore.exceptions.WaiterError(name="name",
                                                       reason="reason",
                                                       last_response={})
        mock_waiter.wait.side_effect = waiter_error

        with self.assertRaises(exceptions.DeployFailedError):
            mock_deployer.wait_for_execute(stack_name, changeset_type)

        mock_waiter.wait.assert_called_once_with(StackName=stack_name)

        mock_client.get_waiter.assert_called_once_with(
                "stack_create_complete")


def make_stack_obj(stack_name, status="CREATE_COMPLETE"):
    return {
        "StackId": stack_name,
        "StackName": stack_name,
        "CreationTime": "2013-08-23T01:02:15.422Z",
        "StackStatus": status
    }
