"""
Module to include the Status class which will, if started, make sure that
you have always a list of online users stored in Users.online, as well as
add an online information to all users. It will also keep all online users
locked.

The users are stored in Users.online as user data objects.
"""

import re

class Status(object):
    def __init__(self, icsbot=None):
        """
        Initialize the Status class with icsbot instance.
        Note that while the status itself is instant (playing, examing), The
        Game information is only gotten later.
        Adds to the users class:
            o A set of online users. users.online (user instances).
            o The online attribute each user (You can register it).
            o Adds/expands the tags attribute to include Fide titles, computer
               or unregistered.
        Currently no ratings are fetched/parsed.
        
        NOTE:
            o whoIA is parsed once, after that everything is kept up to date
                with iset pin 1 info. So if connection is lost, use the
                reset function.
        """
        
        assert icsbot, 'Must give the Main instance.'

        self.send = icsbot.send
        self._icsbot = icsbot
        self._users = self._icsbot['users']
        self.status = self._users['__status__']
        self.status['got_all'] = False
        
        self._users.online = set()            
        
        self.send('iset pin 1')
        icsbot.execute('who IbslwBzSLx', self._who_i)
        
        self.re_connect = re.compile('^<wa> (?P<handle>[a-zA-Z]*).(?P<tags>\d{2})(?P<blitz>\d+)[^0-9](?P<standard>\d+)[^0-9](?P<lightning>\d+)[^0-9](?P<wild>\d+)[^0-9](?P<bughouse>\d+)[^0-9](?P<crazyhouse>\d+)[^0-9](?P<suicide>\d+)[^0-9](?P<losers>\d+)[^0-9](?P<atomic>\d+)[^0-9]?$')
        self.re_disconnect = '^<wd> (?P<handle>.*)$'


    def _set_tags(self, usr, tags):
        # Set the tags based on the string gotten from server.
        info1 = int(tags[1])
        info2 = int(tags[0])
        tags = set()
        if info1 & 1:
            tags.add('U')
        if info1 & 2:
            tags.add('C')
        if info1 & 4:
            tags.add('GM')
        if info1 & 8:
            tags.add('IM')
        if info2 & 1:
            tags.add('FM')
        if info2 & 2:
            tags.add('WGM')
        if info2 & 4:
            tags.add('WIM')
        if info2 & 8:
            tags.add('WFM')
        
        usr['tags'] = tags

    
    def _who_i(self, data):
        pattern = re.compile('^\r?(?P<handle>[a-zA-Z]{3,18}).(?P<tags>\d{2})(?P<blitz>\d+)[^0-9](?P<standard>\d+)[^0-9](?P<lightning>\d+)[^0-9](?P<wild>\d+)[^0-9](?P<bughouse>\d+)[^0-9](?P<crazyhouse>\d+)[^0-9](?P<suicide>\d+)[^0-9](?P<losers>\d+)[^0-9](?P<atomic>\d+)[^0-9]\s*$', re.MULTILINE)
        online = set()
        for m in pattern.finditer(data):
            d = m.groupdict()
            usr = self._users[d['handle']]
            online.add(usr)
            usr.items.update(d)
            self._set_tags(usr, d['tags'])
            usr['online'] = True

        # Lets make sure that all users are correctly set to offline too.
        meantime_change = self._users.online.difference(online)
        for user in meantime_change:
            usr['online'] = False
        
        self._users.online = online

        self._icsbot.reg_comm(self.re_connect, self._connect)
        self._icsbot.reg_comm(self.re_disconnect, self._disconnect)
        
        self.status['got_all'] = True
        
        print 'known:', len(self._users.online)
        print 'expected:'
        print data.split('\n')[-1]


    def _connect(self, matches):
        d = matches.groupdict()
        usr = self._users[d['handle']]
        self._users.online.add(usr)
        usr.items.update(d)
        tags = d['tags']
        self._set_tags(usr, tags)
        usr['online'] = True
    
    
    def _disconnect(self, matches):
        handle = matches.group('handle')
        usr = self._users[handle]
        self._users.online.remove(usr)
        usr['online'] = False
        
    
    def reset(self):
        """
        Reset the status for when the bot disconnected. Note that the status
        is only correct after who IA has been parsed. (as always true)
        """
        self._icsbot.unreg_comm(self._connect)
        self._icsbot.unreg_comm(self._disconnect)
        self._users.online = set()
        self.execute('who IbslwbzSLx', self._who_i)
