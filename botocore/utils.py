# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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


def normalize_url_path(path):
    if not path:
        return '/'
    return remove_dot_segments(path)


def remove_dot_segments(url):
    # RFC 2986, section 5.2.4 "Remove Dot Segments"
    output = []
    while url:
        if url.startswith('../'):
            url = url[3:]
        elif url.startswith('./'):
            url = url[2:]
        elif url.startswith('/./'):
            url = '/' + url[3:]
        elif url.startswith('/../'):
            url = '/' + url[4:]
            if output:
                output.pop()
        elif url.startswith('/..'):
            url = '/' + url[3:]
            if output:
                output.pop()
        elif url.startswith('/.'):
            url = '/' + url[2:]
        elif url == '.' or url == '..':
            url = ''
        elif url.startswith('//'):
            # As far as I can tell, this is not in the RFC,
            # but AWS auth services require consecutive
            # slashes are removed.
            url = url[1:]
        else:
            if url[0] == '/':
                next_slash = url.find('/', 1)
            else:
                next_slash = url.find('/', 0)
            if next_slash == -1:
                output.append(url)
                url = ''
            else:
                output.append(url[:next_slash])
                url = url[next_slash:]
    return ''.join(output)
