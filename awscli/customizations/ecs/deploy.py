# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import hashlib
import json
import os
import sys

from botocore import compat
from botocore.exceptions import ClientError
from awscli.compat import compat_open
from awscli.customizations.ecs import exceptions, filehelpers
from awscli.customizations.commands import BasicCommand


class ECSDeploy(BasicCommand):
    NAME = 'deploy'

    DESCRIPTION = (
        "Deploys a new task definition to the specified ECS service. "
        "Only services that use CodeDeploy for deployments are supported. "
        "This command will register a new task definition, update the "
        "CodeDeploy appspec with the new task definition revision, create a "
        "CodeDeploy deployment, and wait for the deployment to successfully "
        "complete. This command will exit with a return code of 255 if the "
        "deployment does not succeed within 30 minutes."
    )

    ARG_TABLE = [
        {
            'name': 'service',
            'help_text': ("The short name or full Amazon Resource Name "
                          "(ARN) of the service to update"),
            'required': True
        },
        {
            'name': 'task-definition',
            'help_text': ("The file path where your task definition file is "
                          "located. The format of the file must be the same "
                          "as the JSON output of: <codeblock>aws ecs "
                          "register-task-definition "
                          "--generate-cli-skeleton</codeblock>"),
            'required': True
        },
        {
            'name': 'codedeploy-appspec',
            'help_text': ("The file path where your AWS CodeDeploy appspec "
                          "file is located. The appspec file may be in JSON "
                          "or YAML format. The <code>TaskDefinition</code> "
                          "property will be updated within the appspec with "
                          "the newly registered task definition ARN, "
                          "overwriting any placeholder values in the file."),
            'required': True
        },
        {
            'name': 'cluster',
            'help_text': ("The short name or full Amazon Resource Name "
                          "(ARN) of the cluster that your service is "
                          "running within. If you do not specify a "
                          "cluster, the \"default\" cluster is assumed."),
            'required': False
        },
        {
            'name': 'codedeploy-application',
            'help_text': ("The name of the AWS CodeDeploy application "
                          "to use for the deployment. The specified "
                          "application must use the 'ECS' compute "
                          "platform. If you do not specify an "
                          "application, the application name "
                          "<code>AppECS-[CLUSTER_NAME]-[SERVICE_NAME]</code> "
                          "is assumed."),
            'required': False
        },
        {
            'name': 'codedeploy-deployment-group',
            'help_text': ("The name of the AWS CodeDeploy deployment "
                          "group to use for the deployment. The "
                          "specified deployment group must be associated "
                          "with the specified ECS service and cluster. "
                          "If you do not specify a deployment group, "
                          "the deployment group name "
                          "<code>DgpECS-[CLUSTER_NAME]-[SERVICE_NAME]</code> "
                          "is assumed."),
            'required': False
        }
    ]

    MSG_TASK_DEF_REGISTERED = \
        "Successfully registered new ECS task definition {arn}\n"

    MSG_CREATED_DEPLOYMENT = "Successfully created deployment {id}\n"

    MSG_WAITING = "Waiting for {deployment_id} to succeed..."

    def _run_main(self, parsed_args, parsed_globals):

        register_task_def_kwargs, appspec_obj = \
            self._load_file_args(parsed_args.task_definition,
                                 parsed_args.codedeploy_appspec)

        ecs_client_wrapper = ECSClient(
            self._session, parsed_args, parsed_globals)

        self.resources = self._get_resource_names(
            parsed_args, ecs_client_wrapper)

        codedeploy_client = self._session.create_client(
            'codedeploy',
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl)

        self._validate_code_deploy_resources(codedeploy_client)

        self.task_def_arn = self._register_task_def(
            register_task_def_kwargs, ecs_client_wrapper)

        self._create_and_wait_for_deployment(codedeploy_client, appspec_obj)

    def _create_and_wait_for_deployment(self, client, appspec):
        deployer = CodeDeployer(client, appspec)
        deployer.update_task_def_arn(self.task_def_arn)
        deployment_id = deployer.create_deployment(
            self.resources['app_name'],
            self.resources['deployment_group_name'])

        sys.stdout.write(self.MSG_CREATED_DEPLOYMENT.format(
            id=deployment_id))
        sys.stdout.write(
            self.MSG_WAITING.format(deployment_id=deployment_id))
        sys.stdout.flush()

        deployer.wait_for_deploy_success(deployment_id)

    def _get_file_contents(self, file_path):
        full_path = os.path.expandvars(os.path.expanduser(file_path))
        try:
            with compat_open(full_path) as f:
                return f.read()
        except (OSError, IOError, UnicodeDecodeError) as e:
            raise exceptions.FileLoadError(
                file_path=file_path, error=e)

    def _get_resource_names(self, args, ecs_client):
        service_details = ecs_client.get_service_details()
        service_name = service_details['service_name']
        cluster_name = service_details['cluster_name']

        application_name = filehelpers.get_app_name(
            service_name, cluster_name, args.codedeploy_application)
        deployment_group_name = filehelpers.get_deploy_group_name(
            service_name, cluster_name, args.codedeploy_deployment_group)

        return {
            'service': service_name,
            'service_arn': service_details['service_arn'],
            'cluster': cluster_name,
            'cluster_arn': service_details['cluster_arn'],
            'app_name': application_name,
            'deployment_group_name': deployment_group_name
        }

    def _load_file_args(self, task_def_arg, appspec_arg):
        task_def_string = self._get_file_contents(task_def_arg)
        register_task_def_kwargs = json.loads(task_def_string)

        appspec_string = self._get_file_contents(appspec_arg)
        appspec_obj = filehelpers.parse_appspec(appspec_string)

        return register_task_def_kwargs, appspec_obj

    def _register_task_def(self, task_def_kwargs, ecs_client):
        response = ecs_client.register_task_definition(task_def_kwargs)

        task_def_arn = response['taskDefinition']['taskDefinitionArn']

        sys.stdout.write(self.MSG_TASK_DEF_REGISTERED.format(
            arn=task_def_arn))
        sys.stdout.flush()

        return task_def_arn

    def _validate_code_deploy_resources(self, client):
        validator = CodeDeployValidator(client, self.resources)
        validator.describe_cd_resources()
        validator.validate_all()


