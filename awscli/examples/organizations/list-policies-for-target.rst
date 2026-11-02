**To retrieve a list of the SCPs attached directly to an account**

The following ``list-policies-for-target`` example gets a list of all service control policies (SCPs), as specified by the ``--filter`` parameter, that are directly attached to an account. ::

    aws organizations list-policies-for-target \
        --filter SERVICE_CONTROL_POLICY \
        --target-id 123456789333
  
The output includes a list of policy structures with summary information about the policies. The list does not include policies that apply to the account because of inheritance from its location in an OU hierarchy.

Output::

    {
        "Policies": [
            {
                "Type": "SERVICE_CONTROL_POLICY",
                "Name": "AllowAllEC2Actions",
                "AwsManaged": false,
                "Id": "p-examplepolicyid222",
                "Arn": "arn:aws:organizations::o-exampleorgid:policy/service_control_policy/p-examplepolicyid222",
                "Description": "Enables account admins to delegate permissions for any EC2 actions to users and roles in their accounts."
            }
        ]
    }

For more information, see `Getting information about your organization's policies <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_info-operations.html>`__ in the *AWS Organizations User Guide*.
