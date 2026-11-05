**To add a custom attribute**

The following ``add-custom-attributes`` example adds a custom attribute CustomAttr1 to a user pool. It is a String type,
and requires a minimum of 1 character and a maximum of 15. It is not required. ::

    aws cognito-idp add-custom-attributes \
        --user-pool-id us-west-2_aaaaaaaaa \
        --custom-attributes Name="CustomAttr1",AttributeDataType="String",DeveloperOnlyAttribute=false,Required=false,StringAttributeConstraints="{MinLength=1,MaxLength=15}"

This command produces no output.

For more information, see `Working with user attributes <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html>`__ in the *Amazon Cognito Developer Guide*.
