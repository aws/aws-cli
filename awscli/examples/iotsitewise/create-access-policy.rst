**Example 1: To grant a user administrative access to a portal**

The following ``create-access-policy`` example creates an access policy that grants a user administrative access to a web portal for a wind farm company. ::

    aws iotsitewise create-access-policy \
        --cli-input-json file://create-portal-administrator-access-policy.json

Contents of ``create-portal-administrator-access-policy.json``::

    {
        "accessPolicyIdentity": {
            "user": { 
                "id": "a1b2c3d4e5-a1b2c3d4-5678-90ab-cdef-bbbbbEXAMPLE"
            }
        },
        "accessPolicyPermission": "ADMINISTRATOR",
        "accessPolicyResource": { 
            "portal": { 
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        }
    }

Output::

    {
        "accessPolicyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "accessPolicyArn": "arn:aws:iotsitewise:us-west-2:123456789012:access-policy/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Adding or removing portal administrators <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/portal-change-admins.html>`__ in the *AWS IoT SiteWise User Guide*.

**Example 2: To grant a user read-only access to a project**

The following ``create-access-policy`` example creates an access policy that grants a user read-only access to a wind farm project. ::

    aws iotsitewise create-access-policy \
        --cli-input-json file://create-project-viewer-access-policy.json

Contents of ``create-project-viewer-access-policy.json``::

    {
        "accessPolicyIdentity": {
            "user": { 
                "id": "a1b2c3d4e5-a1b2c3d4-5678-90ab-cdef-bbbbbEXAMPLE"
            }
        },
        "accessPolicyPermission": "VIEWER",
        "accessPolicyResource": { 
            "project": { 
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            }
        }
    }

Output::

    {
        "accessPolicyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
        "accessPolicyArn": "arn:aws:iotsitewise:us-west-2:123456789012:access-policy/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
    }

For more information, see `Assigning project viewers <https://docs.aws.amazon.com/iot-sitewise/latest/appguide/assign-project-viewers.html>`__ in the *AWS IoT SiteWise Monitor Application Guide*.