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

# Declare all the constants used by EMR in this file.

EC2_ROLE_NAME = "EMR_EC2_DefaultRole"
EMR_ROLE_NAME = "EMR_DefaultRole"
EC2_ROLE_ARN_PATTERN = ("arn:{{region_suffix}}:iam::aws:policy/service-role/"
                        "AmazonElasticMapReduceforEC2Role")
EMR_ROLE_ARN_PATTERN = ("arn:{{region_suffix}}:iam::aws:policy/service-role/"
                        "AmazonElasticMapReduceRole")

# Action on failure
CONTINUE = 'CONTINUE'
CANCEL_AND_WAIT = 'CANCEL_AND_WAIT'
TERMINATE_CLUSTER = 'TERMINATE_CLUSTER'
DEFAULT_FAILURE_ACTION = CONTINUE

# Market type
SPOT = 'SPOT'
ON_DEMAND = 'ON_DEMAND'

SCRIPT_RUNNER_PATH = '/libs/script-runner/script-runner.jar'
COMMAND_RUNNER = 'command-runner.jar'
DEBUGGING_PATH = '/libs/state-pusher/0.1/fetch'
DEBUGGING_COMMAND = 'state-pusher-script'
DEBUGGING_NAME = 'Setup Hadoop Debugging'

CONFIG_HADOOP_PATH = '/bootstrap-actions/configure-hadoop'

# S3 copy bootstrap action
S3_GET_BA_NAME = 'S3 get'
S3_GET_BA_SRC = '-s'
S3_GET_BA_DEST = '-d'
S3_GET_BA_FORCE = '-f'

# EMRFS
EMRFS_BA_NAME = 'Setup EMRFS'
EMRFS_BA_ARG_KEY = '-e'
EMRFS_CONSISTENT_KEY = 'fs.s3.consistent'
EMRFS_SSE_KEY = 'fs.s3.enableServerSideEncryption'
EMRFS_RETRY_COUNT_KEY = 'fs.s3.consistent.retryCount'
EMRFS_RETRY_PERIOD_KEY = 'fs.s3.consistent.retryPeriodSeconds'
EMRFS_CSE_KEY = 'fs.s3.cse.enabled'
EMRFS_CSE_KMS_KEY_ID_KEY = 'fs.s3.cse.kms.keyId'
EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY = \
    'fs.s3.cse.encryptionMaterialsProvider'
EMRFS_CSE_CUSTOM_PROVIDER_URI_KEY = 'fs.s3.cse.custom.provider.uri'

EMRFS_CSE_KMS_PROVIDER_FULL_CLASS_NAME = ('com.amazon.ws.emr.hadoop.fs.cse.'
                                          'KMSEncryptionMaterialsProvider')
EMRFS_CSE_CUSTOM_S3_GET_BA_PATH = 'file:/usr/share/aws/emr/scripts/s3get'
EMRFS_CUSTOM_DEST_PATH = '/usr/share/aws/emr/auxlib'

EMRFS_SERVER_SIDE = 'SERVERSIDE'
EMRFS_CLIENT_SIDE = 'CLIENTSIDE'
EMRFS_KMS = 'KMS'
EMRFS_CUSTOM = 'CUSTOM'

EMRFS_SITE = 'emrfs-site'

MAX_BOOTSTRAP_ACTION_NUMBER = 16
BOOTSTRAP_ACTION_NAME = 'Bootstrap action'

HIVE_BASE_PATH = '/libs/hive'
HIVE_SCRIPT_PATH = '/libs/hive/hive-script'
HIVE_SCRIPT_COMMAND = 'hive-script'

PIG_BASE_PATH = '/libs/pig'
PIG_SCRIPT_PATH = '/libs/pig/pig-script'
PIG_SCRIPT_COMMAND = 'pig-script'

GANGLIA_INSTALL_BA_PATH = '/bootstrap-actions/install-ganglia'

# HBase
HBASE_INSTALL_BA_PATH = '/bootstrap-actions/setup-hbase'
HBASE_PATH_HADOOP1_INSTALL_JAR = '/home/hadoop/lib/hbase-0.92.0.jar'
HBASE_PATH_HADOOP2_INSTALL_JAR = '/home/hadoop/lib/hbase.jar'
HBASE_INSTALL_ARG = ['emr.hbase.backup.Main', '--start-master']
HBASE_JAR_PATH = '/home/hadoop/lib/hbase.jar'
HBASE_MAIN = 'emr.hbase.backup.Main'