class CodeDeployer():
    def __init__(self, cd_client, appspec_dict):
        self._client = cd_client
        self._appspec_dict = appspec_dict

    def create_deployment(self, app_name, deploy_grp_name):
        request_obj = self._get_create_deploy_request(
            app_name, deploy_grp_name)

        try:
            response = self._client.create_deployment(**request_obj)
        except ClientError as e:
            raise exceptions.ServiceClientError(
                action='create deployment', error=e)

        return response['deploymentId']

    def _get_appspec_hash(self):
        appspec_str = json.dumps(self._appspec_dict)
        appspec_encoded = compat.ensure_bytes(appspec_str)
        return hashlib.sha256(appspec_encoded).hexdigest()

    def _get_create_deploy_request(self, app_name, deploy_grp_name):
        return {
            "applicationName": app_name,
            "deploymentGroupName": deploy_grp_name,
            "revision": {
                "revisionType": "AppSpecContent",
                "appSpecContent": {
                    "content": json.dumps(self._appspec_dict),
                    "sha256": self._get_appspec_hash()
                }
            }
        }

    def update_task_def_arn(self, new_arn):
        """
        Inserts the ARN of the previously created ECS task definition
        into the provided appspec.

        Expected format of ECS appspec (YAML) is:
            version: 0.0
            resources:
              - <service-name>:
                  type: AWS::ECS::Service
                  properties:
                    taskDefinition: <value>  # replace this
                    loadBalancerInfo:
                      containerName: <value>
                      containerPort: <value>
        """
        appspec_obj = self._appspec_dict

        resources_key = filehelpers.find_required_key(
            'codedeploy-appspec', appspec_obj, 'resources')
        updated_resources = []

        # 'resources' is a list of string:obj dictionaries
        for resource in appspec_obj[resources_key]:
            for name in resource:
                # get content of resource
                resource_content = resource[name]
                # get resource properties
                properties_key = filehelpers.find_required_key(
                    name, resource_content, 'properties')
                properties_content = resource_content[properties_key]
                # find task definition property
                task_def_key = filehelpers.find_required_key(
                    properties_key, properties_content, 'taskDefinition')

                # insert new task def ARN into resource
                properties_content[task_def_key] = new_arn

            updated_resources.append(resource)

        appspec_obj[resources_key] = updated_resources
        self._appspec_dict = appspec_obj

    def wait_for_deploy_success(self, id):
        waiter = self._client.get_waiter("deployment_successful")
        waiter.wait(deploymentId=id)


