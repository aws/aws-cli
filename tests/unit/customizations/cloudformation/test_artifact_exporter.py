import mock
import botocore.session
import tempfile
import os
import string
import random
import zipfile

from nose.tools import assert_true, assert_false, assert_equal
from contextlib import contextmanager,closing
from mock import patch, Mock, MagicMock
from botocore.stub import Stubber
from awscli.testutils import unittest, FileCreator
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.artifact_exporter \
    import is_s3_url, parse_s3_url, is_local_file, is_local_folder, \
    upload_local_artifacts, zip_folder, make_abs_path, make_zip, \
    Template, Resource, ResourceWithS3UrlDict, ServerlessApiResource, \
    ServerlessFunctionResource, LambdaFunctionResource, ApiGatewayRestApiResource, \
    ElasticBeanstalkApplicationVersion, CloudFormationStackResource


def test_is_s3_url():
    valid = [
        "s3://foo/bar",
        "s3://foo/bar/baz/cat/dog",
        "s3://foo/bar?versionId=abc",
        "s3://foo/bar/baz?versionId=abc&versionId=123",
        "s3://foo/bar/baz?versionId=abc",
        "s3://www.amazon.com/foo/bar",
        "s3://my-new-bucket/foo/bar?a=1&a=2&a=3&b=1",
    ]

    invalid = [

        # For purposes of exporter, we need S3 URLs to point to an object
        # and not a bucket
        "s3://foo",

        # two versionIds is invalid
        "https://s3-eu-west-1.amazonaws.com/bucket/key",
        "https://www.amazon.com"
    ]

    for url in valid:
        yield _assert_is_valid_s3_url, url

    for url in invalid:
        yield _assert_is_invalid_s3_url, url

def _assert_is_valid_s3_url(url):
    assert_true(is_s3_url(url), "{0} should be valid".format(url))

def _assert_is_invalid_s3_url(url):
    assert_false(is_s3_url(url), "{0} should be valid".format(url))

def test_all_resources_export():
    uploaded_s3_url = "s3://foo/bar?versionId=baz"

    setup = [
        {
            "class": ServerlessFunctionResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": ServerlessApiResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": ApiGatewayRestApiResource,
            "expected_result": {
                "Bucket": "foo", "Key": "bar", "Version": "baz"
            }
        },

        {
            "class": LambdaFunctionResource,
            "expected_result": {
                "S3Bucket": "foo", "S3Key": "bar", "S3ObjectVersion": "baz"
            }
        },

        {
            "class": ElasticBeanstalkApplicationVersion,
            "expected_result": {
                "S3Bucket": "foo", "S3Key": "bar"
            }
        },
    ]

    with patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts") as upload_local_artifacts_mock:
        for test in setup:
            yield _helper_verify_export_resources, \
                    test["class"], uploaded_s3_url, \
                    upload_local_artifacts_mock, \
                    test["expected_result"]


def _helper_verify_export_resources(
        test_class, uploaded_s3_url, upload_local_artifacts_mock,
        expected_result):

    s3_uploader_mock = Mock()
    upload_local_artifacts_mock.reset_mock()

    resource_id = "id"
    resource_dict = {}
    parent_dir = "dir"

    upload_local_artifacts_mock.return_value = uploaded_s3_url

    resource_obj = test_class(s3_uploader_mock)

    resource_obj.export(resource_id, resource_dict, parent_dir)

    upload_local_artifacts_mock.assert_called_once_with(resource_id,
                                                        resource_dict,
                                                        test_class.PROPERTY_NAME,
                                                        parent_dir,
                                                        s3_uploader_mock)
    result = resource_dict[test_class.PROPERTY_NAME]
    assert_equal(result, expected_result)