# HBase commands
HBASE_RESTORE = '--restore'
HBASE_BACKUP_DIR_FOR_RESTORE = '--backup-dir-to-restore'
HBASE_BACKUP_VERSION_FOR_RESTORE = '--backup-version'
HBASE_BACKUP = '--backup'
HBASE_SCHEDULED_BACKUP = '--set-scheduled-backup'
HBASE_BACKUP_DIR = '--backup-dir'
HBASE_INCREMENTAL_BACKUP_INTERVAL = '--incremental-backup-time-interval'
HBASE_INCREMENTAL_BACKUP_INTERVAL_UNIT = '--incremental-backup-time-unit'
HBASE_FULL_BACKUP_INTERVAL = '--full-backup-time-interval'
HBASE_FULL_BACKUP_INTERVAL_UNIT = '--full-backup-time-unit'
HBASE_DISABLE_FULL_BACKUP = '--disable-full-backups'
HBASE_DISABLE_INCREMENTAL_BACKUP = '--disable-incremental-backups'
HBASE_BACKUP_STARTTIME = '--start-time'
HBASE_BACKUP_CONSISTENT = '--consistent'
HBASE_BACKUP_STEP_NAME = 'Backup HBase'
HBASE_RESTORE_STEP_NAME = 'Restore HBase'
HBASE_SCHEDULE_BACKUP_STEP_NAME = 'Modify Backup Schedule'

IMPALA_INSTALL_PATH = '/libs/impala/setup-impala'

# Step
HADOOP_STREAMING_PATH = '/home/hadoop/contrib/streaming/hadoop-streaming.jar'
HADOOP_STREAMING_COMMAND = 'hadoop-streaming'

CUSTOM_JAR = 'custom_jar'
HIVE = 'hive'
PIG = 'pig'
IMPALA = 'impala'
STREAMING = 'streaming'
GANGLIA = 'ganglia'
HBASE = 'hbase'
SPARK = 'spark'

DEFAULT_CUSTOM_JAR_STEP_NAME = 'Custom JAR'
DEFAULT_STREAMING_STEP_NAME = 'Streaming program'
DEFAULT_HIVE_STEP_NAME = 'Hive program'
DEFAULT_PIG_STEP_NAME = 'Pig program'
DEFAULT_IMPALA_STEP_NAME = 'Impala program'
DEFAULT_SPARK_STEP_NAME = 'Spark application'

ARGS = '--args'
RUN_HIVE_SCRIPT = '--run-hive-script'
HIVE_VERSIONS = '--hive-versions'
HIVE_STEP_CONFIG = 'HiveStepConfig'
RUN_PIG_SCRIPT = '--run-pig-script'
PIG_VERSIONS = '--pig-versions'
PIG_STEP_CONFIG = 'PigStepConfig'
RUN_IMPALA_SCRIPT = '--run-impala-script'
SPARK_SUBMIT_PATH = '/home/hadoop/spark/bin/spark-submit'
SPARK_SUBMIT_COMMAND = 'spark-submit'
IMPALA_STEP_CONFIG = 'ImpalaStepConfig'
SPARK_STEP_CONFIG = 'SparkStepConfig'
STREAMING_STEP_CONFIG = 'StreamingStepConfig'
CUSTOM_JAR_STEP_CONFIG = 'CustomJARStepConfig'

INSTALL_PIG_ARG = '--install-pig'
INSTALL_PIG_NAME = 'Install Pig'
INSTALL_HIVE_ARG = '--install-hive'
INSTALL_HIVE_NAME = 'Install Hive'
HIVE_SITE_KEY = '--hive-site'
INSTALL_HIVE_SITE_ARG = '--install-hive-site'
INSTALL_HIVE_SITE_NAME = 'Install Hive Site Configuration'
BASE_PATH_ARG = '--base-path'
INSTALL_GANGLIA_NAME = 'Install Ganglia'
INSTALL_HBASE_NAME = 'Install HBase'
START_HBASE_NAME = 'Start HBase'
INSTALL_IMPALA_NAME = 'Install Impala'
IMPALA_VERSION = '--impala-version'
IMPALA_CONF = '--impala-conf'

FULL = 'full'
INCREMENTAL = 'incremental'

MINUTES = 'minutes'
HOURS = 'hours'
DAYS = 'days'
NOW = 'now'

TRUE = 'true'
FALSE = 'false'

EC2 = 'ec2'
EMR = 'elasticmapreduce'

LATEST = 'latest'

APPLICATIONS = ["HIVE", "PIG", "HBASE", "GANGLIA", "IMPALA", "SPARK", "MAPR",
                "MAPR_M3", "MAPR_M5", "MAPR_M7"]

SSH_USER = 'hadoop'
STARTING_STATES = ['STARTING', 'BOOTSTRAPPING']
TERMINATED_STATES = ['TERMINATED', 'TERMINATING', 'TERMINATED_WITH_ERRORS']

# list-clusters
LIST_CLUSTERS_ACTIVE_STATES = ['STARTING', 'BOOTSTRAPPING', 'RUNNING',
                               'WAITING', 'TERMINATING']
LIST_CLUSTERS_TERMINATED_STATES = ['TERMINATED']
LIST_CLUSTERS_FAILED_STATES = ['TERMINATED_WITH_ERRORS']
