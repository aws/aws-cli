# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import logging
import os
import tempfile
import zipfile
import contextlib
import uuid
import shutil
from botocore.utils import set_value_from_jmespath

from awscli.compat import urlparse
from contextlib import contextmanager
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.yamlhelper import yaml_dump, \
    yaml_parse
import jmespath


LOG = logging.getLogger(__name__)


def is_path_value_valid(path):
    return isinstance(path, str)


def make_abs_path(directory, path):
    if is_path_value_valid(path) and not os.path.isabs(path):
        return os.path.normpath(os.path.join(directory, path))
    else:
        return path


def is_s3_url(url):
    try:
        parse_s3_url(url)
        return True
    except ValueError:
        return False


def is_local_folder(path):
    return is_path_value_valid(path) and os.path.isdir(path)


def is_local_file(path):
    return is_path_value_valid(path) and os.path.isfile(path)


def is_zip_file(path):
    return (
        is_path_value_valid(path) and
        zipfile.is_zipfile(path))


def parse_s3_url(url,
                 bucket_name_property="Bucket",
                 object_key_property="Key",
                 version_property=None):

    if isinstance(url, str) \
            and url.startswith("s3://"):

        # Python < 2.7.10 don't parse query parameters from URI with custom
        # scheme such as s3://blah/blah. As a workaround, remove scheme
        # altogether to trigger the parser "s3://foo/bar?v=1" =>"//foo/bar?v=1"
        parsed = urlparse.urlparse(url[3:])
        query = urlparse.parse_qs(parsed.query)

        if parsed.netloc and parsed.path:
            result = dict()
            result[bucket_name_property] = parsed.netloc
            result[object_key_property] = parsed.path.lstrip('/')

            # If there is a query string that has a single versionId field,
            # set the object version and return
            if version_property is not None \
                    and 'versionId' in query \
                    and len(query['versionId']) == 1:
                result[version_property] = query['versionId'][0]

            return result

    raise ValueError("URL given to the parse method is not a valid S3 url "
                     "{0}".format(url))


def upload_local_artifacts(resource_id, resource_dict, property_name,
                           parent_dir, uploader):
    """
    Upload local artifacts referenced by the property at given resource and
    return S3 URL of the uploaded object. It is the responsibility of callers
    to ensure property value is a valid string

    If path refers to a file, this method will upload the file. If path refers
    to a folder, this method will zip the folder and upload the zip to S3.
    If path is omitted, this method will zip the current working folder and
    upload.

    If path is already a path to S3 object, this method does nothing.

    :param resource_id:     Id of the CloudFormation resource
    :param resource_dict:   Dictionary containing resource definition
    :param property_name:   Property name of CloudFormation resource where this
                            local path is present
    :param parent_dir:      Resolve all relative paths with respect to this
                            directory
    :param uploader:        Method to upload files to S3

    :return:                S3 URL of the uploaded object
    :raise:                 ValueError if path is not a S3 URL or a local path
    """

    local_path = jmespath.search(property_name, resource_dict)

    if local_path is None:
        # Build the root directory and upload to S3
        local_path = parent_dir

    if is_s3_url(local_path):
        # A valid CloudFormation template will specify artifacts as S3 URLs.
        # This check is supporting the case where your resource does not
        # refer to local artifacts
        # Nothing to do if property value is an S3 URL
        LOG.debug("Property {0} of {1} is already a S3 URL"
                  .format(property_name, resource_id))
        return local_path

    local_path = make_abs_path(parent_dir, local_path)

    # Or, pointing to a folder. Zip the folder and upload
    if is_local_folder(local_path):
        return zip_and_upload(local_path, uploader)

    # Path could be pointing to a file. Upload the file
    elif is_local_file(local_path):
        return uploader.upload_with_dedup(local_path)

    raise exceptions.InvalidLocalPathError(
            resource_id=resource_id,
            property_name=property_name,
            local_path=local_path)


def zip_and_upload(local_path, uploader):
    with zip_folder(local_path) as zipfile:
            return uploader.upload_with_dedup(zipfile)


@contextmanager
def zip_folder(folder_path):
    """
    Zip the entire folder and return a file to the zip. Use this inside
    a "with" statement to cleanup the zipfile after it is used.

    :param folder_path:
    :return: Name of the zipfile
    """

    filename = os.path.join(
        tempfile.gettempdir(), "data-" + uuid.uuid4().hex)

    zipfile_name = make_zip(filename, folder_path)
    try:
        yield zipfile_name
    finally:
        if os.path.exists(zipfile_name):
            os.remove(zipfile_name)


