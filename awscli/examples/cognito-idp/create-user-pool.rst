**Example 1: To create a minimally configured user pool**

The following ``create-user-pool`` example creates a user pool named MyUserPool using default values. There are no required attributes
and no application clients. MFA and advanced security is disabled. ::

    aws cognito-idp create-user-pool \
        --pool-name MyUserPool

Output::

    {
        "UserPool": {
            "SchemaAttributes": [
                {
                    "Name": "sub",
                    "StringAttributeConstraints": {
                        "MinLength": "1",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": true,
                    "AttributeDataType": "String",
                    "Mutable": false
                },
                {
                    "Name": "name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "given_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "family_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "middle_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "nickname",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "preferred_username",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "profile",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "picture",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "website",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "email",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "AttributeDataType": "Boolean",
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "Name": "email_verified",
                    "Mutable": true
                },
                {
                    "Name": "gender",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "birthdate",
                    "StringAttributeConstraints": {
                        "MinLength": "10",
                        "MaxLength": "10"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "zoneinfo",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "locale",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "phone_number",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "AttributeDataType": "Boolean",
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "Name": "phone_number_verified",
                    "Mutable": true
                },
                {
                    "Name": "address",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "updated_at",
                    "NumberAttributeConstraints": {
                        "MinValue": "0"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "Number",
                    "Mutable": true
                }
            ],
            "MfaConfiguration": "OFF",
            "Name": "MyUserPool",
            "LastModifiedDate": 1547833345.777,
            "AdminCreateUserConfig": {
                "UnusedAccountValidityDays": 7,
                "AllowAdminCreateUserOnly": false
            },
            "EmailConfiguration": {},
            "Policies": {
                "PasswordPolicy": {
                    "RequireLowercase": true,
                    "RequireSymbols": true,
                    "RequireNumbers": true,
                    "MinimumLength": 8,
                    "RequireUppercase": true
                }
            },
            "CreationDate": 1547833345.777,
            "EstimatedNumberOfUsers": 0,
            "Id": "us-west-2_aaaaaaaaa",
            "LambdaConfig": {}
        }
    }

For more information, see `Authenticating users with Amazon Cognito user pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html>`__ in the *Amazon Cognito Developer Guide*.

**Example 2: To create a user pool with two required attributes**

The following ``create-user-pool`` example creates a user pool MyUserPool. The pool is configured to accept
email as a username attribute. It also sets the email source address to a
validated address using Amazon Simple Email Service. ::

    aws cognito-idp create-user-pool \
        --pool-name MyUserPool \
        --username-attributes "email" \
        --email-configuration SourceArn="arn:aws:ses:us-west-2:123456789012:identity/jane@example.com",ReplyToEmailAddress="jane@example.com"

Output::

    {
        "UserPool": {
            "SchemaAttributes": [
                {
                    "Name": "sub",
                    "StringAttributeConstraints": {
                        "MinLength": "1",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": true,
                    "AttributeDataType": "String",
                    "Mutable": false
                },
                {
                    "Name": "name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "given_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "family_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "middle_name",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "nickname",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "preferred_username",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "profile",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "picture",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "website",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "email",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "AttributeDataType": "Boolean",
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "Name": "email_verified",
                    "Mutable": true
                },
                {
                    "Name": "gender",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "birthdate",
                    "StringAttributeConstraints": {
                        "MinLength": "10",
                        "MaxLength": "10"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "zoneinfo",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "locale",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "phone_number",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "AttributeDataType": "Boolean",
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "Name": "phone_number_verified",
                    "Mutable": true
                },
                {
                    "Name": "address",
                    "StringAttributeConstraints": {
                        "MinLength": "0",
                        "MaxLength": "2048"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "String",
                    "Mutable": true
                },
                {
                    "Name": "updated_at",
                    "NumberAttributeConstraints": {
                        "MinValue": "0"
                    },
                    "DeveloperOnlyAttribute": false,
                    "Required": false,
                    "AttributeDataType": "Number",
                    "Mutable": true
                }
            ],
            "MfaConfiguration": "OFF",
            "Name": "MyUserPool",
            "LastModifiedDate": 1547837788.189,
            "AdminCreateUserConfig": {
                "UnusedAccountValidityDays": 7,
                "AllowAdminCreateUserOnly": false
            },
            "EmailConfiguration": {
                "ReplyToEmailAddress": "jane@example.com",
                "SourceArn": "arn:aws:ses:us-west-2:123456789012:identity/jane@example.com"
            },
            "Policies": {
                "PasswordPolicy": {
                    "RequireLowercase": true,
                    "RequireSymbols": true,
                    "RequireNumbers": true,
                    "MinimumLength": 8,
                    "RequireUppercase": true
                }
            },
            "UsernameAttributes": [
                "email"
            ],
            "CreationDate": 1547837788.189,
            "EstimatedNumberOfUsers": 0,
            "Id": "us-west-2_aaaaaaaaa",
            "LambdaConfig": {}
        }
    }

For more information, see `Authenticating users with Amazon Cognito user pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools.html>`__ in the *Amazon Cognito Developer Guide*.
