# Copyright (c) 2015 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import json

import mock

from awscli.testutils import unittest, FileCreator
from awscli.topictags import TopicTagDB


class TestTopicTagDB(unittest.TestCase):
    def setUp(self):
        self.topic_tag_db = TopicTagDB()
        self.file_creator = FileCreator()

    def tearDown(self):
        self.file_creator.remove_all()


class TestTopicTagDBGeneral(TestTopicTagDB):
    def test_valid_tags(self):
        self.assertCountEqual(
            self.topic_tag_db.valid_tags,
            ['title', 'description', 'category', 'related command',
             'related topic']
        )

    def test_topic_dir(self):
        self.topic_tag_db = TopicTagDB(topic_dir='foo')
        self.assertEqual(self.topic_tag_db.topic_dir, 'foo')
        self.topic_tag_db.topic_dir = 'bar'
        self.assertEqual(self.topic_tag_db.topic_dir, 'bar')

    def test_index_file(self):
        self.topic_tag_db = TopicTagDB(index_file='foo')
        self.assertEqual(self.topic_tag_db.index_file, 'foo')
        self.topic_tag_db.index_file = 'bar'
        self.assertEqual(self.topic_tag_db.index_file, 'bar')

    def test_get_all_topic_names(self):
        tag_dict = {
            'topic-name-1': {
                'title': ['My First Topic Title'],
            },
            'topic-name-2': {
                'title': ['My Second Topic Title'],
            }
        }
        reference_topic_list = ['topic-name-1', 'topic-name-2']
        self.topic_tag_db = TopicTagDB(tag_dict)
        self.assertCountEqual(self.topic_tag_db.get_all_topic_names(),
                              reference_topic_list)

    def test_get_all_topic_source_files(self):
        source_files = []
        topic_dir = self.file_creator.rootdir
        self.topic_tag_db = TopicTagDB(topic_dir=topic_dir)
        for i in range(5):
            topic_name = 'topic-name-' + str(i)
            source_files.append(self.file_creator.create_file(topic_name, ''))

        self.assertCountEqual(
            self.topic_tag_db.get_all_topic_src_files(),
            source_files
        )

    def test_get_all_topic_source_files_ignore_index(self):
        topic_filename = 'mytopic'
        index_filename = 'topic-tags.json'
        source_files = []
        source_files.append(self.file_creator.create_file(topic_filename, ''))
        index_file = self.file_creator.create_file(index_filename, '')
        topic_dir = self.file_creator.rootdir
        self.topic_tag_db = TopicTagDB(index_file=index_file,
                                       topic_dir=topic_dir)
        self.assertCountEqual(
            self.topic_tag_db.get_all_topic_src_files(),
            source_files
        )

    def test_get_all_topic_source_files_ignore_hidden(self):
        topic_filename = 'mytopic'
        hidden_filename = '.' + topic_filename
        source_files = []
        source_files.append(self.file_creator.create_file(topic_filename, ''))
        self.file_creator.create_file(hidden_filename, '')
        topic_dir = self.file_creator.rootdir
        self.topic_tag_db = TopicTagDB(topic_dir=topic_dir)
        self.assertCountEqual(
            self.topic_tag_db.get_all_topic_src_files(),
            source_files
        )

    def test_get_tag_value_all_tags(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'title': ['My First Topic Title'],
                'description': ['This describes my first topic'],
                'category': ['General Topics'],
                'related command': ['aws s3'],
                'related topic': ['topic-name-2']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)

        # Check the title get tag value
        value = self.topic_tag_db.get_tag_value(topic_name, 'title')
        self.assertEqual(value, ['My First Topic Title'])

        # Check the description get tag value
        value = self.topic_tag_db.get_tag_value(topic_name, 'description')
        self.assertEqual(value, ['This describes my first topic'])

        # Check the category get tag value
        value = self.topic_tag_db.get_tag_value(topic_name, 'category')
        self.assertEqual(value, ['General Topics'])

        # Check the related command get tag value
        value = self.topic_tag_db.get_tag_value(topic_name,
                                                'related command')
        self.assertEqual(value, ['aws s3'])

        # Check the related topic get tag value
        value = self.topic_tag_db.get_tag_value(topic_name, 'related topic')
        self.assertEqual(value, ['topic-name-2'])

    def test_get_tag_multi_value(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'related topic': ['foo', 'bar']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        # Check the related topic get tag value
        value = self.topic_tag_db.get_tag_value(topic_name, 'related topic')
        self.assertEqual(value, ['foo', 'bar'])

    def test_get_tag_topic_no_exists(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'related topic': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        value = self.topic_tag_db.get_tag_value('no-exist', 'related topic')
        self.assertEqual(value, None)

    def test_get_tag_no_exist_tag(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'related topic': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        value = self.topic_tag_db.get_tag_value(topic_name, ':foo:')
        self.assertEqual(value, None)

    def test_get_tag_no_exist_use_default(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'related topic': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        value = self.topic_tag_db.get_tag_value('no-exist', ':foo:', [])
        self.assertEqual(value, [])

    def test_get_tag_single_value(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'title': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        value = self.topic_tag_db.get_tag_single_value('topic-name-1', 'title')
        self.assertEqual(value, 'foo')

    def test_get_tag_single_value_exception(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'title': ['foo', 'bar']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        with self.assertRaises(ValueError):
            self.topic_tag_db.get_tag_single_value('topic-name-1', 'title')

    def test_get_tag_single_value_no_exists(self):
        topic_name = 'topic-name-1'
        tag_dict = {
            topic_name: {
                'title': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        value = self.topic_tag_db.get_tag_single_value(
            'topic-name-1', ':title:')
        self.assertEqual(value, None)

    def test_load_and_save_json_index(self):
        tag_dict = {
            'topic-name-1': {
                'title': ['My First Topic Title'],
                'description': ['This describes my first topic'],
                'category': ['General Topics', 'S3'],
                'related command': ['aws s3'],
                'related topic': ['topic-name-2']
            },
            'topic-name-2': {
                'title': ['My Second Topic Title'],
                'description': ['This describes my second topic'],
                'category': ['General Topics'],
                'related topic': ['topic-name-1']
            }
        }

        json_index = self.file_creator.create_file('index.json', '')

        # Create a JSON index to be loaded.
        tag_json = json.dumps(tag_dict, indent=4, sort_keys=True)
        with open(json_index, 'w') as f:
            f.write(tag_json)

        # Load the JSON index.
        self.topic_tag_db = TopicTagDB(index_file=json_index)
        self.topic_tag_db.load_json_index()

        # Write the loaded json to disk and ensure it is as expected.
        saved_json_index = self.file_creator.create_file('index2.json', '')
        self.topic_tag_db.index_file = saved_json_index

        self.topic_tag_db.save_to_json_index()
        with open(saved_json_index, 'r') as f:
            self.assertEqual(f.read(), tag_json)


class TestTopicTagDBQuery(TestTopicTagDB):
    def test_query_all_tags_single_topic(self):
        tag_dict = {
            'topic-name-1': {
                'title': ['My First Topic Title'],
                'description': ['This describes my first topic'],
                'category': ['General Topics'],
                'related command': ['aws s3'],
                'related topic': ['topic-name-2']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)

        # Check title query
        query_dict = self.topic_tag_db.query('title')
        self.assertEqual(query_dict,
                         {'My First Topic Title': ['topic-name-1']})

        # Check the description query
        query_dict = self.topic_tag_db.query('description')
        self.assertEqual(query_dict,
                         {'This describes my first topic': ['topic-name-1']})

        # Check the category query
        query_dict = self.topic_tag_db.query('category')
        self.assertEqual(query_dict,
                         {'General Topics': ['topic-name-1']})

        # Check the related command query
        query_dict = self.topic_tag_db.query('related command')
        self.assertEqual(query_dict,
                         {'aws s3': ['topic-name-1']})

        # Check the description query
        query_dict = self.topic_tag_db.query('related topic')
        self.assertEqual(query_dict,
                         {'topic-name-2': ['topic-name-1']})

    def test_query_tag_multi_values(self):
        tag_dict = {
            'topic-name-1': {
                'related topic': ['foo', 'bar']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('related topic')
        self.assertEqual(query_dict,
                         {'foo': ['topic-name-1'], 'bar': ['topic-name-1']})

    def test_query_tag_multi_values(self):
        tag_dict = {
            'topic-name-1': {
                'related topic': ['foo', 'bar']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('related topic')
        self.assertEqual(query_dict,
                         {'foo': ['topic-name-1'], 'bar': ['topic-name-1']})

    def test_query_multiple_topics(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo']
            },
            'topic-name-2': {
                'category': ['bar']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('category')
        self.assertEqual(query_dict,
                         {'foo': ['topic-name-1'], 'bar': ['topic-name-2']})

    def test_query_multiple_topics_with_multi_values(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo', 'bar']
            },
            'topic-name-2': {
                'category': ['baz', 'biz']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('category')
        self.assertEqual(query_dict,
                         {'foo': ['topic-name-1'], 'bar': ['topic-name-1'],
                          'baz': ['topic-name-2'], 'biz': ['topic-name-2']})

    def test_query_multiple_topics_with_overlap_values(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo', 'bar']
            },
            'topic-name-2': {
                'category': ['bar', 'biz']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('category')
        self.assertCountEqual(
            query_dict, {'foo': ['topic-name-1'], 'biz': ['topic-name-2'],
                         'bar': ['topic-name-1', 'topic-name-2']})

    def test_query_with_limit_single_value(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo', 'bar']
            },
            'topic-name-2': {
                'category': ['bar', 'biz']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('category', ['bar'])
        self.assertCountEqual(query_dict,
                              {'bar': ['topic-name-1', 'topic-name-2']})

    def test_query_with_limit_multi_value(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo', 'bar']
            },
            'topic-name-2': {
                'category': ['bar', 'biz']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query('category', ['foo', 'bar'])
        self.assertCountEqual(query_dict,
                              {'foo': ['topic-name-1'],
                               'bar': ['topic-name-1', 'topic-name-2']})

    def topic_query_with_non_existant_tag(self):
        tag_dict = {
            'topic-name-1': {
                'category': ['foo']
            }
        }
        self.topic_tag_db = TopicTagDB(tag_dict)
        query_dict = self.topic_tag_db.query(':bar:')
        self.assertEqual(query_dict, {})


class TestTopicDBScan(TestTopicTagDB):
    def create_topic_src_file(self, topic_name, tags):
        """Create a topic source file from a list of tags and topic name"""
        content = '\n'.join(tags)
        topic_name = topic_name + '.rst'
        topic_filepath = self.file_creator.create_file(topic_name, content)
        return topic_filepath

    def assert_json_index(self, file_paths, reference_tag_dict):
        """Asserts the scanned tags by checking the saved JSON index"""
        json_index = self.file_creator.create_file('index.json', '')
        self.topic_tag_db = TopicTagDB(index_file=json_index)
        self.topic_tag_db.scan(file_paths)
        self.topic_tag_db.save_to_json_index()
        with open(json_index, 'r') as f:
            saved_index = json.loads(f.read())
            self.assertEqual(saved_index, reference_tag_dict)

    def test_scan_all_valid_tags(self):
        tags = [
            ':description: This is a description',
            ':title: Title',
            ':category: Foo',
            ':related topic: Bar',
            ':related command: ec2'
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'description': ['This is a description'],
                'title': ['Title'],
                'category': ['Foo'],
                'related topic': ['Bar'],
                'related command': ['ec2']
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_invalid_tag(self):
        tags = [
            ':description: This is a description',
            ':title: Title',
            ':category: Foo',
            ':related_topic: Bar',
        ]
        topic_name = 'my-topic'

        topic_filepath = self.create_topic_src_file(topic_name, tags)
        with self.assertRaises(ValueError):
            self.topic_tag_db.scan([topic_filepath])

    def test_scan_no_tags(self):
        tags = []
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {}
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_multi_values(self):
        tags = [
            ':category: Foo, Bar',
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'category': ['Foo', 'Bar'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_single_and_multi_values(self):
        tags = [
            ':title: Title',
            ':category: Foo, Bar',
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'title': ['Title'],
                'category': ['Foo', 'Bar'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_multi_duplicate_values(self):
        tags = [
            ':category: Foo, Foo, Bar'
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'category': ['Foo', 'Bar'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_multi_values_extra_space(self):
        tags = [
            ':category:    Foo, Bar   ',
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'category': ['Foo', 'Bar'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_multi_values_no_space(self):
        tags = [
            ':category: Foo,Bar',
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'category': ['Foo', 'Bar'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_tags_with_multi_preserve_space(self):
        tags = [
            ':category: Foo Bar, Baz',
        ]
        topic_name = 'my-topic'

        reference_tag_dict = {
            topic_name: {
                'category': ['Foo Bar', 'Baz'],
            }
        }
        topic_filepath = self.create_topic_src_file(topic_name, tags)
        self.assert_json_index([topic_filepath], reference_tag_dict)

    def test_scan_multiple_files(self):
        topic_base = 'my-topic'
        reference_tag_dict = {}
        topic_files = []
        for i in range(5):
            topic_name = topic_base + '-' + str(i)
            tags = [
                ':description: This is about %s' % topic_name,
                ':title: Title',
                ':category: Foo',
                ':related topic: Bar',
                ':related command: ec2'
            ]

            reference_tag_dict[topic_name] = {
                'description': ['This is about %s' % topic_name],
                'title': ['Title'],
                'category': ['Foo'],
                'related topic': ['Bar'],
                'related command': ['ec2']
            }
            topic_files.append(self.create_topic_src_file(topic_name, tags))
        self.assert_json_index(topic_files, reference_tag_dict)
