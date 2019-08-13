import mock
import botocore.session
import tempfile
import os
import string
import random
import zipfile

from nose.tools import assert_true, assert_false, assert_equal
from contextlib import contextmanager, closing
from mock import patch, Mock, MagicMock
from botocore.stub import Stubber
from awscli.testutils import unittest, FileCreator
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.artifact_exporter \
    import is_s3_url, parse_s3_url, is_local_file, is_local_folder, \
    upload_local_artifacts, zip_folder, make_abs_path, make_zip, \
    Template, Resource, ResourceWithS3UrlDict, ServerlessApiResource, \
    ServerlessFunctionResource, GraphQLSchemaResource, \
    LambdaFunctionResource, ApiGatewayRestApiResource, \
    ElasticBeanstalkApplicationVersion, CloudFormationStackResource, \
    ServerlessApplicationResource, LambdaLayerVersionResource, \
    copy_to_temp_dir, include_transform_export_handler, GLOBAL_EXPORT_DICT, \
    ServerlessLayerVersionResource, ServerlessRepoApplicationLicense, \
    ServerlessRepoApplicationReadme, \
    AppSyncResolverRequestTemplateResource, \
    AppSyncResolverResponseTemplateResource, \
    AppSyncFunctionConfigurationRequestTemplateResource, \
    AppSyncFunctionConfigurationResponseTemplateResource, \
    GlueJobCommandScriptLocationResource


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
            "class": GraphQLSchemaResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": AppSyncResolverRequestTemplateResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": AppSyncResolverResponseTemplateResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": AppSyncFunctionConfigurationRequestTemplateResource,
            "expected_result": uploaded_s3_url
        },

        {
            "class": AppSyncFunctionConfigurationResponseTemplateResource,
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
        {
            "class": LambdaLayerVersionResource,
            "expected_result": {
                "S3Bucket": "foo", "S3Key": "bar", "S3ObjectVersion": "baz"
            }
        },
        {
            "class": ServerlessLayerVersionResource,
            "expected_result": uploaded_s3_url
        },
        {
            "class": ServerlessRepoApplicationReadme,
            "expected_result": uploaded_s3_url
        },
        {
            "class": ServerlessRepoApplicationLicense,
            "expected_result": uploaded_s3_url
        },
        {
            "class": ServerlessRepoApplicationLicense,
            "expected_result": uploaded_s3_url
        },
        {
            "class": GlueJobCommandScriptLocationResource,
            "expected_result": {
                    "ScriptLocation": uploaded_s3_url
            }
        }
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

    if '.' in test_class.PROPERTY_NAME:
        reversed_property_names = test_class.PROPERTY_NAME.split('.')
        reversed_property_names.reverse()
        property_dict = {
            reversed_property_names[0]: "foo"
        }
        for sub_property_name in reversed_property_names[1:]:
            property_dict = {
                sub_property_name: property_dict
            }
        resource_dict = property_dict
    else:
        resource_dict = {
            test_class.PROPERTY_NAME: "foo"
        }
    parent_dir = "dir"

    upload_local_artifacts_mock.return_value = uploaded_s3_url

    resource_obj = test_class(s3_uploader_mock)

    resource_obj.export(resource_id, resource_dict, parent_dir)

    upload_local_artifacts_mock.assert_called_once_with(resource_id,
                                                        resource_dict,
                                                        test_class.PROPERTY_NAME,
                                                        parent_dir,
                                                        s3_uploader_mock)
    if '.' in test_class.PROPERTY_NAME:
        top_level_property_name = test_class.PROPERTY_NAME.split('.')[0]
        result = resource_dict[top_level_property_name]
    else:
        result = resource_dict[test_class.PROPERTY_NAME]
    assert_equal(result, expected_result)


class TestArtifactExporter(unittest.TestCase):

    def setUp(self):
        self.s3_uploader_mock = Mock()
        self.s3_uploader_mock.s3.meta.endpoint_url = "https://s3.some-valid-region.amazonaws.com"

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

    @patch("shutil.rmtree")
    @patch("zipfile.is_zipfile")
    @patch("awscli.customizations.cloudformation.artifact_exporter.copy_to_temp_dir")
    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_resource_with_force_zip_on_regular_file(self, is_local_file_mock, \
        zip_and_upload_mock, copy_to_temp_dir_mock, is_zipfile_mock, rmtree_mock):
        # Property value is a path to file and FORCE_ZIP is True

        class MockResource(Resource):
            PROPERTY_NAME = "foo"
            FORCE_ZIP = True

        resource = MockResource(self.s3_uploader_mock)

        resource_id = "id"
        resource_dict = {}
        original_path = "/path/to/file"
        resource_dict[resource.PROPERTY_NAME] = original_path
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        zip_and_upload_mock.return_value = s3_url
        is_local_file_mock.return_value = True

        with self.make_temp_dir() as tmp_dir:

            copy_to_temp_dir_mock.return_value = tmp_dir

            # This is not a zip file
            is_zipfile_mock.return_value = False

            resource.export(resource_id, resource_dict, parent_dir)

            zip_and_upload_mock.assert_called_once_with(tmp_dir, mock.ANY)
            rmtree_mock.assert_called_once_with(tmp_dir)
            is_zipfile_mock.assert_called_once_with(original_path)
            assert_equal(resource_dict[resource.PROPERTY_NAME], s3_url)

    @patch("shutil.rmtree")
    @patch("zipfile.is_zipfile")
    @patch("awscli.customizations.cloudformation.artifact_exporter.copy_to_temp_dir")
    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_resource_with_force_zip_on_zip_file(self, is_local_file_mock, \
        zip_and_upload_mock, copy_to_temp_dir_mock, is_zipfile_mock, rmtree_mock):
        # Property value is a path to zip file and FORCE_ZIP is True
        # We should *not* re-zip an existing zip

        class MockResource(Resource):
            PROPERTY_NAME = "foo"
            FORCE_ZIP = True

        resource = MockResource(self.s3_uploader_mock)

        resource_id = "id"
        resource_dict = {}
        original_path = "/path/to/zip_file"
        resource_dict[resource.PROPERTY_NAME] = original_path
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        # When the file is actually a zip-file, no additional zipping has to happen
        is_zipfile_mock.return_value = True
        is_local_file_mock.return_value = True
        zip_and_upload_mock.return_value = s3_url
        self.s3_uploader_mock.upload_with_dedup.return_value = s3_url

        resource.export(resource_id, resource_dict, parent_dir)

        copy_to_temp_dir_mock.assert_not_called()
        zip_and_upload_mock.assert_not_called()
        rmtree_mock.assert_not_called()
        is_zipfile_mock.assert_called_once_with(original_path)
        assert_equal(resource_dict[resource.PROPERTY_NAME], s3_url)

    @patch("shutil.rmtree")
    @patch("zipfile.is_zipfile")
    @patch("awscli.customizations.cloudformation.artifact_exporter.copy_to_temp_dir")
    @patch("awscli.customizations.cloudformation.artifact_exporter.zip_and_upload")
    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_resource_without_force_zip(self, is_local_file_mock, \
        zip_and_upload_mock, copy_to_temp_dir_mock, is_zipfile_mock, rmtree_mock):

        class MockResourceNoForceZip(Resource):
            PROPERTY_NAME = "foo"

        resource = MockResourceNoForceZip(self.s3_uploader_mock)

        resource_id = "id"
        resource_dict = {}
        original_path = "/path/to/file"
        resource_dict[resource.PROPERTY_NAME] = original_path
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        # This is not a zip file, but a valid local file. Since FORCE_ZIP is NOT set, this will not be zipped
        is_zipfile_mock.return_value = False
        is_local_file_mock.return_value = True
        zip_and_upload_mock.return_value = s3_url
        self.s3_uploader_mock.upload_with_dedup.return_value = s3_url

        resource.export(resource_id, resource_dict, parent_dir)

        copy_to_temp_dir_mock.assert_not_called()
        zip_and_upload_mock.assert_not_called()
        rmtree_mock.assert_not_called()
        is_zipfile_mock.assert_called_once_with(original_path)
        assert_equal(resource_dict[resource.PROPERTY_NAME], s3_url)

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
    def test_resource_has_package_null_property_to_false(self, upload_local_artifacts_mock):
        # Should not upload anything if PACKAGE_NULL_PROPERTY is set to False

        class MockResource(Resource):
            PROPERTY_NAME = "foo"
            PACKAGE_NULL_PROPERTY = False

        resource = MockResource(self.s3_uploader_mock)
        resource_id = "id"
        resource_dict = {}
        parent_dir = "dir"
        s3_url = "s3://foo/bar"

        upload_local_artifacts_mock.return_value = s3_url

        resource.export(resource_id, resource_dict, parent_dir)

        upload_local_artifacts_mock.assert_not_called()
        self.assertNotIn(resource.PROPERTY_NAME, resource_dict)

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
        result_path_style_s3_url = "http://s3.amazonws.com/hello/world"

        template_instance_mock = Mock()
        TemplateMock.return_value = template_instance_mock
        template_instance_mock.export.return_value = exported_template_dict

        self.s3_uploader_mock.upload_with_dedup.return_value = result_s3_url
        self.s3_uploader_mock.to_path_style_s3_url.return_value = result_path_style_s3_url

        with tempfile.NamedTemporaryFile() as handle:
            template_path = handle.name
            resource_dict = {property_name: template_path}
            parent_dir = tempfile.gettempdir()

            stack_resource.export(resource_id, resource_dict, parent_dir)

            self.assertEquals(resource_dict[property_name], result_path_style_s3_url)

            TemplateMock.assert_called_once_with(template_path, parent_dir, self.s3_uploader_mock)
            template_instance_mock.export.assert_called_once_with()
            self.s3_uploader_mock.upload_with_dedup.assert_called_once_with(mock.ANY, "template")
            self.s3_uploader_mock.to_path_style_s3_url.assert_called_once_with("world", None)

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

    def test_export_cloudformation_stack_no_upload_path_is_httpsurl(self):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "https://s3.amazonaws.com/hello/world"
        resource_dict = {property_name: s3_url}

        # Case 1: Path is already S3 url
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict[property_name], s3_url)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_cloudformation_stack_no_upload_path_is_s3_region_httpsurl(self):
        stack_resource = CloudFormationStackResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME

        s3_url = "https://s3.some-valid-region.amazonaws.com/hello/world"
        resource_dict = {property_name: s3_url}

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

    @patch("awscli.customizations.cloudformation.artifact_exporter.Template")
    def test_export_serverless_application(self, TemplateMock):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)

        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        exported_template_dict = {"foo": "bar"}
        result_s3_url = "s3://hello/world"
        result_path_style_s3_url = "http://s3.amazonws.com/hello/world"

        template_instance_mock = Mock()
        TemplateMock.return_value = template_instance_mock
        template_instance_mock.export.return_value = exported_template_dict

        self.s3_uploader_mock.upload_with_dedup.return_value = result_s3_url
        self.s3_uploader_mock.to_path_style_s3_url.return_value = result_path_style_s3_url

        with tempfile.NamedTemporaryFile() as handle:
            template_path = handle.name
            resource_dict = {property_name: template_path}
            parent_dir = tempfile.gettempdir()

            stack_resource.export(resource_id, resource_dict, parent_dir)

            self.assertEquals(resource_dict[property_name], result_path_style_s3_url)

            TemplateMock.assert_called_once_with(template_path, parent_dir, self.s3_uploader_mock)
            template_instance_mock.export.assert_called_once_with()
            self.s3_uploader_mock.upload_with_dedup.assert_called_once_with(mock.ANY, "template")
            self.s3_uploader_mock.to_path_style_s3_url.assert_called_once_with("world", None)

    def test_export_serverless_application_no_upload_path_is_s3url(self):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "s3://hello/world"
        resource_dict = {property_name: s3_url}

        # Case 1: Path is already S3 url
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict[property_name], s3_url)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_serverless_application_no_upload_path_is_httpsurl(self):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME
        s3_url = "https://s3.amazonaws.com/hello/world"
        resource_dict = {property_name: s3_url}

        # Case 1: Path is already S3 url
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict[property_name], s3_url)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_serverless_application_no_upload_path_is_empty(self):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME

        # Case 2: Path is empty
        resource_dict = {}
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict, {})
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_serverless_application_no_upload_path_not_file(self):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME

        # Case 3: Path is not a file
        with self.make_temp_dir() as dirname:
            resource_dict = {property_name: dirname}
            with self.assertRaises(exceptions.ExportFailedError):
                stack_resource.export(resource_id, resource_dict, "dir")
                self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    def test_export_serverless_application_no_upload_path_is_dictionary(self):
        stack_resource = ServerlessApplicationResource(self.s3_uploader_mock)
        resource_id = "id"
        property_name = stack_resource.PROPERTY_NAME

        # Case 4: Path is dictionary
        location = {"ApplicationId": "id", "SemanticVersion": "1.0.1"}
        resource_dict = {property_name: location}
        stack_resource.export(resource_id, resource_dict, "dir")
        self.assertEquals(resource_dict[property_name], location)
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.yaml_parse")
    def test_template_export_metadata(self, yaml_parse_mock):
        parent_dir = os.path.sep
        template_dir = os.path.join(parent_dir, 'foo', 'bar')
        template_path = os.path.join(template_dir, 'path')
        template_str = self.example_yaml_template()

        metadata_type1_class = Mock()
        metadata_type1_class.RESOURCE_TYPE = "metadata_type1"
        metadata_type1_class.PROPERTY_NAME = "property_1"
        metadata_type1_instance = Mock()
        metadata_type1_class.return_value = metadata_type1_instance

        metadata_type2_class = Mock()
        metadata_type2_class.RESOURCE_TYPE = "metadata_type2"
        metadata_type2_class.PROPERTY_NAME = "property_2"
        metadata_type2_instance = Mock()
        metadata_type2_class.return_value = metadata_type2_instance

        metadata_to_export = [
            metadata_type1_class,
            metadata_type2_class
        ]

        template_dict = {
            "Metadata": {
                "metadata_type1": {
                    "property_1": "abc"
                },
                "metadata_type2": {
                    "property_2": "def"
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
                metadata_to_export=metadata_to_export)
            exported_template = template_exporter.export()
            self.assertEquals(exported_template, template_dict)

            open_mock.assert_called_once_with(
                    make_abs_path(parent_dir, template_path), "r")

            self.assertEquals(1, yaml_parse_mock.call_count)

            metadata_type1_class.assert_called_once_with(self.s3_uploader_mock)
            metadata_type1_instance.export.assert_called_once_with(
                "metadata_type1", mock.ANY, template_dir)
            metadata_type2_class.assert_called_once_with(self.s3_uploader_mock)
            metadata_type2_instance.export.assert_called_once_with(
                "metadata_type2", mock.ANY, template_dir)

    @patch("awscli.customizations.cloudformation.artifact_exporter.yaml_parse")
    def test_template_export(self, yaml_parse_mock):
        parent_dir = os.path.sep
        template_dir = os.path.join(parent_dir, 'foo', 'bar')
        template_path = os.path.join(template_dir, 'path')
        template_str = self.example_yaml_template()

        resource_type1_class = Mock()
        resource_type1_class.RESOURCE_TYPE = "resource_type1"
        resource_type1_instance = Mock()
        resource_type1_class.return_value = resource_type1_instance
        resource_type2_class = Mock()
        resource_type2_class.RESOURCE_TYPE = "resource_type2"
        resource_type2_instance = Mock()
        resource_type2_class.return_value = resource_type2_instance

        resources_to_export = [
            resource_type1_class,
            resource_type2_class
        ]

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

    @patch("awscli.customizations.cloudformation.artifact_exporter.yaml_parse")
    def test_template_global_export(self, yaml_parse_mock):
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
        properties1 = {"foo": "bar", "Fn::Transform": {"Name": "AWS::Include", "Parameters": {"Location": "foo.yaml"}}}
        properties2 = {"foo": "bar", "Fn::Transform": {"Name": "AWS::OtherTransform"}}
        properties_in_list = {"Fn::Transform": {"Name": "AWS::Include", "Parameters": {"Location": "bar.yaml"}}}
        template_dict = {
            "Resources": {
                "Resource1": {
                    "Type": "resource_type1",
                    "Properties": properties1
                },
                "Resource2": {
                    "Type": "resource_type2",
                    "Properties": properties2,
                }
            },
            "List": ["foo", properties_in_list]
        }
        open_mock = mock.mock_open()
        include_transform_export_handler_mock = Mock()
        include_transform_export_handler_mock.return_value = {"Name": "AWS::Include", "Parameters": {"Location": "s3://foo"}}
        yaml_parse_mock.return_value = template_dict

        with patch(
                "awscli.customizations.cloudformation.artifact_exporter.open",
                open_mock(read_data=template_str)) as open_mock:
            with patch.dict(GLOBAL_EXPORT_DICT, {"Fn::Transform": include_transform_export_handler_mock}):
                template_exporter = Template(
                    template_path, parent_dir, self.s3_uploader_mock,
                    resources_to_export)

                exported_template = template_exporter.export_global_artifacts(template_exporter.template_dict)

                first_call_args, kwargs = include_transform_export_handler_mock.call_args_list[0]
                second_call_args, kwargs = include_transform_export_handler_mock.call_args_list[1]
                third_call_args, kwargs = include_transform_export_handler_mock.call_args_list[2]
                call_args = [first_call_args[0], second_call_args[0], third_call_args[0]]
                self.assertTrue({"Name": "AWS::Include", "Parameters": {"Location": "foo.yaml"}} in call_args)
                self.assertTrue({"Name": "AWS::OtherTransform"} in call_args)
                self.assertTrue({"Name": "AWS::Include", "Parameters": {"Location": "bar.yaml"}} in call_args)
                self.assertTrue(template_dir in first_call_args)
                self.assertTrue(template_dir in second_call_args)
                self.assertTrue(template_dir in third_call_args)
                self.assertEquals(include_transform_export_handler_mock.call_count, 3)
                #new s3 url is added to include location
                self.assertEquals(exported_template["Resources"]["Resource1"]["Properties"]["Fn::Transform"], {"Name": "AWS::Include", "Parameters": {"Location": "s3://foo"}})
                self.assertEquals(exported_template["List"][1]["Fn::Transform"], {"Name": "AWS::Include", "Parameters": {"Location": "s3://foo"}})

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_with_relative_file_path(self, is_local_file_mock):
        #exports transform
        parent_dir = os.path.abspath("someroot")
        self.s3_uploader_mock.upload_with_dedup.return_value = "s3://foo"
        is_local_file_mock.return_value = True
        abs_file_path = os.path.join(parent_dir, "foo.yaml")

        handler_output = include_transform_export_handler({"Name": "AWS::Include", "Parameters": {"Location": "foo.yaml"}}, self.s3_uploader_mock, parent_dir)
        self.s3_uploader_mock.upload_with_dedup.assert_called_once_with(abs_file_path)
        is_local_file_mock.assert_called_with(abs_file_path)
        self.assertEquals(handler_output, {'Name': 'AWS::Include', 'Parameters': {'Location': 's3://foo'}})

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_with_absolute_file_path(self, is_local_file_mock):
        #exports transform
        parent_dir = os.path.abspath("someroot")
        self.s3_uploader_mock.upload_with_dedup.return_value = "s3://foo"
        is_local_file_mock.return_value = True
        abs_file_path = os.path.abspath(os.path.join("my", "file.yaml"))

        handler_output = include_transform_export_handler({"Name": "AWS::Include", "Parameters": {"Location": abs_file_path}}, self.s3_uploader_mock, parent_dir)
        self.s3_uploader_mock.upload_with_dedup.assert_called_once_with(abs_file_path)
        is_local_file_mock.assert_called_with(abs_file_path)
        self.assertEquals(handler_output, {'Name': 'AWS::Include', 'Parameters': {'Location': 's3://foo'}})

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_with_s3_uri(self, is_local_file_mock):

        handler_output = include_transform_export_handler({"Name": "AWS::Include", "Parameters": {"Location": "s3://bucket/foo.yaml"}}, self.s3_uploader_mock, "parent_dir")
        # Input is returned unmodified
        self.assertEquals(handler_output, {"Name": "AWS::Include", "Parameters": {"Location": "s3://bucket/foo.yaml"}})

        is_local_file_mock.assert_not_called()
        self.s3_uploader_mock.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_with_no_path(self, is_local_file_mock):

        handler_output = include_transform_export_handler({"Name": "AWS::Include", "Parameters": {"Location": ""}}, self.s3_uploader_mock, "parent_dir")
        # Input is returned unmodified
        self.assertEquals(handler_output, {"Name": "AWS::Include", "Parameters": {"Location": ""}})

        is_local_file_mock.assert_not_called()
        self.s3_uploader_mock.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_with_dict_value_for_location(self, is_local_file_mock):

        handler_output = include_transform_export_handler(
            {"Name": "AWS::Include", "Parameters": {"Location": {"Fn::Sub": "${S3Bucket}/file.txt"}}},
            self.s3_uploader_mock,
            "parent_dir")
        # Input is returned unmodified
        self.assertEquals(handler_output, {"Name": "AWS::Include", "Parameters": {"Location": {"Fn::Sub": "${S3Bucket}/file.txt"}}})

        is_local_file_mock.assert_not_called()
        self.s3_uploader_mock.assert_not_called()


    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_non_local_file(self, is_local_file_mock):
        #returns unchanged template dict if transform not a local file, and not a S3 URI
        is_local_file_mock.return_value = False

        with self.assertRaises(exceptions.InvalidLocalPathError):
            include_transform_export_handler({"Name": "AWS::Include", "Parameters": {"Location": "http://foo.yaml"}}, self.s3_uploader_mock, "parent_dir")
            is_local_file_mock.assert_called_with("http://foo.yaml")
            self.s3_uploader_mock.assert_not_called()

    @patch("awscli.customizations.cloudformation.artifact_exporter.is_local_file")
    def test_include_transform_export_handler_non_include_transform(self, is_local_file_mock):
        #ignores transform that is not aws::include
        handler_output = include_transform_export_handler({"Name": "AWS::OtherTransform", "Parameters": {"Location": "foo.yaml"}}, self.s3_uploader_mock, "parent_dir")
        self.s3_uploader_mock.upload_with_dedup.assert_not_called()
        self.assertEquals(handler_output, {"Name": "AWS::OtherTransform", "Parameters": {"Location": "foo.yaml"}})

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

    @patch("shutil.copyfile")
    @patch("tempfile.mkdtemp")
    def test_copy_to_temp_dir(self, mkdtemp_mock, copyfile_mock):
        temp_dir = "/tmp/foo/"
        filename = "test.js"
        mkdtemp_mock.return_value = temp_dir

        returned_dir = copy_to_temp_dir(filename)

        self.assertEqual(returned_dir, temp_dir)
        copyfile_mock.assert_called_once_with(filename, temp_dir + filename)

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
