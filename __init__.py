#-*- coding: utf-8 -*-
"""Classes defined here (Please look at help(icsbot.IcsBot):
    o IcsBot: The main class. It is imported here, but package help will not
        show it appearently.

Further modules provided:
    o Status: Module which provides information on online status of users.
    o Also a fiew more invisible ones, that are all accessable through IcsBot
    o parser provides some more parsing modules:
        o gamelist: Keep a up to all games being played, starting or ending
            on FICS
        o moves: Parse the moves/smoves command.
    o misc are some more tools, some useful some less so. The for sure working
        and useful are:
        o sqldata: Provides an interface to have IcsBot Data Items to be stored
            and loaded from a database automatically (they are still cached
            though)
        o pgn: Provides a pgn generator from a dictionary similar to
            parser.moves output.
        o tells: Provides a parser function to correctly parse things like:
            "asdf fds d" -t --test "fd sdfs", etc.
        o glicko: Module which knows glicko rating system (2 and 1) for FICS
            like live updating. (It does not support period based updates but
            does updates for each game immidiatly)

This is made available under the LGPL version 3 -- see
http://www.gnu.org/licenses/lgpl.html. I would appriciate it if you send me
modifications and improvements you make!
"""

__version__ = '2.0'
__author__ = 'Sebastian Berg'
__copyright__ = 'Sebastian Berg 2008'
__license__ = 'LGPLv3'
__email__ = 'sebastian@sipsolutions.net'

__all__ = ['_data', '_qtell', 'status', '_tells', 'qtelldummy', 'misc', 'parser', 'icsbot']


import time, socket, re, datetime

try:
    import pytz
    TZINFO = pytz.timezone('UTC')
except ImportError:
    print 'No pytz available, times will be naive datetimes.'
    TZINFO = None

import _data, tells, misc.regex

