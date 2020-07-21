# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class BaseRekognitionTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseRekognitionTest, self).setUp()
        self.files = FileCreator()
        self.temp_file = self.files.create_file(
            'foo', 'mycontents')
        with open(self.temp_file, 'rb') as f:
            self.temp_file_bytes = f.read()

    def tearDown(self):
        super(BaseRekognitionTest, self).tearDown()
        self.files.remove_all()


class TestCompareFaces(BaseRekognitionTest):

    prefix = 'rekognition compare-faces'

    def test_image_file_does_populate_bytes_param(self):
        second_temp_file = self.files.create_file('bar', 'othercontents')
        second_file_bytes = open(second_temp_file, 'rb').read()

        cmdline = self.prefix
        cmdline += ' --source-image-bytes fileb://%s' % self.temp_file
        cmdline += ' --target-image-bytes fileb://%s' % second_temp_file
        result = {
            'SourceImage': {'Bytes': self.temp_file_bytes},
            'TargetImage': {'Bytes': second_file_bytes},
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --source-image Bytes=foo'
        cmdline += ' --target-image Bytes=bar'
        result = {
            'SourceImage': {'Bytes': 'foo'},
            'TargetImage': {'Bytes': 'bar'},
        }
        self.assert_params_for_cmd(cmdline, result)


class TestDetectFaces(BaseRekognitionTest):

    prefix = 'rekognition detect-faces'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --image Bytes=foobar'
        result = {
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestDetectLabels(BaseRekognitionTest):

    prefix = 'rekognition detect-labels'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --image Bytes=foobar'
        result = {
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestDetectModerationLabels(BaseRekognitionTest):

    prefix = 'rekognition detect-moderation-labels'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --image Bytes=foobar'
        result = {
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestDetectText(BaseRekognitionTest):

    prefix = 'rekognition detect-text'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --image Bytes=foobar'
        result = {
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestIndexFaces(BaseRekognitionTest):

    prefix = 'rekognition index-faces'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --collection-id foobar'
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'CollectionId': 'foobar',
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --collection-id foobar'
        cmdline += ' --image Bytes=foobar'
        result = {
            'CollectionId': 'foobar',
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestRecognizeCelebrities(BaseRekognitionTest):

    prefix = 'rekognition recognize-celebrities'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --image Bytes=foobar'
        result = {
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)


class TestSearchFacesByImage(BaseRekognitionTest):

    prefix = 'rekognition search-faces-by-image'

    def test_image_file_does_populate_bytes_param(self):
        cmdline = self.prefix
        cmdline += ' --collection-id foobar'
        cmdline += ' --image-bytes fileb://%s' % self.temp_file
        result = {
            'CollectionId': 'foobar',
            'Image': {'Bytes': self.temp_file_bytes}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_image_bytes_still_works(self):
        cmdline = self.prefix
        cmdline += ' --collection-id foobar'
        cmdline += ' --image Bytes=foobar'
        result = {
            'CollectionId': 'foobar',
            'Image': {'Bytes': 'foobar'}
        }
        self.assert_params_for_cmd(cmdline, result)
