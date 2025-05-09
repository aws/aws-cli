
class CloudFormationCommandError(Exception):
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        if 'message' in kwargs:
            msg = kwargs['message']
        else:
            msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class InvalidTemplatePathError(CloudFormationCommandError):
    fmt = "Invalid template path {template_path}"


class ChangeEmptyError(CloudFormationCommandError):
    fmt = "No changes to deploy. Stack {stack_name} is up to date"


class InvalidLocalPathError(CloudFormationCommandError):
    fmt = ("Parameter {property_name} of resource {resource_id} refers "
           "to a file or folder that does not exist {local_path}")


class InvalidTemplateUrlParameterError(CloudFormationCommandError):
    fmt = ("{property_name} parameter of {resource_id} resource is invalid. "
           "It must be a S3 URL or path to CloudFormation "
           "template file. Actual: {template_path}")


class ExportFailedError(CloudFormationCommandError):
    fmt = ("Unable to upload artifact {property_value} referenced "
           "by {property_name} parameter of {resource_id} resource."
           "\n"
           "{ex}")


class InvalidKeyValuePairArgumentError(CloudFormationCommandError):
    fmt = ("{value} value passed to --{argname} must be of format "
           "Key=Value")


class DeployFailedError(CloudFormationCommandError):
    fmt = \
        ("Failed to create/update the stack. Run the following command"
         "\n"
         "to fetch the list of events leading up to the failure"
         "\n"
         "aws cloudformation describe-stack-events --stack-name {stack_name}")

class DeployBucketRequiredError(CloudFormationCommandError):
    fmt = \
        ("Templates with a size greater than 51,200 bytes must be deployed "
         "via an S3 Bucket. Please add the --s3-bucket parameter to your "
         "command. The local template will be copied to that S3 bucket and "
         "then deployed.")
        
class PackageBucketRequiredError(CloudFormationCommandError):
    fmt = "Add the --s3-bucket parameter to your command to upload artifacts to S3"

class InvalidForEachIntrinsicFunctionError(CloudFormationCommandError):
    fmt = 'The value of {resource_id} has an invalid "Fn::ForEach::" format: Must be a list of three entries'

class InvalidModulePathError(CloudFormationCommandError):
    fmt = 'The value of {source} is not a valid path to a local file'

class InvalidModuleError(CloudFormationCommandError):
    fmt = 'Module parameter validation error{line_info}: {msg}'
    
    def __init__(self, **kwargs):
        # Add line information if available
        if 'line_number' in kwargs:
            kwargs['line_info'] = f" at line {kwargs['line_number']}"
        else:
            kwargs['line_info'] = ""
        super().__init__(**kwargs)