class CodeDeployValidator():
    def __init__(self, cd_client, resources):
        self._client = cd_client
        self._resource_names = resources

    def describe_cd_resources(self):
        try:
            self.app_details = self._client.get_application(
                applicationName=self._resource_names['app_name'])
        except ClientError as e:
            raise exceptions.ServiceClientError(
                action='describe Code Deploy application', error=e)

        try:
            dgp = self._resource_names['deployment_group_name']
            app = self._resource_names['app_name']
            self.deployment_group_details = self._client.get_deployment_group(
                applicationName=app, deploymentGroupName=dgp)
        except ClientError as e:
            raise exceptions.ServiceClientError(
                action='describe Code Deploy deployment group', error=e)

    def validate_all(self):
        self.validate_application()
        self.validate_deployment_group()

    def validate_application(self):
        app_name = self._resource_names['app_name']
        if self.app_details['application']['computePlatform'] != 'ECS':
            raise exceptions.InvalidPlatformError(
                resource='Application', name=app_name)

    def validate_deployment_group(self):
        dgp = self._resource_names['deployment_group_name']
        service = self._resource_names['service']
        service_arn = self._resource_names['service_arn']
        cluster = self._resource_names['cluster']
        cluster_arn = self._resource_names['cluster_arn']

        grp_info = self.deployment_group_details['deploymentGroupInfo']
        compute_platform = grp_info['computePlatform']

        if compute_platform != 'ECS':
            raise exceptions.InvalidPlatformError(
                resource='Deployment Group', name=dgp)

        target_services = \
            self.deployment_group_details['deploymentGroupInfo']['ecsServices']

        # either ECS resource names or ARNs can be stored, so check both
        for target in target_services:
            target_serv = target['serviceName']
            if target_serv != service and target_serv != service_arn:
                raise exceptions.InvalidProperyError(
                    dg_name=dgp, resource='service', resource_name=service)

            target_cluster = target['clusterName']
            if target_cluster != cluster and target_cluster != cluster_arn:
                raise exceptions.InvalidProperyError(
                    dg_name=dgp, resource='cluster', resource_name=cluster)


class ECSClient():
    def __init__(self, session, parsed_args, parsed_globals):
        self._args = parsed_args
        self._client = session.create_client(
            'ecs',
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)

    def get_service_details(self):
        cluster = self._args.cluster

        if cluster is None or '':
            cluster = 'default'

        try:
            service_response = self._client.describe_services(
                cluster=cluster, services=[self._args.service])
        except ClientError as e:
            raise exceptions.ServiceClientError(
                action='describe ECS service', error=e)

        if len(service_response['services']) == 0:
            raise exceptions.InvalidServiceError(
                service=self._args.service, cluster=cluster)

        service_details = service_response['services'][0]
        cluster_name = \
            filehelpers.get_cluster_name_from_arn(
                service_details['clusterArn'])

        return {
            'service_arn': service_details['serviceArn'],
            'service_name': service_details['serviceName'],
            'cluster_arn': service_details['clusterArn'],
            'cluster_name': cluster_name
        }

    def register_task_definition(self, kwargs):
        try:
            response = \
                self._client.register_task_definition(**kwargs)
        except ClientError as e:
            raise exceptions.ServiceClientError(
                action='register ECS task definition', error=e)

        return response
