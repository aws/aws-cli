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

from awscli.customizations.emr import helptext
from awscli.customizations.emr.createdefaultroles import EC2_ROLE_NAME


INSTANCE_GROUPS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "description":
                    "Friendly name given to the instance group."
            },
            "InstanceGroupType": {
                "type": "string",
                "description":
                    "The type of the instance group in the cluster.",
                "enum": ["MASTER", "CORE", "TASK"],
                "required": True
            },
            "BidPrice": {
                "type": "string",
                "description":
                    "Bid price for each Amazon EC2 instance in the "
                    "instance group when launching nodes as Spot Instances, "
                    "expressed in USD."
            },
            "InstanceType": {
                "type": "string",
                "description":
                    "The Amazon EC2 instance type for all instances "
                    "in the instance group.",
                "required": True
            },
            "InstanceCount": {
                "type": "integer",
                "description": "Target number of Amazon EC2 instances "
                "for the instance group",
                "required": True
            }
        }
    }
}


EC2_ATTRIBUTES_SCHEMA = {
    "type": "object",
    "properties": {
        "KeyName": {
            "type": "string",
            "description":
                "The name of the Amazon EC2 key pair that can "
                "be used to ssh to the master node as the user 'hadoop'."
        },
        "SubnetId": {
            "type": "string",
            "description":
                "To launch the cluster in Amazon "
                "Virtual Private Cloud (Amazon VPC), set this parameter to "
                "the identifier of the Amazon VPC subnet where you want "
                "the cluster to launch. If you do not specify this value, "
                "the cluster is launched in the normal Amazon Web Services "
                "cloud, outside of an Amazon VPC. "
        },
        "AvailabilityZone": {
            "type": "string",
            "description": "The Availability Zone the cluster will run in."
        },
        "InstanceProfile": {
            "type": "string",
            "description":
                "An IAM role for the cluster. The EC2 instances of the cluster"
                " assume this role. The default role is " +
                EC2_ROLE_NAME + ". In order to use the default"
                " role, you must have already created it using the "
                "<code>create-default-roles</code> command. "
        },
        "EmrManagedMasterSecurityGroup": {
            "type": "string",
            "description": helptext.EMR_MANAGED_MASTER_SECURITY_GROUP
        },
        "EmrManagedSlaveSecurityGroup": {
            "type": "string",
            "description": helptext.EMR_MANAGED_SLAVE_SECURITY_GROUP
        },
        "AdditionalMasterSecurityGroups": {
            "type": "array",
            "description": helptext.ADDITIONAL_MASTER_SECURITY_GROUPS,
            "items": {
                "type": "string"
            }
        },
        "AdditionalSlaveSecurityGroups": {
            "type": "array",
            "description": helptext.ADDITIONAL_SLAVE_SECURITY_GROUPS,
            "items": {
                "type": "string"
            }
        }
    }
}


APPLICATIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "description": "Application name.",
                "enum": ["MapR", "HUE", "HIVE", "PIG", "HBASE",
                         "IMPALA", "GANGLIA", "HADOOP", "SPARK"],
                "required": True
            },
            "Args": {
                "type": "array",
                "description":
                    "A list of arguments to pass to the application.",
                "items": {
                    "type": "string"
                }
            }
        }
    }
}

BOOTSTRAP_ACTIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "default": "Bootstrap Action"
            },
            "Path": {
                "type": "string",
                "description":
                    "Location of the script to run during a bootstrap action. "
                    "Can be either a location in Amazon S3 or "
                    "on a local file system.",
                "required": True
            },
            "Args": {
                "type": "array",
                "description":
                    "A list of command line arguments to pass to "
                    "the bootstrap action script",
                "items": {
                    "type": "string"
                }
            }
        }
    }
}


STEPS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Type": {
                "type": "string",
                "description":
                    "The type of a step to be added to the cluster.",
                "default": "custom_jar",
                "enum": ["CUSTOM_JAR", "STREAMING", "HIVE", "PIG", "IMPALA"],
            },
            "Name": {
                "type": "string",
                "description": "The name of the step. ",
            },
            "ActionOnFailure": {
                "type": "string",
                "description": "The action to take if the cluster step fails.",
                "enum": ["TERMINATE_CLUSTER", "CANCEL_AND_WAIT", "CONTINUE"],
                "default": "CONTINUE"
            },
            "Jar": {
                "type": "string",
                "description": "A path to a JAR file run during the step.",
            },
            "Args": {
                "type": "array",
                "description":
                    "A list of command line arguments to pass to the step.",
                "items": {
                        "type": "string"
                }
            },
            "MainClass": {
                "type": "string",
                "description":
                    "The name of the main class in the specified "
                    "Java file. If not specified, the JAR file should "
                    "specify a Main-Class in its manifest file."
            },
            "Properties": {
                "type": "string",
                "description":
                    "A list of Java properties that are set when the step "
                    "runs. You can use these properties to pass key value "
                    "pairs to your main function."
            }
        }
    }
}

HBASE_RESTORE_FROM_BACKUP_SCHEMA = {
    "type": "object",
    "properties": {
        "Dir": {
            "type": "string",
            "description": helptext.HBASE_BACKUP_DIR
        },
        "BackupVersion": {
            "type": "string",
            "description": helptext.HBASE_BACKUP_VERSION
        }
    }
}

EMR_FS_SCHEMA = {
    "type": "object",
    "properties": {
        "Consistent": {
            "type": "boolean",
            "description": "Enable EMRFS consistent view."
        },
        "SSE": {
            "type": "boolean",
            "description": "Enable Amazon S3 server-side encryption on files "
                           "written to S3 by EMRFS."
        },
        "RetryCount": {
            "type": "integer",
            "description":
                "The maximum number of times to retry upon S3 inconsistency."
        },
        "RetryPeriod": {
            "type": "integer",
            "description": "The amount of time (in seconds) until the first "
                           "retry. Subsequent retries use an exponential "
                           "back-off."
        },
        "Args": {
            "type": "array",
            "description": "A list of arguments to pass for additional "
                           "EMRFS configuration.",
            "items": {
                "type": "string"
            }
        },
        "Encryption": {
            "type": "string",
            "description": "EMRFS encryption type.",
            "enum": ["SERVERSIDE", "CLIENTSIDE"]
        },
        "ProviderType": {
            "type": "string",
            "description": "EMRFS client-side encryption provider type.",
            "enum": ["KMS", "CUSTOM"]
        },
        "KMSKeyId": {
            "type": "string",
            "description": "AWS KMS's customer master key identifier",
        },
        "CustomProviderLocation": {
            "type": "string",
            "description": "Custom encryption provider JAR location."
        },
        "CustomProviderClass": {
            "type": "string",
            "description": "Custom encryption provider full class name."
        }
    }
}

TAGS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "string"
    }
}
