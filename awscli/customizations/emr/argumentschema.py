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

CONFIGURATIONS_PROPERTIES_SCHEMA = {
    "type": "map",
    "key": {
        "type": "string",
        "description": "Configuration key"
    },
    "value": {
        "type": "string",
        "description": "Configuration value"
    },
    "description": "Application configuration properties"
}

CONFIGURATIONS_CLASSIFICATION_SCHEMA = {
    "type": "string",
    "description": "Application configuration classification name",
}

INNER_CONFIGURATIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Classification": CONFIGURATIONS_CLASSIFICATION_SCHEMA,
            "Properties": CONFIGURATIONS_PROPERTIES_SCHEMA
        }
    },
    "description": "Instance group application configurations."
}

OUTER_CONFIGURATIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Classification": CONFIGURATIONS_CLASSIFICATION_SCHEMA,
            "Properties": CONFIGURATIONS_PROPERTIES_SCHEMA,
            "Configurations": INNER_CONFIGURATIONS_SCHEMA
        }
    },
    "description": "Instance group application configurations."
}

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
            },
            "CustomAmiId": {
                "type": "string",
                "description": "The AMI ID of a custom AMI to use when Amazon EMR provisions EC2 instances."
            },
            "EbsConfiguration": {
                "type": "object",
                "description": "EBS configuration that will be associated with the instance group.",
                "properties": {
                    "EbsOptimized": {
                        "type": "boolean",
                        "description": "Boolean flag used to tag EBS-optimized instances.",
                    },
                    "EbsBlockDeviceConfigs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "VolumeSpecification" : {
                                    "type": "object",
                                    "description": "The EBS volume specification that will be created and attached to every instance in this instance group.",
                                    "properties": {
                                        "VolumeType": {
                                            "type": "string",
                                            "description": "The EBS volume type that is attached to all the instances in the instance group. Valid types are: gp2, io1, and standard.",
                                            "required": True
                                        },
                                        "SizeInGB": {
                                            "type": "integer",
                                            "description": "The EBS volume size, in GB, that is attached to all the instances in the instance group.",
                                            "required": True
                                        },
                                        "Iops": {
                                            "type": "integer",
                                            "description": "The IOPS of the EBS volume that is attached to all the instances in the instance group.",
                                        },
                                        "Throughput": {
                                            "type": "integer",
                                            "description": "The throughput of the EBS volume that is attached to all the instances in the instance group.",
                                        }
                                    }
                                },
                                "VolumesPerInstance": {
                                    "type": "integer",
                                    "description": "The number of EBS volumes that will be created and attached to each instance in the instance group.",
                                }
                            }
                        }
                    }
                }
            },
            "AutoScalingPolicy": {
                "type": "object",
                "description": "Auto Scaling policy that will be associated with the instance group.",
                "properties": {
                    "Constraints": {
                        "type": "object",
                        "description": "The Constraints that will be associated to an Auto Scaling policy.",
                        "properties": {
                            "MinCapacity": {
                                "type": "integer",
                                "description": "The minimum value for the instances to scale in"
                                               " to in response to scaling activities."
                            },
                            "MaxCapacity": {
                                "type": "integer",
                                "description": "The maximum value for the instances to scale out to in response"
                                               " to scaling activities"
                            }
                        }
                    },
                    "Rules": {
                        "type": "array",
                        "description": "The Rules associated to an Auto Scaling policy.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "Name": {
                                    "type": "string",
                                    "description": "Name of the Auto Scaling rule."
                                },
                                "Description": {
                                    "type": "string",
                                    "description": "Description of the Auto Scaling rule."
                                },
                                "Action": {
                                    "type": "object",
                                    "description": "The Action associated to an Auto Scaling rule.",
                                    "properties": {
                                        "Market": {  # Required for Instance Fleets
                                            "type": "string",
                                            "description": "Market type of the Amazon EC2 instances used to create a "
                                                           "cluster node by Auto Scaling action.",
                                            "enum": ["ON_DEMAND", "SPOT"]
                                        },
                                        "SimpleScalingPolicyConfiguration": {
                                            "type": "object",
                                            "description": "The Simple scaling configuration that will be associated"
                                                           "to Auto Scaling action.",
                                            "properties": {
                                                "AdjustmentType": {
                                                    "type": "string",
                                                    "description": "Specifies how the ScalingAdjustment parameter is "
                                                                   "interpreted.",
                                                    "enum": ["CHANGE_IN_CAPACITY", "PERCENT_CHANGE_IN_CAPACITY",
                                                             "EXACT_CAPACITY"]
                                                },
                                                "ScalingAdjustment": {
                                                    "type": "integer",
                                                    "description": "The amount by which to scale, based on the "
                                                                   "specified adjustment type."
                                                },
                                                "CoolDown": {
                                                    "type": "integer",
                                                    "description": "The amount of time, in seconds, after a scaling "
                                                                   "activity completes and before the next scaling "
                                                                   "activity can start."
                                                }
                                            }
                                        }
                                    }
                                },
                                "Trigger": {
                                    "type": "object",
                                    "description": "The Trigger associated to an Auto Scaling rule.",
                                    "properties": {
                                        "CloudWatchAlarmDefinition": {
                                            "type": "object",
                                            "description": "The Alarm to be registered with CloudWatch, to trigger"
                                                           " scaling activities.",
                                            "properties": {
                                                "ComparisonOperator": {
                                                    "type": "string",
                                                    "description": "The arithmetic operation to use when comparing the"
                                                                   " specified Statistic and Threshold."
                                                },
                                                "EvaluationPeriods": {
                                                    "type": "integer",
                                                    "description": "The number of periods over which data is compared"
                                                                   " to the specified threshold."
                                                },
                                                "MetricName": {
                                                    "type": "string",
                                                    "description": "The name for the alarm's associated metric."
                                                },
                                                "Namespace": {
                                                    "type": "string",
                                                    "description": "The namespace for the alarm's associated metric."
                                                },
                                                "Period": {
                                                    "type": "integer",
                                                    "description": "The period in seconds over which the specified "
                                                                   "statistic is applied."
                                                },
                                                "Statistic": {
                                                    "type": "string",
                                                    "description": "The statistic to apply to the alarm's associated "
                                                                   "metric."
                                                },
                                                "Threshold": {
                                                    "type": "double",
                                                    "description": "The value against which the specified statistic is "
                                                                   "compared."
                                                },
                                                "Unit": {
                                                    "type": "string",
                                                    "description": "The statistic's unit of measure."
                                                },
                                                "Dimensions": {
                                                    "type": "array",
                                                    "description": "The dimensions for the alarm's associated metric.",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "Key": {
                                                                "type": "string",
                                                                "description": "Dimension Key."
                                                            },
                                                            "Value": {
                                                                "type": "string",
                                                                "description": "Dimension Value."
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "Configurations": OUTER_CONFIGURATIONS_SCHEMA
        }
    }
}

INSTANCE_FLEETS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "description": "Friendly name given to the instance fleet."
            },
            "InstanceFleetType": {
                "type": "string",
                "description": "The type of the instance fleet in the cluster.",
                "enum": ["MASTER", "CORE", "TASK"],
                "required": True
            },
            "TargetOnDemandCapacity": {
                "type": "integer",
                "description": "Target on-demand capacity for the instance fleet."
            },
            "TargetSpotCapacity": {
                "type": "integer",
                "description": "Target spot capacity for the instance fleet."
            },
            "InstanceTypeConfigs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "InstanceType": {
                            "type": "string",
                            "description": "The Amazon EC2 instance type for the instance fleet.",
                            "required": True
                        },
                        "WeightedCapacity": {
                            "type": "integer",
                            "description": "The weight assigned to an instance type, which will impact the overall fulfillment of the capacity."
                        },
                        "BidPrice": {
                            "type": "string",
                            "description": "Bid price for each Amazon EC2 instance in the "
                                "instance fleet when launching nodes as Spot Instances, "
                                "expressed in USD."
                        },
                        "BidPriceAsPercentageOfOnDemandPrice": {
                            "type": "double",
                            "description": "Bid price as percentage of on-demand price."
                        },
                        "CustomAmiId": {
                            "type": "string",
                            "description": "The AMI ID of a custom AMI to use when Amazon EMR provisions EC2 instances."
                        },
                        "EbsConfiguration": {
                            "type": "object",
                            "description": "EBS configuration that is associated with the instance group.",
                            "properties": {
                                "EbsOptimized": {
                                    "type": "boolean",
                                    "description": "Boolean flag used to tag EBS-optimized instances.",
                                },
                                "EbsBlockDeviceConfigs": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "VolumeSpecification" : {
                                                "type": "object",
                                                "description": "The EBS volume specification that is created "
                                                    "and attached to each instance in the instance group.",
                                                "properties": {
                                                    "VolumeType": {
                                                        "type": "string",
                                                        "description": "The EBS volume type that is attached to all "
                                                            "the instances in the instance group. Valid types are: "
                                                            "gp2, io1, and standard.",
                                                            "required": True
                                                    },
                                                    "SizeInGB": {
                                                        "type": "integer",
                                                        "description": "The EBS volume size, in GB, that is attached "
                                                            "to all the instances in the instance group.",
                                                        "required": True
                                                    },
                                                    "Iops": {
                                                        "type": "integer",
                                                        "description": "The IOPS of the EBS volume that is attached to "
                                                            "all the instances in the instance group.",
                                                    },
                                                    "Throughput": {
                                                         "type": "integer",
                                                         "description": "The throughput of the EBS volume that is attached to "
                                                             "all the instances in the instance group.",
                                                    }
                                                }
                                            },
                                            "VolumesPerInstance": {
                                                "type": "integer",
                                                "description": "The number of EBS volumes that will be created and "
                                                    "attached to each instance in the instance group.",
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "Configurations": OUTER_CONFIGURATIONS_SCHEMA
                    }
                }
            },
            "LaunchSpecifications": {
                "type": "object",
                "properties" : {
                    "OnDemandSpecification": {
                        "type": "object",
                        "properties": {
                            "AllocationStrategy": {
                                "type": "string",
                                "description": "The strategy to use in launching On-Demand instance fleets.",
                                "enum": ["lowest-price"]
                            },
                            "CapacityReservationOptions": {
                                "type": "object",
                                "properties" : {
                                    "UsageStrategy": {
                                        "type": "string",
                                        "description": "The strategy of whether to use unused Capacity Reservations for fulfilling On-Demand capacity.",
                                        "enum": ["use-capacity-reservations-first"]
                                    },
                                    "CapacityReservationPreference": {
                                        "type": "string",
                                        "description": "The preference of the instance's Capacity Reservation.",
                                        "enum": [
                                            "open",
                                            "none"
                                        ]
                                    },
                                    "CapacityReservationResourceGroupArn": {
                                        "type": "string",
                                        "description": "The ARN of the Capacity Reservation resource group in which to run the instance."
                                    }
                                }
                            }
                        }
                    },
                    "SpotSpecification": {
                        "type": "object",
                        "properties": {
                            "TimeoutDurationMinutes": {
                                "type": "integer",
                                "description": "The time, in minutes, after which the action specified in TimeoutAction field will be performed if requested resources are unavailable."
                            },
                            "TimeoutAction": {
                                "type": "string",
                                "description": "The action that is performed after TimeoutDurationMinutes.",
                                "enum": [
                                    "TERMINATE_CLUSTER",
                                    "SWITCH_TO_ONDEMAND"
                                ]
                            },
                            "BlockDurationMinutes": {
                                "type": "integer",
                                "description": "Block duration in minutes."
                            },
                            "AllocationStrategy": {
                                "type": "string",
                                "description": "The strategy to use in launching Spot instance fleets.",
                                "enum": ["capacity-optimized"]
                            }
                        }
                    }
                }
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
        "SubnetIds": {
            "type": "array",
            "description":
                "List of SubnetIds.",
            "items": {
                "type": "string"
            }
        },
        "AvailabilityZone": {
            "type": "string",
            "description": "The Availability Zone the cluster will run in."
        },
        "AvailabilityZones": {
            "type": "array",
            "description": "List of AvailabilityZones.",
            "items": {
                "type": "string"
            }
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
        "ServiceAccessSecurityGroup": {
            "type": "string",
            "description": helptext.SERVICE_ACCESS_SECURITY_GROUP
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

KERBEROS_ATTRIBUTES_SCHEMA = {
    "type": "object",
    "properties": {
        "Realm": {
            "type": "string",
            "description": "The name of Kerberos realm."
        },
        "KdcAdminPassword": {
            "type": "string",
            "description": "The password of Kerberos administrator."
        },
        "CrossRealmTrustPrincipalPassword": {
            "type": "string",
            "description": "The password to establish cross-realm trusts."
        },
        "ADDomainJoinUser": {
            "type": "string",
            "description": "The name of the user with privileges to join instances to Active Directory."
        },
        "ADDomainJoinPassword": {
            "type": "string",
            "description": "The password of the user with privileges to join instances to Active Directory."
        }
    }
}

MANAGED_SCALING_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "ComputeLimits": {
            "type": "object",
            "description": 
                "The EC2 unit limits for a managed scaling policy. "
                "The managed scaling activity of a cluster is not allowed to go above "
                "or below these limits. The limits apply to CORE and TASK groups "
                "and exclude the capacity of the MASTER group.",
            "properties": {
               "MinimumCapacityUnits": {
                  "type": "integer",
                  "description": 
                      "The lower boundary of EC2 units. It is measured through "
                      "VCPU cores or instances for instance groups and measured "
                      "through units for instance fleets. Managed scaling "
                      "activities are not allowed beyond this boundary.",
                  "required": True
               },
               "MaximumCapacityUnits": {
                  "type": "integer",
                  "description": 
                      "The upper boundary of EC2 units. It is measured through "
                      "VCPU cores or instances for instance groups and measured "
                      "through units for instance fleets. Managed scaling "
                      "activities are not allowed beyond this boundary.",
                  "required": True
               },
               "MaximumOnDemandCapacityUnits": {
                  "type": "integer",
                  "description": 
                      "The upper boundary of on-demand EC2 units. It is measured through "
                      "VCPU cores or instances for instance groups and measured "
                      "through units for instance fleets. The on-demand units are not "
                      "allowed to scale beyond this boundary. "
                      "This value must be lower than MaximumCapacityUnits."
               },
               "UnitType": {
                  "type": "string",
                  "description": "The unit type used for specifying a managed scaling policy.",
                  "enum": ["VCPU", "Instances", "InstanceFleetUnits"],
                  "required": True
               },
               "MaximumCoreCapacityUnits": {
                  "type": "integer",
                  "description":
                      "The upper boundary of EC2 units for core node type in a cluster. "
                      "It is measured through VCPU cores or instances for instance groups "
                      "and measured through units for instance fleets. "
                      "The core units are not allowed to scale beyond this boundary. "
                      "The parameter is used to split capacity allocation between core and task nodes."
               }
            } 
        }
    }
}

PLACEMENT_GROUP_CONFIGS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "InstanceRole": {
                "type": "string",
                "description": "Role of the instance in the cluster.",
                "enum": ["MASTER", "CORE", "TASK"],
                "required": True
            },
            "PlacementStrategy": {
                "type": "string",
                "description": "EC2 Placement Group strategy associated "
                               "with instance role.",
                "enum": ["SPREAD", "PARTITION", "CLUSTER", "NONE"]
            }
        }
    }
}

AUTO_TERMINATION_POLICY_SCHEMA = {
    "type": "object",
    "properties":  {
        "IdleTimeout": {
            "type": "long",
            "description":
                "Specifies the amount of idle time in seconds after which the cluster automatically terminates. "
                "You can specify a minimum of 60 seconds and a maximum of 604800 seconds (seven days).",
        }
    }
}