def make_zip(filename, source_root):
    zipfile_name = "{0}.zip".format(filename)
    source_root = os.path.abspath(source_root)
    with open(zipfile_name, 'wb') as f:
        zip_file = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
        with contextlib.closing(zip_file) as zf:
            for root, dirs, files in os.walk(source_root, followlinks=True):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(
                        full_path, source_root)
                    zf.write(full_path, relative_path)

    return zipfile_name


@contextmanager
def mktempfile():
    directory = tempfile.gettempdir()
    filename = os.path.join(directory, uuid.uuid4().hex)

    try:
        with open(filename, "w+") as handle:
            yield handle
    finally:
        if os.path.exists(filename):
            os.remove(filename)


def copy_to_temp_dir(filepath):
    tmp_dir = tempfile.mkdtemp()
    dst = os.path.join(tmp_dir, os.path.basename(filepath))
    shutil.copy2(filepath, dst)
    return tmp_dir


class Resource(object):
    """
    Base class representing a CloudFormation resource that can be exported
    """

    RESOURCE_TYPE = None
    PROPERTY_NAME = None
    PACKAGE_NULL_PROPERTY = True
    # Set this property to True in base class if you want the exporter to zip
    # up the file before uploading This is useful for Lambda functions.
    FORCE_ZIP = False

    def __init__(self, uploader):
        self.uploader = uploader

    def export(self, resource_id, resource_dict, parent_dir):
        if resource_dict is None:
            return

        property_value = jmespath.search(self.PROPERTY_NAME, resource_dict)

        if not property_value and not self.PACKAGE_NULL_PROPERTY:
            return

        if isinstance(property_value, dict):
            LOG.debug("Property {0} of {1} resource is not a URL"
                      .format(self.PROPERTY_NAME, resource_id))
            return

        # If property is a file but not a zip file, place file in temp
        # folder and send the temp folder to be zipped
        temp_dir = None
        if is_local_file(property_value) and not \
                is_zip_file(property_value) and self.FORCE_ZIP:
            temp_dir = copy_to_temp_dir(property_value)
            set_value_from_jmespath(resource_dict, self.PROPERTY_NAME, temp_dir)

        try:
            self.do_export(resource_id, resource_dict, parent_dir)

        except Exception as ex:
            LOG.debug("Unable to export", exc_info=ex)
            raise exceptions.ExportFailedError(
                    resource_id=resource_id,
                    property_name=self.PROPERTY_NAME,
                    property_value=property_value,
                    ex=ex)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        Default export action is to upload artifacts and set the property to
        S3 URL of the uploaded object
        """
        uploaded_url = upload_local_artifacts(resource_id, resource_dict,
                                   self.PROPERTY_NAME,
                                   parent_dir, self.uploader)
        set_value_from_jmespath(resource_dict, self.PROPERTY_NAME, uploaded_url)


class ResourceWithS3UrlDict(Resource):
    """
    Represents CloudFormation resources that need the S3 URL to be specified as
    an dict like {Bucket: "", Key: "", Version: ""}
    """

    BUCKET_NAME_PROPERTY = None
    OBJECT_KEY_PROPERTY = None
    VERSION_PROPERTY = None

    def __init__(self, uploader):
        super(ResourceWithS3UrlDict, self).__init__(uploader)

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        Upload to S3 and set property to an dict representing the S3 url
        of the uploaded object
        """

        artifact_s3_url = \
            upload_local_artifacts(resource_id, resource_dict,
                                   self.PROPERTY_NAME,
                                   parent_dir, self.uploader)

        parsed_url = parse_s3_url(
                artifact_s3_url,
                bucket_name_property=self.BUCKET_NAME_PROPERTY,
                object_key_property=self.OBJECT_KEY_PROPERTY,
                version_property=self.VERSION_PROPERTY)
        set_value_from_jmespath(resource_dict, self.PROPERTY_NAME, parsed_url)


class ServerlessFunctionResource(Resource):
    RESOURCE_TYPE = "AWS::Serverless::Function"
    PROPERTY_NAME = "CodeUri"
    FORCE_ZIP = True


