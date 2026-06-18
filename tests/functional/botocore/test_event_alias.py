import pytest

from botocore.session import Session

# The list of services which were available when we switched over from using
# endpoint prefix in event to using service id. These should all accept
# either.
SERVICES = {
    "acm": {"endpoint_prefix": "acm", "service_id": "acm"},
    "acm-pca": {"endpoint_prefix": "acm-pca", "service_id": "acm-pca"},
    "apigateway": {
        "endpoint_prefix": "apigateway",
        "service_id": "api-gateway",
    },
    "application-autoscaling": {"service_id": "application-auto-scaling"},
    "appstream": {"endpoint_prefix": "appstream2", "service_id": "appstream"},
    "appsync": {"endpoint_prefix": "appsync", "service_id": "appsync"},
    "athena": {"endpoint_prefix": "athena", "service_id": "athena"},
    "autoscaling": {
        "endpoint_prefix": "autoscaling",
        "service_id": "auto-scaling",
    },
    "autoscaling-plans": {"service_id": "auto-scaling-plans"},
    "batch": {"endpoint_prefix": "batch", "service_id": "batch"},
    "budgets": {"endpoint_prefix": "budgets", "service_id": "budgets"},
    "ce": {"endpoint_prefix": "ce", "service_id": "cost-explorer"},
    "cloud9": {"endpoint_prefix": "cloud9", "service_id": "cloud9"},
    "clouddirectory": {
        "endpoint_prefix": "clouddirectory",
        "service_id": "clouddirectory",
    },
    "cloudformation": {
        "endpoint_prefix": "cloudformation",
        "service_id": "cloudformation",
    },
    "cloudfront": {
        "endpoint_prefix": "cloudfront",
        "service_id": "cloudfront",
    },
    "cloudhsm": {"endpoint_prefix": "cloudhsm", "service_id": "cloudhsm"},
    "cloudhsmv2": {
        "endpoint_prefix": "cloudhsmv2",
        "service_id": "cloudhsm-v2",
    },
    "cloudsearch": {
        "endpoint_prefix": "cloudsearch",
        "service_id": "cloudsearch",
    },
    "cloudsearchdomain": {
        "endpoint_prefix": "cloudsearchdomain",
        "service_id": "cloudsearch-domain",
    },
    "cloudtrail": {
        "endpoint_prefix": "cloudtrail",
        "service_id": "cloudtrail",
    },
    "cloudwatch": {
        "endpoint_prefix": "monitoring",
        "service_id": "cloudwatch",
    },
    "codebuild": {"endpoint_prefix": "codebuild", "service_id": "codebuild"},
    "codecommit": {
        "endpoint_prefix": "codecommit",
        "service_id": "codecommit",
    },
    "codedeploy": {
        "endpoint_prefix": "codedeploy",
        "service_id": "codedeploy",
    },
    "codepipeline": {
        "endpoint_prefix": "codepipeline",
        "service_id": "codepipeline",
    },
    "cognito-identity": {
        "endpoint_prefix": "cognito-identity",
        "service_id": "cognito-identity",
    },
    "cognito-idp": {
        "endpoint_prefix": "cognito-idp",
        "service_id": "cognito-identity-provider",
    },
    "cognito-sync": {
        "endpoint_prefix": "cognito-sync",
        "service_id": "cognito-sync",
    },
    "comprehend": {
        "endpoint_prefix": "comprehend",
        "service_id": "comprehend",
    },
    "config": {"endpoint_prefix": "config", "service_id": "config-service"},
    "connect": {"endpoint_prefix": "connect", "service_id": "connect"},
    "cur": {
        "endpoint_prefix": "cur",
        "service_id": "cost-and-usage-report-service",
    },
    "datapipeline": {
        "endpoint_prefix": "datapipeline",
        "service_id": "data-pipeline",
    },
    "dax": {"endpoint_prefix": "dax", "service_id": "dax"},
    "devicefarm": {
        "endpoint_prefix": "devicefarm",
        "service_id": "device-farm",
    },
    "directconnect": {
        "endpoint_prefix": "directconnect",
        "service_id": "direct-connect",
    },
    "discovery": {
        "endpoint_prefix": "discovery",
        "service_id": "application-discovery-service",
    },
    "dlm": {"endpoint_prefix": "dlm", "service_id": "dlm"},
    "dms": {
        "endpoint_prefix": "dms",
        "service_id": "database-migration-service",
    },
    "ds": {"endpoint_prefix": "ds", "service_id": "directory-service"},
    "dynamodb": {"endpoint_prefix": "dynamodb", "service_id": "dynamodb"},
    "dynamodbstreams": {
        "endpoint_prefix": "streams.dynamodb",
        "service_id": "dynamodb-streams",
    },
    "ec2": {"endpoint_prefix": "ec2", "service_id": "ec2"},
    "ecr": {"endpoint_prefix": "ecr", "service_id": "ecr"},
    "ecs": {"endpoint_prefix": "ecs", "service_id": "ecs"},
    "efs": {"endpoint_prefix": "elasticfilesystem", "service_id": "efs"},
    "eks": {"endpoint_prefix": "eks", "service_id": "eks"},
    "elasticache": {
        "endpoint_prefix": "elasticache",
        "service_id": "elasticache",
    },
    "elasticbeanstalk": {
        "endpoint_prefix": "elasticbeanstalk",
        "service_id": "elastic-beanstalk",
    },
    "elb": {
        "endpoint_prefix": "elasticloadbalancing",
        "service_id": "elastic-load-balancing",
    },
    "elbv2": {"service_id": "elastic-load-balancing-v2"},
    "emr": {"endpoint_prefix": "elasticmapreduce", "service_id": "emr"},
    "es": {"endpoint_prefix": "es", "service_id": "elasticsearch-service"},
    "events": {"endpoint_prefix": "events", "service_id": "cloudwatch-events"},
    "firehose": {"endpoint_prefix": "firehose", "service_id": "firehose"},
    "fms": {"endpoint_prefix": "fms", "service_id": "fms"},
    "gamelift": {"endpoint_prefix": "gamelift", "service_id": "gamelift"},
    "glacier": {"endpoint_prefix": "glacier", "service_id": "glacier"},
    "glue": {"endpoint_prefix": "glue", "service_id": "glue"},
    "greengrass": {
        "endpoint_prefix": "greengrass",
        "service_id": "greengrass",
    },
    "guardduty": {"endpoint_prefix": "guardduty", "service_id": "guardduty"},
    "health": {"endpoint_prefix": "health", "service_id": "health"},
    "iam": {"endpoint_prefix": "iam", "service_id": "iam"},
    "importexport": {
        "endpoint_prefix": "importexport",
        "service_id": "importexport",
    },
    "inspector": {"endpoint_prefix": "inspector", "service_id": "inspector"},
    "iot": {"endpoint_prefix": "iot", "service_id": "iot"},
    "iot-data": {
        "endpoint_prefix": "data.iot",
        "service_id": "iot-data-plane",
    },
    "iot-jobs-data": {
        "endpoint_prefix": "data.jobs.iot",
        "service_id": "iot-jobs-data-plane",
    },
    "kinesis": {"endpoint_prefix": "kinesis", "service_id": "kinesis"},
    "kinesis-video-archived-media": {
        "service_id": "kinesis-video-archived-media"
    },
    "kinesis-video-media": {"service_id": "kinesis-video-media"},
    "kinesisanalytics": {
        "endpoint_prefix": "kinesisanalytics",
        "service_id": "kinesis-analytics",
    },
    "kinesisvideo": {
        "endpoint_prefix": "kinesisvideo",
        "service_id": "kinesis-video",
    },
    "kms": {"endpoint_prefix": "kms", "service_id": "kms"},
    "lambda": {"endpoint_prefix": "lambda", "service_id": "lambda"},
    "lex-models": {
        "endpoint_prefix": "models.lex",
        "service_id": "lex-model-building-service",
    },
    "lex-runtime": {
        "endpoint_prefix": "runtime.lex",
        "service_id": "lex-runtime-service",
    },
    "lightsail": {"endpoint_prefix": "lightsail", "service_id": "lightsail"},
    "logs": {"endpoint_prefix": "logs", "service_id": "cloudwatch-logs"},
    "machinelearning": {
        "endpoint_prefix": "machinelearning",
        "service_id": "machine-learning",
    },
    "marketplace-entitlement": {
        "endpoint_prefix": "entitlement.marketplace",
        "service_id": "marketplace-entitlement-service",
    },
    "marketplacecommerceanalytics": {
        "endpoint_prefix": "marketplacecommerceanalytics",
        "service_id": "marketplace-commerce-analytics",
    },
    "mediaconvert": {
        "endpoint_prefix": "mediaconvert",
        "service_id": "mediaconvert",
    },
    "medialive": {"endpoint_prefix": "medialive", "service_id": "medialive"},
    "mediapackage": {
        "endpoint_prefix": "mediapackage",
        "service_id": "mediapackage",
    },
    "mediastore": {
        "endpoint_prefix": "mediastore",
        "service_id": "mediastore",
    },
    "mediastore-data": {
        "endpoint_prefix": "data.mediastore",
        "service_id": "mediastore-data",
    },
    "mediatailor": {
        "endpoint_prefix": "api.mediatailor",
        "service_id": "mediatailor",
    },
    "meteringmarketplace": {
        "endpoint_prefix": "metering.marketplace",
        "service_id": "marketplace-metering",
    },
    "mgh": {"endpoint_prefix": "mgh", "service_id": "migration-hub"},
    "mq": {"endpoint_prefix": "mq", "service_id": "mq"},
    "mturk": {"endpoint_prefix": "mturk-requester", "service_id": "mturk"},
    "neptune": {"service_id": "neptune"},
    "organizations": {
        "endpoint_prefix": "organizations",
        "service_id": "organizations",
    },
    "pi": {"endpoint_prefix": "pi", "service_id": "pi"},
    "pinpoint": {"endpoint_prefix": "pinpoint", "service_id": "pinpoint"},
    "polly": {"endpoint_prefix": "polly", "service_id": "polly"},
    "pricing": {"endpoint_prefix": "api.pricing", "service_id": "pricing"},
    "rds": {"endpoint_prefix": "rds", "service_id": "rds"},
    "redshift": {"endpoint_prefix": "redshift", "service_id": "redshift"},
    "rekognition": {
        "endpoint_prefix": "rekognition",
        "service_id": "rekognition",
    },
    "resource-groups": {
        "endpoint_prefix": "resource-groups",
        "service_id": "resource-groups",
    },
    "resourcegroupstaggingapi": {
        "endpoint_prefix": "tagging",
        "service_id": "resource-groups-tagging-api",
    },
    "route53": {"endpoint_prefix": "route53", "service_id": "route-53"},
    "route53domains": {
        "endpoint_prefix": "route53domains",
        "service_id": "route-53-domains",
    },
    "s3": {"endpoint_prefix": "s3", "service_id": "s3"},
    "sagemaker": {
        "endpoint_prefix": "api.sagemaker",
        "service_id": "sagemaker",
    },
    "sagemaker-runtime": {
        "endpoint_prefix": "runtime.sagemaker",
        "service_id": "sagemaker-runtime",
    },
    "sdb": {"endpoint_prefix": "sdb", "service_id": "simpledb"},
    "secretsmanager": {
        "endpoint_prefix": "secretsmanager",
        "service_id": "secrets-manager",
    },
    "serverlessrepo": {
        "endpoint_prefix": "serverlessrepo",
        "service_id": "serverlessapplicationrepository",
    },
    "servicecatalog": {
        "endpoint_prefix": "servicecatalog",
        "service_id": "service-catalog",
    },
    "servicediscovery": {
        "endpoint_prefix": "servicediscovery",
        "service_id": "servicediscovery",
    },
    "ses": {"endpoint_prefix": "email", "service_id": "ses"},
    "shield": {"endpoint_prefix": "shield", "service_id": "shield"},
    "snowball": {"endpoint_prefix": "snowball", "service_id": "snowball"},
    "sns": {"endpoint_prefix": "sns", "service_id": "sns"},
    "sqs": {"endpoint_prefix": "sqs", "service_id": "sqs"},
    "ssm": {"endpoint_prefix": "ssm", "service_id": "ssm"},
    "stepfunctions": {"endpoint_prefix": "states", "service_id": "sfn"},
    "storagegateway": {
        "endpoint_prefix": "storagegateway",
        "service_id": "storage-gateway",
    },
    "sts": {"endpoint_prefix": "sts", "service_id": "sts"},
    "support": {"endpoint_prefix": "support", "service_id": "support"},
    "swf": {"endpoint_prefix": "swf", "service_id": "swf"},
    "transcribe": {
        "endpoint_prefix": "transcribe",
        "service_id": "transcribe",
    },
    "translate": {"endpoint_prefix": "translate", "service_id": "translate"},
    "waf": {"endpoint_prefix": "waf", "service_id": "waf"},
    "waf-regional": {
        "endpoint_prefix": "waf-regional",
        "service_id": "waf-regional",
    },
    "workdocs": {"endpoint_prefix": "workdocs", "service_id": "workdocs"},
    "workmail": {"endpoint_prefix": "workmail", "service_id": "workmail"},
    "workspaces": {
        "endpoint_prefix": "workspaces",
        "service_id": "workspaces",
    },
    "xray": {"endpoint_prefix": "xray", "service_id": "xray"},
}