class IcsBot(object):
    """This is the base class to handle the connection (and timer).

    Functions/Classes that want to get access to FICS output need to register
    with this module. They have the following functions available to call in
    this modules instance:
        o register(regular expression object OR unparsed string, itself)
        o unregister(itself).
    Note, that due to the fact that python cleans up behind you, a
    class/function should selfdestruct when it calls unregister (unless
    you reference it from somwhere else of course).
    
    There is one more thing available for you which can be handy:
        o Use timer(time_in_epoch, function) to have a specific function
           be called when the time is reached. I am not too happy with
           the implementation, but I think its the best you will get.

    NOTES:
        o The function to first register, is the function that will
           first be tried to match for.
        o Note that the parser strips commands, so you don't need to expect
           any whitespaces, even if there “should” be.
        o If you want to parse something before the first prompt, you will need
           to register something to match it all at once.
           
    Some other variables:
        o self.READ_SIZE: amount of data the socket tries to read at once.
        o self.TIMEOUT: default timeout on the socket (Modified for the
           timer implementation). Set to None if your connection is stable,
           otherwise I will consider the connection dead when the timeout
           is ever hit. (And if your bot does almost nothing, FICS can be
           quiet)
        o self.ics: The actual socket being used (when connected).
        o self.block_code: The current block code gotten or None
    
    If ptime is set, IcsBot.fics_time will be the time (hour and minute) when
    the last command was gotten. Else it is None. The bot currently sets the
    timezone to GMT for simplicity.
    """

    def __init__(self, qtell_dummy=False, qtell_width=78, interface='seberg\'s base bot.', unmatched_log=None, tell_logger=None):
        """Optional arguments:
            o qtell_dummy=False. Set to true if qtells are not possible.
            o qtell_width=78. Default Qtell widths. (ignored with dummy.)
            o interface="seberg's base bot." FICS interface variable.
            o tell_logger = Function which will be used to log all tells to the
                bot. IE. pass sys.stdout.write to print, (default no logging).
        """
        self._buffer = ''
        # Initialize stupid to get around having to check later.
        self._timed = []
        self._registered = []
        
        self.handle = None
        self.tags = None

        self.READ_SIZE = 2048
        self.TIMEOUT = 300
        
        self._prompt = re.compile('\n\r(?:(\d\d):(\d\d)_)?fics% ')

        self._data_sets = {}
        self._qtell_dummy = qtell_dummy
        
        self._used_blocks = set()
        self._block_funcs = {}
        self._block_regex = re.compile('^\x15(?P<id>\d+)\x16(?P<code>\d+)\x16(?P<data>.*)$', re.DOTALL)
        
        if not qtell_dummy:
            import _qtell
            self.qtell = _qtell.Qtell(width=qtell_width, users=self['users'])
        else:
            import _qtelldummy
            self.qtell = _qtelldummy.QtellDummy()
        
        self._tells = tells.PrivateTells(self, tell_logger)
        # Provide access to self._tells register/unregister functions:
        self.reg_tell = self._tells.register
        self.deco_tell = self._tells.decorate

        self.send = self._store_send
        self.execute = self._store_execute
        
        self.fics_time = None
        self.block_code = None
        
        self.unmatched_log = unmatched_log
        
        self.send_after=[('normal', 'iset nowrap 1'), ('normal', 'set interface %s' % interface), ('normal', 'set seek 0'), ('normal', 'iset defprompt 1'), ('normal', 'set tzone GMT')]


    def send(self, obj):
        """Send data to FICS. Accepts one string OR iteratable item that
        gives strings. Each string should be one line, a newline is
        appended automatically.
        (This function does not actually exist as such, but is defined after
        creation to the approriate send function.)
        
        NOTE: Use iterables to send more then one command. Using \\n will
            NOT work, because of block.
        """
        pass
        
    
    def execute(self, command, handler, *args, **kwargs):
        """Execute a command on FICS, giving a handler function that will get
        the data returned by FICS. This uses blocking, so you can be sure
        to get a result, and that this will be exactly what you want.
        For just anything to send, use the send function.
        (This function does not actually exist as such, but is defined after
        creation to the approriate send function.)
        
        Further *args and **kwargs are given to the handler function, thus it
        should take handler(data, *args, **kwargs).
        """
        pass
    

    def _send(self, obj):
        """Send data to FICS. Accepts one string OR iteratable item that
        gives strings. Each string should be one line, a newline is
        appended automatically.
        
        NOTE: Use iterables to send more then one command. Using \\n will
            NOT work, because of block.
        """
        #print 'sending:', repr(obj)
        
        # We use 1 for all miscallaneous commands.
        if not obj:
            return
        elif type(obj) == str or type(obj) == unicode:
            self.ics.send('1 ' + obj + '\n')
        else:
            for command in obj:
                self.ics.send('1 ' + str(command) + '\n')    
    
    
    def _execute(self, command, handler, *args, **kwargs):
        """Execute a command on FICS, giving a handler function that will get
        the data returned by FICS. This uses blocking, so you can be sure
        to get a result, and that this will be exactly what you want.
        For just anything to send, use the send function.
        (This function does not actually exist as such, but is defined after
        creation to the approriate send function.)
        
        Further *args and **kwargs are given to the handler function, thus it
        should take handler(data, *args, **kwargs).
        """
        #print 'sending:', repr(obj)
        
        i = 0
        for i in xrange(2,1000):
            if i not in self._used_blocks:
                self._used_blocks.add(i)
                break
        else:
            raise Exception('More then 999 commands executed (and no result gotten), quitting, as this is most likely a (spammy) bug. If you do need more, check the code.')
        
        self.ics.send(('%s ' % i) + command + '\n')
        self._block_funcs[i] = (handler, args, kwargs)
    
    
    def _store_send(self, obj):
        """Command that stored things to send to the server, if we are not
        yet connected.
        SEND USUALLY DOES:
        Send data to FICS. Accepts one string OR iteratable item that
        gives strings. Each string should be one line, a newline is
        appended automatically.
        """
        self.send_after += [('normal', obj)]


    def _store_execute(self, command, handler, *args, **kwargs):
        """Command that stored things to execute on the server, if we are not
        yet connected. further args and kwargs are passed on to the function.
        """
        self.send_after += [('block', command, handler, args, kwargs)]       

    
    def __getitem__(self, item):
        """Create or get a data item. If a tuple is given (ie, not ['users'],
        but ['sgames', 'game'], then the second item will be the new main_key
        of the data item (see corresponding class). In this case it will always
        be overwritten). A possible third item sets the buffer size, not that
        this should really matter for anything much *item[1:] is handed on.
        """
        if type(item) is tuple:
            self._data_sets[item[0].lower()] = _data.Data(*item[1:])
            return self._data_sets[item[0].lower()]
        try:
            return self._data_sets[item.lower()]
        except KeyError:
            self._data_sets[item.lower()] = _data.Data()
            return self._data_sets[item.lower()]


    def reg_comm(self, REGEX, function):
        """register(regular expression object OR unparsed string, itself)
        Register a function to be parsed. The function must accept the
        corresponding match object as argument.
        
        NOTE: The bot uses FICS blocking, but it does not matter for these
            regexes. Things that are matched through blocking (execute command)
            will not be matched with these regexes.
        
        ALSO NOTE:
            The bot strips the FICS data from whitespaces. This means that
            in very fiew cases (ie. sending "asdf(1)" which is an invalid command)
            it cannot be differentiated from asdf telling in 1 Command not found.
        """
        if type(REGEX) is str:
            REGEX = re.compile(REGEX)
        
        self._registered += [[REGEX, function]]
    
    
    def unreg_comm(self, function):
        """unreg_comm(function)
        Unregister a function (itself usually from being parsed.
        (Loops through the all functions and deletes all occurences)
        """
        to_delete = []
        # Get all indexes with the function:
        for i in xrange(0, len(self._registered)):
            if self._registered[i][1] == function:
                to_delete += [i]
                
        # Reverse the list of occurences.
        to_delete.reverse()
        
        # Delete the Occurences from the end, so that the indexing doesn't
        # change.
        for i in to_delete:
            del self._registered[i]


    def connect(self, user='guest', password='', ics='freechess.org', port=5000):
        """Connect to FICS and returns a socket object.
        Anything send before connection is only send after you are connected.
        This command also sets a header and a next info item to the qtell class,
        as those use the provided username. Overwrite them again after
        connection if you want something else.
        """
        try:
            del self.ics
        except AttributeError:
            pass
        
        s = socket.socket()
        # For connection purpose ... use max 60 second timeout. Otherwise we
        # really are laggy (and FICS timeouts anyways).
        if self.TIMEOUT:
            s.settimeout(min(60, self.TIMEOUT))
        else:
            s.settimeout(60)
        s.connect((ics, port))

        data = ''
        while True:
            try:
                new = s.recv(self.READ_SIZE)
            except socket.timeout:
                s.close()
                raise ConnectionClosed('Socket timeout (max. 60 seconds) reached while connecting.')
            if new == '':
                s.close()
                raise ConnectionClosed('Socket was closed while connecting.')
                return
            data += new
            if data.endswith('login: '):
                s.send(user + '\n')
                break
        
        data = ''
        while True:
            try:
                new = s.recv(self.READ_SIZE)
            except socket.timeout:
                raise ConnectionClosed('Socket timeout (max. 60 seconds) reached while connecting.')
            if new == '':
                raise ConnectionClosed('Socket was closed while connecting.')
                return
            data += new

            # If server wants us to login as guest:
            if data.endswith('":\n\r'):
                # Lets get over with it ...
                s.send('\n')
                break
            
            if 'guest connections have been prevented' in data:
                raise InvalidLogin('Guest connections are blocked.')
                break
            
            elif data.endswith('password: '):
                if not password:
                    raise InvalidLogin('Registered account, but no password.')
                s.send(password + '\n')
                break
            
            elif data.endswith('login: '):
                raise InvalidLogin('Invalid username.')
                return
                
        data = ''
        while True:
            # ignore the read here. I have no idea what the 10 does, but
            # it does one thing I want, and that is not to read too much.
            try:
                new = s.recv(self.READ_SIZE)
            except socket.timeout:
                raise ConnectionClosed('Socket timeout (max. 60 seconds) reached while connecting.')
            if new == '':
                raise ConnectionClosed('Socket was closed while connecting.')
                return
            data += new
            
            if '**** Invalid password! ****' in data:
                raise InvalidLogin('Invalid Password.')
                return
            elif '**** Starting FICS session' in data:
                break
            elif 'already logged in ***' in data:
                raise InvalidLogin('Handle in use.')
                return        
        
        offset = data.find('**** Starting FICS session')
        self._buffer = data[offset:]

        r = re.compile('\*\*\*\* Starting FICS session as (%s)(%s) \*\*\*\*' % (misc.regex.HANDLE, misc.regex.TAGS))
        self.handle, self.tags = r.match(self._buffer).groups()
        self.ics = s
        self.ics.settimeout(self.TIMEOUT)
        
        if not self._qtell_dummy:
            print 'setting next note.'
            self.qtell.set_header('%s%s:' % (self.handle, self.tags))
            self.qtell.set_next_note('Use "tell %s next" to view more.' % self.handle)
        else:
            # Just to make sure that we don't have too long tells ...
            # I did not check the widths exactly.
            if 'U' in self.tags:
                self.qtell.__class__.width = 170
            elif 'C' in self.tags or '*' in self.tags or 'TM' in self.tags or 'TD' in self.tags or 'SR' in self.tags:
                self.qtell.__class__.width = 999
            else:
                self.qtell.__class__.width = 370
        
        s.send('iset block 1\n')
                
        self.send = self._send
        self.execute = self._execute
        for i in self.send_after:
            if i[0] == 'normal':
                self.send(i[1])
            else:
                self.execute(i[1], i[2], *i[3], **i[4])


    def close(self):
        """Close the connection and delete self.ics the hard way. Raises
        ConnectionClosed('Closed by us.')
        """
        self.send('$quit')
        self.ics.close()
        del self.ics
        raise ConnectionClosed('Closed by us.')
    

    def timer(self, epoch, function, *args, **kwargs):
        """timer(time_in_epoch, function, *args, **kwargs):
        Register a function to be executed at a specific time. All args
        and kwargs are passed through to the function.
        Old times are quietly ignored (function will get executed later)
        """
        self._timed += [[epoch, function, args, kwargs]]
        self._timed.sort()


    def remove_timer(self, epoch, function, no_kwargs=False, *args, **kwargs):
        """remove_timer(time_in_epoch, function, *args, no_kwargs=False, **kwargs):
        Removes a timer, if the time is None, removes all matching
        timed commands without checking the time.
        
        If no_kwargs is given, matches the function only for args.
        """
        if epoch is None and no_kwargs is True:
            to_del = []
            for i in xrange(0, len(self._timed)):
                if self._timed[i][1] == function and self._timed[i][2] == args:
                    to_del += i
            for i in to_del:
                del self._timed[i]
        elif epoch is None:
            to_del = []
            for i in xrange(0, len(self._timed)):
                if self._timed[i][1] == function and self._timed[i][2] == args and self._timed[i][3] == kwargs:
                    to_del += i
            for i in to_del:
                del self._timed[i]
        elif no_kwargs is True:
            to_del = []
            for i in xrange(0, len(self._timed)):
                if self._timed[i][0] == epoch and self._timed[i][1] == function and self._timed[i][2] == args:
                    to_del += i
            for i in to_del:
                del self._timed[i]                        
        else:
            self._timed.remove([epoch, function, args, kwargs])
    
    
    def parse_block(self, data):
        """This function can be used to get a snipplet from FICS parsed alone,
        which was garbage to some other parsing function.
        
        IE. before (and after) style 12 info there can be quite a bit of spam
        which is basically unrelated to style 12. I don't know if this can be
        needed, but I provide the possibility anyways.
        """
        data = data.strip()
        if not data:
            return
        for (regex, function) in self._registered:
            match = regex.match(data)
            if match:
                self.send(function(match))
                break
        
        if self.unmatched_log is not None:
            self.unmatched_log.write(data)
    
    
    def _parse(self, string):
        buf = self._buffer + string
        
        split = []
        prev = 0
        for match in self._prompt.finditer(buf):
            if match.groups()[0]:
                t = datetime.time(int(match.groups()[0]), int(match.groups()[1]), tzinfo=TZINFO)
            else:
                t = None
            split.append((buf[prev:match.start()], t))
            prev = match.end()
        
        # The last item in list is not yet complete.
        self._buffer = buf[prev:]

        # loop through all the outputs and match each with all regexes, after
        # checking for blocks.
        for ics_output, t in split:
            self.fics_time = t
            # Now FICS has a bad habit of (at least for error messages because
            # of no ID) not doing quite prompt to prompt sending with blocking.
            # so we first split along \x17.
            outputs = ics_output.split('\x17')
            for block in outputs:
                # Delete annoying whitespaces.
                block_match = self._block_regex.match(block)
                if block_match:
                    info = block_match.groupdict()
                    data = info['data'].strip()
                    id_ = int(info['id'])
                    self.block_code = int(info['code'])
                    if self._block_funcs.has_key(id_):
                        handler = self._block_funcs[id_]
                        self.send(handler[0](data, *handler[1], **handler[2]))
                        del self._block_funcs[id_]
                        self._used_blocks.remove(id_)
                else:
                    data = block.strip()
                    self.block_code = None
                                                
                for (regex, function) in self._registered:
                    match = regex.match(data)
                    if match:
                        self.send(function(match))
                        break
                
                if self.unmatched_log is not None:
                    self.unmatched_log.write(block)
            

    def run(self):
        # The mainloop
        timed = False
        while True:
            # Current time, we don't want any chance of race conditions here.
            # The timeout, must not be 0/negative, or we get a non-blocking
            # reading and a different exception. Don't feel like thinking about
            # it more.
            t = time.time()
            while self._timed and self._timed[0][0] <= t:
                self.send(self._timed[0][1](*self._timed[0][2], **self._timed[0][3]))
                del self._timed[0]
            
            if self._timed:
                next = self._timed[0][0] - t
                timed = True
            else:
                # We use default timeout:
                next = self.TIMEOUT
                timed = False
            
            self.ics.settimeout(next)    
            try:
                data = self.ics.recv(self.READ_SIZE)
            # If a timeout is hit, we don't need to parse something.
            except socket.timeout:
                if not timed:
                    self.send('$quit')
                    self.ics.close()
                    del self.ics
                    raise ConnectionClosed('Socket timeout')
                continue

            if data == '':
                # Raise a corresponding exception or close if all is good.
                b = self._buffer
                
                if '**** You have been kicked out by' in b:
                    raise(ConnectionClosed('Nuked'))
                elif 'you can\'t both be logged in. ****' in b:
                    raise ConnectionClosed('Someone logged in as me.')
                elif 'Logging you out.' in b:
                    raise ConnectionClosed('Closed by us.')
                else:
                    raise ConnectionClosed()
            
            # Parse and act upon the data if functions are registered:
            self._parse(data)



class InvalidLogin(Exception):
    """Is raised if the Login fails (not because of a connection error).
    Possible error descriptions are:
        o 'Registered account, but no password.'
        o 'Invalid username.' (FICS didn't like what we send)
        o 'Invalid Password.'
        o 'Handle in use.' (This is for a guest logins)
        o 'Guest connections are blocked.' (This is if FICS had massive problems
            with some guests)
    """
    def __init__(self, string=''):
        self.value = string
    def __str__(self):
        return self.value

class ConnectionClosed(Exception):
    """Is raised whenever the connection is closed (even with IcsBot.close()).
    Possible error descriptions are:
        o 'Someone logged in as me.'
        o 'Socket timeout'
        o 'Nuked'
        o 'Socket closed.' (Fallback)
        o 'Closed by us.'
        o 'Socket timeout (max. 60 seconds) reached while connecting.'
        o 'Socket was closed while connecting.'
    NOTE: The usual socket Exceptions still occur (just not timeout of course).
    """
    
    def __init__(self, string='Socket closed.'):
        self.value = string
    def __str__(self):
        return self.value