class ServerlessApiResource(Resource):
    RESOURCE_TYPE = "AWS::Serverless::Api"
    PROPERTY_NAME = "DefinitionUri"
    # Don't package the directory if DefinitionUri is omitted.
    # Necessary to support DefinitionBody
    PACKAGE_NULL_PROPERTY = False


class GraphQLSchemaResource(Resource):
    RESOURCE_TYPE = "AWS::AppSync::GraphQLSchema"
    PROPERTY_NAME = "DefinitionS3Location"
    # Don't package the directory if DefinitionS3Location is omitted.
    # Necessary to support Definition
    PACKAGE_NULL_PROPERTY = False


class AppSyncResolverRequestTemplateResource(Resource):
    RESOURCE_TYPE = "AWS::AppSync::Resolver"
    PROPERTY_NAME = "RequestMappingTemplateS3Location"
    # Don't package the directory if RequestMappingTemplateS3Location is omitted.
    # Necessary to support RequestMappingTemplate
    PACKAGE_NULL_PROPERTY = False


class AppSyncResolverResponseTemplateResource(Resource):
    RESOURCE_TYPE = "AWS::AppSync::Resolver"
    PROPERTY_NAME = "ResponseMappingTemplateS3Location"
    # Don't package the directory if ResponseMappingTemplateS3Location is omitted.
    # Necessary to support ResponseMappingTemplate
    PACKAGE_NULL_PROPERTY = False


class AppSyncFunctionConfigurationRequestTemplateResource(Resource):
    RESOURCE_TYPE = "AWS::AppSync::FunctionConfiguration"
    PROPERTY_NAME = "RequestMappingTemplateS3Location"
    # Don't package the directory if RequestMappingTemplateS3Location is omitted.
    # Necessary to support RequestMappingTemplate
    PACKAGE_NULL_PROPERTY = False


class AppSyncFunctionConfigurationResponseTemplateResource(Resource):
    RESOURCE_TYPE = "AWS::AppSync::FunctionConfiguration"
    PROPERTY_NAME = "ResponseMappingTemplateS3Location"
    # Don't package the directory if ResponseMappingTemplateS3Location is omitted.
    # Necessary to support ResponseMappingTemplate
    PACKAGE_NULL_PROPERTY = False