class TestArtifactExporter(unittest.TestCase):

    def setUp(self):
        self.s3_uploader_mock = Mock()

    def test_parse_s3_url(self):

        valid = [
            {
                "url": "s3://foo/bar",
                "result": {"Bucket": "foo", "Key": "bar"}
            },
            {
                "url": "s3://foo/bar/cat/dog",
                "result": {"Bucket": "foo", "Key": "bar/cat/dog"}
            },
            {
                "url": "s3://foo/bar/baz?versionId=abc&param1=val1&param2=val2",
                "result": {"Bucket": "foo", "Key": "bar/baz", "VersionId": "abc"}
            },
            {
                # VersionId is not returned if there are more than one versionId
                # keys in query parameter
                "url": "s3://foo/bar/baz?versionId=abc&versionId=123",
                "result": {"Bucket": "foo", "Key": "bar/baz"}
            }
        ]

        invalid = [

            # For purposes of exporter, we need S3 URLs to point to an object
            # and not a bucket
            "s3://foo",

            # two versionIds is invalid
            "https://s3-eu-west-1.amazonaws.com/bucket/key",
            "https://www.amazon.com"
        ]

        for config in valid:
            result = parse_s3_url(config["url"],
                                  bucket_name_property="Bucket",
                                  object_key_property="Key",
                                  version_property="VersionId")

            self.assertEquals(result, config["result"])

        for url in invalid:
            with self.assertRaises(ValueError):
                parse_s3_url(url)

    def test_is_local_file(self):
        with tempfile.NamedTemporaryFile() as handle:
            self.assertTrue(is_local_file(handle.name))
            self.assertFalse(is_local_folder(handle.name))

    def test_is_local_folder(self):
        with self.make_temp_dir() as filename:
            self.assertTrue(is_local_folder(filename))
            self.assertFalse(is_local_file(filename))

    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_local_file(self, zip_and_upload_mock):
        # Case 1: Artifact path is a relative path
        # Verifies that we package local artifacts appropriately
        property_name = "property"
        resource_id = "resource_id"
        expected_s3_url = "s3://foo/bar?versionId=baz"

        self.s3_uploader_mock.upload_with_dedup.return_value = expected_s3_url

        with tempfile.NamedTemporaryFile() as handle:
            # Artifact is a file in the temporary directory
            artifact_path = handle.name
            parent_dir = tempfile.gettempdir()

            resource_dict = {property_name: artifact_path}
            result = upload_local_artifacts(resource_id,
                                            resource_dict,
                                            property_name,
                                            parent_dir,
                                            self.s3_uploader_mock)
            self.assertEquals(result, expected_s3_url)

            # Internally the method would convert relative paths to absolute
            # path, with respect to the parent directory
            absolute_artifact_path = make_abs_path(parent_dir, artifact_path)
            self.s3_uploader_mock.upload_with_dedup.assert_called_with(absolute_artifact_path)

            zip_and_upload_mock.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_local_file_abs_path(self, zip_and_upload_mock):
        # Case 2: Artifact path is an absolute path
        # Verifies that we package local artifacts appropriately
        property_name = "property"
        resource_id = "resource_id"
        expected_s3_url = "s3://foo/bar?versionId=baz"

        self.s3_uploader_mock.upload_with_dedup.return_value = expected_s3_url

        with tempfile.NamedTemporaryFile() as handle:
            parent_dir = tempfile.gettempdir()
            artifact_path = make_abs_path(parent_dir, handle.name)

            resource_dict = {property_name: artifact_path}
            result = upload_local_artifacts(resource_id,
                                            resource_dict,
                                            property_name,
                                            parent_dir,
                                            self.s3_uploader_mock)
            self.assertEquals(result, expected_s3_url)

            self.s3_uploader_mock.upload_with_dedup.assert_called_with(artifact_path)
            zip_and_upload_mock.assert_not_called()


    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_local_folder(self, zip_and_upload_mock):
        property_name = "property"
        resource_id = "resource_id"
        expected_s3_url = "s3://foo/bar?versionId=baz"

        zip_and_upload_mock.return_value = expected_s3_url

        #  Artifact path is a Directory
        with self.make_temp_dir() as artifact_path:
            # Artifact is a file in the temporary directory
            parent_dir = tempfile.gettempdir()
            resource_dict = {property_name: artifact_path}

            result = upload_local_artifacts(resource_id,
                                            resource_dict,
                                            property_name,
                                            parent_dir,
                                            Mock())
            self.assertEquals(result, expected_s3_url)

            absolute_artifact_path = make_abs_path(parent_dir, artifact_path)

            zip_and_upload_mock.assert_called_once_with(absolute_artifact_path,
                                                        mock.ANY)



    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_no_path(self, zip_and_upload_mock):
        property_name = "property"
        resource_id = "resource_id"
        expected_s3_url = "s3://foo/bar?versionId=baz"

        zip_and_upload_mock.return_value = expected_s3_url

        # If you don't specify a path, we will default to Current Working Dir
        resource_dict = {}
        parent_dir = tempfile.gettempdir()

        result = upload_local_artifacts(resource_id,
                                        resource_dict,
                                        property_name,
                                        parent_dir,
                                        self.s3_uploader_mock)
        self.assertEquals(result, expected_s3_url)

        zip_and_upload_mock.assert_called_once_with(parent_dir, mock.ANY)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_s3_url(self,
                                           zip_and_upload_mock):
        property_name = "property"
        resource_id = "resource_id"
        object_s3_url = "s3://foo/bar?versionId=baz"

        # If URL is already S3 URL, this will be returned without zip/upload
        resource_dict = {property_name: object_s3_url}
        parent_dir = tempfile.gettempdir()

        result = upload_local_artifacts(resource_id,
                                        resource_dict,
                                        property_name,
                                        parent_dir,
                                        self.s3_uploader_mock)
        self.assertEquals(result, object_s3_url)

        zip_and_upload_mock.assert_not_called()
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    def test_upload_local_artifacts_invalid_value(self, zip_and_upload_mock):
        property_name = "property"
        resource_id = "resource_id"
        parent_dir = tempfile.gettempdir()

        with self.assertRaises(exceptions.InvalidLocalPathError):
            non_existent_file = "some_random_filename"
            resource_dict = {property_name: non_existent_file}
            upload_local_artifacts(resource_id,
                                   resource_dict,
                                   property_name,
                                   parent_dir,
                                   self.s3_uploader_mock)

        with self.assertRaises(exceptions.InvalidLocalPathError):
            non_existent_file = ["invalid datatype"]
            resource_dict = {property_name: non_existent_file}
            upload_local_artifacts(resource_id,
                                   resource_dict,
                                   property_name,
                                   parent_dir,
                                   self.s3_uploader_mock)

        zip_and_upload_mock.assert_not_called()
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()


    @patch("awscli.customizations.cloudformation.artifact_exporter.make_zip")
    def test_zip_folder(self, make_zip_mock):
        zip_file_name = "name.zip"
        make_zip_mock.return_value = zip_file_name

        with self.make_temp_dir() as dirname:
            with zip_folder(dirname) as actual_zip_file_name:
                self.assertEqual(actual_zip_file_name, zip_file_name)

        make_zip_mock.assert_called_once_with(mock.ANY, dirname)

    @patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts")
    def test_resource(self, upload_local_artifacts_mock):
        # Property value is a path to file

        class MockResource(Resource):
            PROPERTY_NAME = "foo"

        resource = MockResource(self.s3_uploader_mock)

        resource_id = "id"
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = "/path/to/file"
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        upload_local_artifacts_mock.return_value = s3_url

        resource.export(resource_id, resource_dict, parent_dir)

        upload_local_artifacts_mock.assert_called_once_with(resource_id,
                                                            resource_dict,
                                                            resource.PROPERTY_NAME,
                                                            parent_dir,
                                                            self.s3_uploader_mock)

        self.assertEquals(resource_dict[resource.PROPERTY_NAME], s3_url)

    @patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts")
    def test_resource_empty_property_value(self, upload_local_artifacts_mock):
        # Property value is empty

        class MockResource(Resource):
            PROPERTY_NAME = "foo"
        resource = MockResource(self.s3_uploader_mock)

        resource_id = "id"
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = "/path/to/file"
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        upload_local_artifacts_mock.return_value = s3_url
        resource_dict = {}
        resource.export(resource_id, resource_dict, parent_dir)
        upload_local_artifacts_mock.assert_called_once_with(resource_id,
                                                            resource_dict,
                                                            resource.PROPERTY_NAME,
                                                            parent_dir,
                                                            self.s3_uploader_mock)
        self.assertEquals(resource_dict[resource.PROPERTY_NAME], s3_url)

    @patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts")
    def test_resource_property_value_dict(self, upload_local_artifacts_mock):
        # Property value is a dictionary. Export should not upload anything

        class MockResource(Resource):
            PROPERTY_NAME = "foo"

        resource = MockResource(self.s3_uploader_mock)
        resource_id = "id"
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = "/path/to/file"
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        upload_local_artifacts_mock.return_value = s3_url
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = {"a": "b"}
        resource.export(resource_id, resource_dict, parent_dir)
        upload_local_artifacts_mock.assert_not_called()
        self.assertEquals(resource_dict, {"foo": {"a": "b"}})


    @patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts")
    def test_resource_export_fails(self, upload_local_artifacts_mock):

        class MockResource(Resource):
            PROPERTY_NAME = "foo"

        resource = MockResource(self.s3_uploader_mock)
        resource_id = "id"
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = "/path/to/file"
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        upload_local_artifacts_mock.side_effect = RuntimeError
        resource_dict = {}

        with self.assertRaises(exceptions.ExportFailedError):
            resource.export(resource_id, resource_dict, parent_dir)


    @patch("awscli.customizations.cloudformation.artifact_exporter.upload_local_artifacts")
    def test_resource_with_s3_url_dict(self, upload_local_artifacts_mock):
        """
        Checks if we properly export from the Resource classc
        :return:
        """

        self.assertTrue(issubclass(ResourceWithS3UrlDict, Resource))

        class MockResource(ResourceWithS3UrlDict):
            PROPERTY_NAME = "foo"
            BUCKET_NAME_PROPERTY = "b"
            OBJECT_KEY_PROPERTY = "o"
            VERSION_PROPERTY = "v"

        resource = MockResource(self.s3_uploader_mock)

        # Case 1: Property value is a path to file
        resource_id = "id"
        resource_dict = {}
        resource_dict[resource.PROPERTY_NAME] = "/path/to/file"
        parent_dir = "dir"
        s3_url = "s3://bucket/key1/key2?versionId=SomeVersionNumber"

        upload_local_artifacts_mock.return_value = s3_url

        resource.export(resource_id, resource_dict, parent_dir)

        upload_local_artifacts_mock.assert_called_once_with(resource_id,
                                                            resource_dict,
                                                            resource.PROPERTY_NAME,
                                                            parent_dir,
                                                            self.s3_uploader_mock)

        self.assertEquals(resource_dict[resource.PROPERTY_NAME], {
            "b": "bucket",
            "o": "key1/key2",
            "v": "SomeVersionNumber"
        })


    @patch("awscli.customizations.cloudformation.artifact_exporter.Template")
    def test_export_cloudformation_stack(self, TemplateMock):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)

        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        exported_template_dict = {"foo": "bar"}
        result_s3_url = "s3://hello/world"

        template_instance_mock = Mock()
        TemplateMock.return_value = template_instance_mock
        template_instance_mock.export.return_value = exported_template_dict

        self.s3_uploader_mock.upload_with_dedup.return_value = result_s3_url

        with tempfile.NamedTemporaryFile() as handle:
            template_path = handle.name
            resource_dict = {property_name: template_path}
            parent_dir = tempfile.gettempdir()

            stack_resource.export(resource_id, resource_dict, parent_dir)

            self.assertEquals(resource_dict[property_name], result_s3_url)

            TemplateMock.assert_called_once_with(template_path, parent_dir, self.s3_uploader_mock)
            template_instance_mock.export.assert_called_once_with()
            self.s3_uploader_mock.upload_with_dedup.assert_called_once_with(mock.ANY, "template")

    def test_export_cloudformation_stack_no_upload_path_is_s3url(self):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "s3://hello/world"
        resource_dict = {property_name: s3_url}

        # Case 1: Path is already S3 url
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict[property_name], s3_url)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_cloudformation_stack_no_upload_path_is_empty(self):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "s3://hello/world"
        resource_dict = {property_name: s3_url}

        # Case 2: Path is empty
        resource_dict = {}
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict, {})
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_cloudformation_stack_no_upload_path_not_file(self):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "s3://hello/world"

        # Case 3: Path is not a file
        with self.make_temp_dir() as dirname:
            resource_dict = {property_name: dirname}
            with self.assertRaises(exceptions.ExportFailedError):
                stack_resource.export(resource_id, resource_dict, "dir")
                self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.yaml_parse")
    def test_template_export(self, yaml_parse_mock):
        parent_dir = os.path.sep
        template_dir = os.path.join(parent_dir, 'foo', 'bar')
        template_path = os.path.join(template_dir, 'path')
        template_str = self.example_yaml_template()

        resource_type1_class = Mock()
        resource_type1_instance = Mock()
        resource_type1_class.return_value = resource_type1_instance
        resource_type2_class = Mock()
        resource_type2_instance = Mock()
        resource_type2_class.return_value = resource_type2_instance

        resources_to_export = {
            "resource_type1": resource_type1_class,
            "resource_type2": resource_type2_class
        }

        properties = {"foo": "bar"}
        template_dict = {
            "Resources": {
                "Resource1": {
                    "Type": "resource_type1",
                    "Properties": properties
                },
                "Resource2": {
                    "Type": "resource_type2",
                    "Properties": properties
                },
                "Resource3": {
                    "Type": "some-other-type",
                    "Properties": properties
                }
            }
        }

        open_mock = mock.mock_open()
        yaml_parse_mock.return_value = template_dict

        # Patch the file open method to return template string
        with patch(
                "awscli.customizations.cloudformation.artifact_exporter.open",
                open_mock(read_data=template_str)) as open_mock:

            template_exporter = Template(
                template_path, parent_dir, self.s3_uploader_mock,
                resources_to_export)
            exported_template = template_exporter.export()
            self.assertEquals(exported_template, template_dict)

            open_mock.assert_called_once_with(
                    make_abs_path(parent_dir, template_path), "r")

            self.assertEquals(1, yaml_parse_mock.call_count)

            resource_type1_class.assert_called_once_with(self.s3_uploader_mock)
            resource_type1_instance.export.assert_called_once_with(
                "Resource1", mock.ANY, template_dir)
            resource_type2_class.assert_called_once_with(self.s3_uploader_mock)
            resource_type2_instance.export.assert_called_once_with(
                "Resource2", mock.ANY, template_dir)

    def test_template_export_path_be_folder(self):

        template_path = "/path/foo"
        # Set parent_dir to be a non-existent folder
        with self.assertRaises(ValueError):
            Template(template_path, "somefolder", self.s3_uploader_mock)

        # Set parent_dir to be a real folder, but just a relative path
        with self.make_temp_dir() as dirname:
            with self.assertRaises(ValueError):
                Template(template_path, os.path.relpath(dirname), self.s3_uploader_mock)

    def test_make_zip(self):
        test_file_creator = FileCreator()
        test_file_creator.append_file('index.js',
                                      'exports handler = (event, context, callback) => {callback(null, event);}')

        dirname = test_file_creator.rootdir

        expected_files = set(['index.js'])

        random_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
        outfile = os.path.join(tempfile.gettempdir(), random_name)

        zipfile_name = None
        try:
            zipfile_name = make_zip(outfile, dirname)

            test_zip_file = zipfile.ZipFile(zipfile_name, "r")
            with closing(test_zip_file) as zf:
                files_in_zip = set()
                for info in zf.infolist():
                    files_in_zip.add(info.filename)

                self.assertEquals(files_in_zip, expected_files)

        finally:
            if zipfile_name:
                os.remove(zipfile_name)
            test_file_creator.remove_all()

    @contextmanager
    def make_temp_dir(self):
        filename = tempfile.mkdtemp()
        try:
            yield filename
        finally:
            if filename:
                os.rmdir(filename)

    def example_yaml_template(self):
        return """
        AWSTemplateFormatVersion: '2010-09-09'
        Description: Simple CRUD webservice. State is stored in a SimpleTable (DynamoDB) resource.
        Resources:
        MyFunction:
          Type: AWS::Lambda::Function
          Properties:
            Code: ./handler
            Handler: index.get
            Role:
              Fn::GetAtt:
              - MyFunctionRole
              - Arn
            Timeout: 20
            Runtime: nodejs4.3
        """