def _event_aliases():
    for client_name in SERVICES.keys():
        service_id = SERVICES[client_name]['service_id']
        yield client_name, service_id


def _event_aliases_with_endpoint_prefix():
    for client_name in SERVICES.keys():
        endpoint_prefix = SERVICES[client_name].get('endpoint_prefix')
        if endpoint_prefix is not None:
            yield client_name, endpoint_prefix


@pytest.mark.parametrize(
    "client_name, endpoint_prefix", _event_aliases_with_endpoint_prefix()
)
def test_event_alias_by_endpoint_prefix(client_name, endpoint_prefix):
    _assert_handler_called(client_name, endpoint_prefix)


@pytest.mark.parametrize("client_name, service_id", _event_aliases())
def test_event_alias_by_service_id(client_name, service_id):
    _assert_handler_called(client_name, service_id)


@pytest.mark.parametrize("client_name, service_id", _event_aliases())
def test_event_alias_by_client_name(client_name, service_id):
    _assert_handler_called(client_name, client_name)


def _assert_handler_called(client_name, event_part):
    hook_calls = []

    def _hook(**kwargs):
        hook_calls.append(kwargs['event_name'])

    session = _get_session()
    session.register(f'creating-client-class.{event_part}', _hook)
    session.create_client(client_name)
    assert len(hook_calls) == 1


def _get_session():
    session = Session()
    session.set_credentials('foo', 'bar')
    session.set_config_variable('region', 'us-west-2')
    session.config_filename = 'no-exist-foo'
    return session
