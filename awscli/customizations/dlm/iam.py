import json


class IAM(object):

    def __init__(self, iam_client):
        self.iam_client = iam_client

    def check_if_role_exists(self, role_name):
        """Method to verify if a particular role exists"""
        try:
            self.iam_client.get_role(RoleName=role_name)
        except self.iam_client.exceptions.NoSuchEntityException:
            return False
        return True

    def check_if_policy_exists(self, policy_arn):
        """Method to verify if a particular policy exists"""
        try:
            self.iam_client.get_policy(PolicyArn=policy_arn)
        except self.iam_client.exceptions.NoSuchEntityException:
            return False
        return True

    def attach_policy_to_role(self, policy_arn, role_name):
        """Method to attach LifecyclePolicy to role specified by role_name"""
        return self.iam_client.attach_role_policy(
            PolicyArn=policy_arn,
            RoleName=role_name
        )

    def create_role_with_trust_policy(self, role_name, assume_role_policy):
        """Method to create role with a given role name
            and assume_role_policy
        """
        return self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy))

    def get_policy(self, arn):
        """Method to get the Policy for a particular ARN
        This is used to display the policy contents to the user
        """
        pol_det = self.iam_client.get_policy(PolicyArn=arn)
        policy_version_details = self.iam_client.get_policy_version(
            PolicyArn=arn,
            VersionId=pol_det.get("Policy", {}).get("DefaultVersionId", "")
        )
        return policy_version_details\
            .get("PolicyVersion", {})\
            .get("Document", {})
