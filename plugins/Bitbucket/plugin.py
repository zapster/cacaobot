###
# Copyright (c) 2013, Josef Eisl
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.utils.structures import TimeoutQueue
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from bs4 import BeautifulSoup

import urllib2

class Bitbucket(callbacks.PluginRegexp):
    """Add the help for "@plugin help Bitbucket" here
    This should describe *how* to use this plugin."""
    threaded = True
    callBefore = ['URL', 'Web']
    unaddressedRegexps = ['snarfPullRequest']
    def __init__(self, irc):
        self.__parent = super(Bitbucket, self)
        self.__parent.__init__(irc)
        self.timeout_queue = TimeoutQueue(self.registryValue('snarferTimeout'))

    def _getResponse(self, id):
        queryurl = self.registryValue('bitbucketurl') + '/pull-request/' + str(id)

        self.log.info('Getting pull request from %s' % queryurl)

        try:
            pullrequestxml = utils.web.getUrl(queryurl)
        except utils.web.Error as e:
            self.log.info(str(e))
            return "pull-request not found: #" + str(id)
        if not pullrequestxml:
            raise callbacks.Error, 'Got empty empty content'

        soup = BeautifulSoup(pullrequestxml)

        status = None
        title = None
        authors = []


        def _find_div_class(tag,clazz):
            return tag.name == 'div' and tag.has_key('class') and tag['class'][0] == clazz

        tag = soup.find(lambda tag : _find_div_class(tag,'pull-request-title'))
        if tag:
            title = str(tag.h1.string).strip()
            self.log.info('Title: ' + title)

        tag = soup.find(lambda tag : _find_div_class(tag,'pull-request-status'))
        if tag:
            e = tag.find_all('span')
            self.log.info(str(e))
            if len(e) >=2:
                status = str(e[1].string).strip()
                self.log.info('Status: ' + status)

        tag = soup.find(lambda tag: tag.name == 'div' and tag.has_key('class') and 'author' in tag['class'])
        if tag:
            for li in tag.find_all('li'):
                author = str(li.span.string).strip()
                authors.append(author)
                self.log.info('Author: ' + author)

        say = queryurl
        if status:
            say += '   ' + str(status).upper()
        if title:
            say += '   "' + str(title) + '"'
        if authors:
            say += '   by'
        for author in authors:
            say += '  ' + str(author)
        return say

    def _check_timeout(self, id):
        if id in self.timeout_queue:
            return False

        self.timeout_queue.enqueue(id)
        return True

    def snarfPullRequest(self, irc, msg, match):
        r"""(?P<type>pull request|pull-request|pullrequest)[\s#]*(?P<id>\d+)"""
        channel = msg.args[0]
        #if not self.registryValue('bugSnarfer', channel): return

        id_matches = match.group('id').split()
        type = match.group('type')

        self.log.debug('Snarfed pull request ID(s): ' + ' '.join(id_matches))
        # Check if the bug has been already snarfed in the last X seconds
        msgs = []
        for id in id_matches:
            if not self._check_timeout(id):
                continue
            response = self._getResponse(id)
            if response:
                msgs.append(response)

        for msg in msgs:
            irc.reply(msg, prefixNick=False)

Class = Bitbucket


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