class LambdaFunctionResource(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::Lambda::Function"
    PROPERTY_NAME = "Code"
    BUCKET_NAME_PROPERTY = "S3Bucket"
    OBJECT_KEY_PROPERTY = "S3Key"
    VERSION_PROPERTY = "S3ObjectVersion"
    FORCE_ZIP = True


class ApiGatewayRestApiResource(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::ApiGateway::RestApi"
    PROPERTY_NAME = "BodyS3Location"
    PACKAGE_NULL_PROPERTY = False
    BUCKET_NAME_PROPERTY = "Bucket"
    OBJECT_KEY_PROPERTY = "Key"
    VERSION_PROPERTY = "Version"


class ElasticBeanstalkApplicationVersion(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::ElasticBeanstalk::ApplicationVersion"
    PROPERTY_NAME = "SourceBundle"
    BUCKET_NAME_PROPERTY = "S3Bucket"
    OBJECT_KEY_PROPERTY = "S3Key"
    VERSION_PROPERTY = None


class LambdaLayerVersionResource(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::Lambda::LayerVersion"
    PROPERTY_NAME = "Content"
    BUCKET_NAME_PROPERTY = "S3Bucket"
    OBJECT_KEY_PROPERTY = "S3Key"
    VERSION_PROPERTY = "S3ObjectVersion"
    FORCE_ZIP = True


class ServerlessLayerVersionResource(Resource):
    RESOURCE_TYPE = "AWS::Serverless::LayerVersion"
    PROPERTY_NAME = "ContentUri"
    FORCE_ZIP = True


class ServerlessRepoApplicationReadme(Resource):
    RESOURCE_TYPE = "AWS::ServerlessRepo::Application"
    PROPERTY_NAME = "ReadmeUrl"
    PACKAGE_NULL_PROPERTY = False


class ServerlessRepoApplicationLicense(Resource):
    RESOURCE_TYPE = "AWS::ServerlessRepo::Application"
    PROPERTY_NAME = "LicenseUrl"
    PACKAGE_NULL_PROPERTY = False


class StepFunctionsStateMachineDefinitionResource(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::StepFunctions::StateMachine"
    PROPERTY_NAME = "DefinitionS3Location"
    BUCKET_NAME_PROPERTY = "Bucket"
    OBJECT_KEY_PROPERTY = "Key"
    VERSION_PROPERTY = "Version"
    PACKAGE_NULL_PROPERTY = False


class ServerlessStateMachineDefinitionResource(ResourceWithS3UrlDict):
    RESOURCE_TYPE = "AWS::Serverless::StateMachine"
    PROPERTY_NAME = "DefinitionUri"
    BUCKET_NAME_PROPERTY = "Bucket"
    OBJECT_KEY_PROPERTY = "Key"
    VERSION_PROPERTY = "Version"
    PACKAGE_NULL_PROPERTY = False


class CloudFormationStackResource(Resource):
    """
    Represents CloudFormation::Stack resource that can refer to a nested
    stack template via TemplateURL property.
    """
    RESOURCE_TYPE = "AWS::CloudFormation::Stack"
    PROPERTY_NAME = "TemplateURL"

    def __init__(self, uploader):
        super(CloudFormationStackResource, self).__init__(uploader)

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        If the nested stack template is valid, this method will
        export on the nested template, upload the exported template to S3
        and set property to URL of the uploaded S3 template
        """

        template_path = resource_dict.get(self.PROPERTY_NAME, None)

        if template_path is None or is_s3_url(template_path) or \
                template_path.startswith("http://") or \
                template_path.startswith("https://"):
            # Nothing to do
            return

        abs_template_path = make_abs_path(parent_dir, template_path)
        if not is_local_file(abs_template_path):
            raise exceptions.InvalidTemplateUrlParameterError(
                    property_name=self.PROPERTY_NAME,
                    resource_id=resource_id,
                    template_path=abs_template_path)

        exported_template_dict = \
            Template(template_path, parent_dir, self.uploader).export()

        exported_template_str = yaml_dump(exported_template_dict)

        with mktempfile() as temporary_file:
            temporary_file.write(exported_template_str)
            temporary_file.flush()

            url = self.uploader.upload_with_dedup(
                    temporary_file.name, "template")

            # TemplateUrl property requires S3 URL to be in path-style format
            parts = parse_s3_url(url, version_property="Version")
            s3_path_url = self.uploader.to_path_style_s3_url(
                    parts["Key"], parts.get("Version", None))
            set_value_from_jmespath(resource_dict, self.PROPERTY_NAME, s3_path_url)


class ServerlessApplicationResource(CloudFormationStackResource):
    """
    Represents Serverless::Application resource that can refer to a nested
    app template via Location property.
    """
    RESOURCE_TYPE = "AWS::Serverless::Application"
    PROPERTY_NAME = "Location"



class GlueJobCommandScriptLocationResource(Resource):
    """
    Represents Glue::Job resource.
    """
    RESOURCE_TYPE = "AWS::Glue::Job"
    # Note the PROPERTY_NAME includes a '.' implying it's nested.
    PROPERTY_NAME = "Command.ScriptLocation"


class CodeCommitRepositoryS3Resource(ResourceWithS3UrlDict):
    """
    Represents CodeCommit::Repository resource.
    """
    RESOURCE_TYPE = "AWS::CodeCommit::Repository"
    PROPERTY_NAME = "Code.S3"
    BUCKET_NAME_PROPERTY = "Bucket"
    OBJECT_KEY_PROPERTY = "Key"
    VERSION_PROPERTY = "ObjectVersion"
    # Don't package the directory if S3 is omitted.
    PACKAGE_NULL_PROPERTY = False
    FORCE_ZIP = True


RESOURCES_EXPORT_LIST = [
    ServerlessFunctionResource,
    ServerlessApiResource,
    GraphQLSchemaResource,
    AppSyncResolverRequestTemplateResource,
    AppSyncResolverResponseTemplateResource,
    AppSyncFunctionConfigurationRequestTemplateResource,
    AppSyncFunctionConfigurationResponseTemplateResource,
    ApiGatewayRestApiResource,
    LambdaFunctionResource,
    ElasticBeanstalkApplicationVersion,
    CloudFormationStackResource,
    ServerlessApplicationResource,
    ServerlessLayerVersionResource,
    LambdaLayerVersionResource,
    GlueJobCommandScriptLocationResource,
    StepFunctionsStateMachineDefinitionResource,
    ServerlessStateMachineDefinitionResource,
    CodeCommitRepositoryS3Resource
]

METADATA_EXPORT_LIST = [
    ServerlessRepoApplicationReadme,
    ServerlessRepoApplicationLicense
]


def include_transform_export_handler(template_dict, uploader, parent_dir):
    if template_dict.get("Name", None) != "AWS::Include":
        return template_dict

    include_location = template_dict.get("Parameters", {}).get("Location", None)
    if not include_location \
            or not is_path_value_valid(include_location) \
            or is_s3_url(include_location):
        # `include_location` is either empty, or not a string, or an S3 URI
        return template_dict

    # We are confident at this point that `include_location` is a string containing the local path
    abs_include_location = os.path.join(parent_dir, include_location)
    if is_local_file(abs_include_location):
        template_dict["Parameters"]["Location"] = uploader.upload_with_dedup(abs_include_location)
    else:
        raise exceptions.InvalidLocalPathError(
            resource_id="AWS::Include",
            property_name="Location",
            local_path=abs_include_location)

    return template_dict


GLOBAL_EXPORT_DICT = {
    "Fn::Transform": include_transform_export_handler
}


class Template(object):
    """
    Class to export a CloudFormation template
    """

    def __init__(self, template_path, parent_dir, uploader,
                 resources_to_export=RESOURCES_EXPORT_LIST,
                 metadata_to_export=METADATA_EXPORT_LIST):
        """
        Reads the template and makes it ready for export
        """

        if not (is_local_folder(parent_dir) and os.path.isabs(parent_dir)):
            raise ValueError("parent_dir parameter must be "
                             "an absolute path to a folder {0}"
                             .format(parent_dir))

        abs_template_path = make_abs_path(parent_dir, template_path)
        template_dir = os.path.dirname(abs_template_path)

        with open(abs_template_path, "r") as handle:
            template_str = handle.read()

        self.template_dict = yaml_parse(template_str)
        self.template_dir = template_dir
        self.resources_to_export = resources_to_export
        self.metadata_to_export = metadata_to_export
        self.uploader = uploader

    def export_global_artifacts(self, template_dict):
        """
        Template params such as AWS::Include transforms are not specific to
        any resource type but contain artifacts that should be exported,
        here we iterate through the template dict and export params with a
        handler defined in GLOBAL_EXPORT_DICT
        """
        for key, val in template_dict.items():
            if key in GLOBAL_EXPORT_DICT:
                template_dict[key] = GLOBAL_EXPORT_DICT[key](val, self.uploader, self.template_dir)
            elif isinstance(val, dict):
                self.export_global_artifacts(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        self.export_global_artifacts(item)
        return template_dict

    def export_metadata(self, template_dict):
        """
        Exports the local artifacts referenced by the metadata section in
        the given template to an s3 bucket.

        :return: The template with references to artifacts that have been
        exported to s3.
        """
        if "Metadata" not in template_dict:
            return template_dict

        for metadata_type, metadata_dict in template_dict["Metadata"].items():
            for exporter_class in self.metadata_to_export:
                if exporter_class.RESOURCE_TYPE != metadata_type:
                    continue

                exporter = exporter_class(self.uploader)
                exporter.export(metadata_type, metadata_dict, self.template_dir)

        return template_dict

    def export(self):
        """
        Exports the local artifacts referenced by the given template to an
        s3 bucket.

        :return: The template with references to artifacts that have been
        exported to s3.
        """
        self.template_dict = self.export_metadata(self.template_dict)

        if "Resources" not in self.template_dict:
            return self.template_dict

        self.template_dict = self.export_global_artifacts(self.template_dict)

        self.export_resources(self.template_dict["Resources"])

        return self.template_dict

    def export_resources(self, resource_dict):
        for resource_id, resource in resource_dict.items():

            if resource_id.startswith("Fn::ForEach::"):
                if not isinstance(resource, list) or len(resource) != 3:
                    raise exceptions.InvalidForEachIntrinsicFunctionError(resource_id=resource_id)
                self.export_resources(resource[2])
                continue

            resource_type = resource.get("Type", None)
            resource_dict = resource.get("Properties", None)

            for exporter_class in self.resources_to_export:
                if exporter_class.RESOURCE_TYPE != resource_type:
                    continue

                # Export code resources
                exporter = exporter_class(self.uploader)
                exporter.export(resource_id, resource_dict, self.template_dir)
