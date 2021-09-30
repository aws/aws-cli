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
import os
import json
import docutils.core


class TopicTagDB(object):
    """This class acts like a database for the tags of all available topics.

    A tag is an element in a topic reStructured text file that contains
    information about a topic. Information can range from titles to even
    related CLI commands. Here are all of the currently supported tags:

    Tag                 Meaning                         Required?
    ---                 -------                         ---------
    :title:             The title of the topic          Yes
    :description:       Sentence description of topic   Yes
    :category:          Category topic falls under      Yes
    :related topic:     A related topic                 No
    :related command:   A related command               No

    To see examples of how to specify tags, look in the directory
    awscli/topics. Note that tags can have multiple values by delimiting
    values with commas. All tags must be on their own line in the file.

    This class can load a JSON index represeting all topics and their tags,
    scan all of the topics and store the values of their tags, retrieve the
    tag value for a particular topic, query for all the topics with a specific
    tag and/or value, and save the loaded data back out to a JSON index.

    The structure of the database can be viewed as a python dictionary:

    {'topic-name-1': {
        'title': ['My First Topic Title'],
        'description': ['This describes my first topic'],
        'category': ['General Topics', 'S3'],
        'related command': ['aws s3'],
        'related topic': ['topic-name-2']
     },
     'topic-name-2': { .....
    }

    The keys of the dictionary are the CLI command names of the topics. These
    names are based off the name of the reStructed text file that corresponds
    to the topic. The value of these keys are dictionaries of tags, where the
    tags are keys and their value is a list of values for that tag. Note
    that all tag values for a specific tag of a specific topic are unique.
    """

    VALID_TAGS = ['category', 'description', 'title', 'related topic',
                  'related command']

    # The default directory to look for topics.
    TOPIC_DIR = os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)), 'topics')

    # The default JSON index to load.
    JSON_INDEX = os.path.join(TOPIC_DIR, 'topic-tags.json')

    def __init__(self, tag_dictionary=None, index_file=JSON_INDEX,
                 topic_dir=TOPIC_DIR):
        """
        :param index_file: The path to a specific JSON index to load.
            If nothing is specified it will default to the default JSON
            index at ``JSON_INDEX``.

        :param topic_dir: The path to the directory where to retrieve
            the topic source files. Note that if you store your index
            in this directory, you must supply the full path to the json
            index to the ``file_index`` argument as it may not be ignored when
            listing topic source files. If nothing is specified it will
            default to the default directory at ``TOPIC_DIR``.
        """
        self._tag_dictionary = tag_dictionary
        if self._tag_dictionary is None:
            self._tag_dictionary = {}

        self._index_file = index_file
        self._topic_dir = topic_dir

    @property
    def index_file(self):
        return self._index_file

    @index_file.setter
    def index_file(self, value):
        self._index_file = value

    @property
    def topic_dir(self):
        return self._topic_dir

    @topic_dir.setter
    def topic_dir(self, value):
        self._topic_dir = value

    @property
    def valid_tags(self):
        return self.VALID_TAGS

    def load_json_index(self):
        """Loads a JSON file into the tag dictionary."""
        with open(self.index_file, 'r') as f:
            self._tag_dictionary = json.load(f)

    def save_to_json_index(self):
        """Writes the loaded data back out to the JSON index."""
        with open(self.index_file, 'w') as f:
            f.write(json.dumps(self._tag_dictionary, indent=4, sort_keys=True))

    def get_all_topic_names(self):
        """Retrieves all of the topic names of the loaded JSON index"""
        return list(self._tag_dictionary)

    def get_all_topic_src_files(self):
        """Retrieves the file paths of all the topics in directory"""
        topic_full_paths = []
        topic_names = os.listdir(self.topic_dir)
        for topic_name in topic_names:
            # Do not try to load hidden files.
            if not topic_name.startswith('.'):
                topic_full_path = os.path.join(self.topic_dir, topic_name)
                # Ignore the JSON Index as it is stored with topic files.
                if topic_full_path != self.index_file:
                    topic_full_paths.append(topic_full_path)
        return topic_full_paths

    def scan(self, topic_files):
        """Scan in the tags of a list of topics into memory.

        Note that if there are existing values in an entry in the database
        of tags, they will not be overwritten. Any new values will be
        appended to original values.

        :param topic_files: A list of paths to topics to scan into memory.
        """
        for topic_file in topic_files:
            with open(topic_file, 'r') as f:
                # Parse out the name of the topic
                topic_name = self._find_topic_name(topic_file)
                # Add the topic to the dictionary if it does not exist
                self._add_topic_name_to_dict(topic_name)
                topic_content = f.read()
                # Record the tags and the values
                self._add_tag_and_values_from_content(
                    topic_name, topic_content)

    def _find_topic_name(self, topic_src_file):
        # Get the name of each of these files
        topic_name_with_ext = os.path.basename(topic_src_file)
        # Strip of the .rst extension from the files
        return topic_name_with_ext[:-4]

    def _add_tag_and_values_from_content(self, topic_name, content):
        # Retrieves tags and values and adds from content of topic file
        # to the dictionary.
        doctree = docutils.core.publish_doctree(content).asdom()
        fields = doctree.getElementsByTagName('field')
        for field in fields:
            field_name = field.getElementsByTagName('field_name')[0]
            field_body = field.getElementsByTagName('field_body')[0]
            # Get the tag.
            tag = field_name.firstChild.nodeValue
            if tag in self.VALID_TAGS:
                # Get the value of the tag.
                values = field_body.childNodes[0].firstChild.nodeValue
                # Separate values into a list by splitting at commas
                tag_values = values.split(',')
                # Strip the white space around each of these values.
                for i in range(len(tag_values)):
                    tag_values[i] = tag_values[i].strip()
                self._add_tag_to_dict(topic_name, tag, tag_values)
            else:
                raise ValueError(
                    "Tag %s found under topic %s is not supported."
                    % (tag, topic_name)
                )

    def _add_topic_name_to_dict(self, topic_name):
        # This method adds a topic name to the dictionary if it does not
        # already exist

        # Check if the topic is in the topic tag dictionary
        if self._tag_dictionary.get(topic_name, None) is None:
            self._tag_dictionary[topic_name] = {}

    def _add_tag_to_dict(self, topic_name, tag, values):
        # This method adds a tag to the dictionary given its tag and value
        # If there are existing values associated to the tag it will add
        # only values that previously did not exist in the list.

        # Add topic to the topic tag dictionary if needed.
        self._add_topic_name_to_dict(topic_name)
        # Get all of a topics tags
        topic_tags = self._tag_dictionary[topic_name]
        self._add_key_values(topic_tags, tag, values)

    def _add_key_values(self, dictionary, key, values):
        # This method adds a value to a dictionary given a key.
        # If there are existing values associated to the key it will add
        # only values that previously did not exist in the list. All values
        # in the dictionary should be lists

        if dictionary.get(key, None) is None:
            dictionary[key] = []
        for value in values:
            if value not in dictionary[key]:
                dictionary[key].append(value)

    def query(self, tag, values=None):
        """Groups topics by a specific tag and/or tag value.

        :param tag: The name of the tag to query for.
        :param values: A list of tag values to only include in query.
            If no value is provided, all possible tag values will be returned

        :rtype: dictionary
        :returns: A dictionary whose keys are all possible tag values and the
            keys' values are all of the topic names that had that tag value
            in its source file. For example, if ``topic-name-1`` had the tag
            ``:category: foo, bar`` and ``topic-name-2`` had the tag
            ``:category: foo`` and we queried based on ``:category:``,
            the returned dictionary would be:

            {
             'foo': ['topic-name-1', 'topic-name-2'],
             'bar': ['topic-name-1']
            }

        """
        query_dict = {}
        for topic_name in self._tag_dictionary.keys():
            # Get the tag values for a specified tag of the topic
            if self._tag_dictionary[topic_name].get(tag, None) is not None:
                tag_values = self._tag_dictionary[topic_name][tag]
                for tag_value in tag_values:
                    # Add the values to dictionary to be returned if
                    # no value constraints are provided or if the tag value
                    # falls in the allowed tag values.
                    if values is None or tag_value in values:
                        self._add_key_values(query_dict,
                                             key=tag_value,
                                             values=[topic_name])
        return query_dict

    def get_tag_value(self, topic_name, tag, default_value=None):
        """Get a value of a tag for a topic

        :param topic_name: The name of the topic
        :param tag: The name of the tag to retrieve
        :param default_value: The value to return if the topic and/or tag
            does not exist.
        """
        if topic_name in self._tag_dictionary:
            return self._tag_dictionary[topic_name].get(tag, default_value)
        return default_value

    def get_tag_single_value(self, topic_name, tag):
        """Get the value of a tag for a topic (i.e. not wrapped in a list)

        :param topic_name: The name of the topic
        :param tag: The name of the tag to retrieve
        :raises VauleError: Raised if there is not exactly one value
            in the list value.
        """
        value = self.get_tag_value(topic_name, tag)
        if value is not None:
            if len(value) != 1:
                raise ValueError(
                    'Tag %s for topic %s has value %s. Expected a single '
                    'element in list.' % (tag, topic_name, value)
                )
            value = value[0]
        return value
