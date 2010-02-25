"""
This Moves class provides parsing and saving for the moves/smoves command.
For this it defines/gets the icsbot['moves'] dataset.
"""

import re, time

import icsbot.misc.regex as reg

import datetime

try:
    import pytz
    TZINFO = pytz.timezone('UTC')
except:
    TZINFO = None

class Moves(object):
    """
    This class initializes movelist parsing for FICS, it does not parse arbitrary
    FICS output, but only grabs the moves you need for you. use
    Moves.get_move('smoves seberg -1', function, *args, **kwargs) for example. The

    The class isets ms 1. But it would also work fine with ms=0.
    """
    
    def __init__(self, icsbot, trigger_duplicate=True):
        self.regex = re.compile('^(?:Movelist for game (?P<gamenumber>\d+):)?\s*(?P<white>%s) \((?P<wrating>(\d+|UNR))\) vs. (?P<black>%s) \((?P<brating>(\d+|UNR))\) --- (?P<start_time>[^\n]+)\n\r(?P<rated>(Unrated|Rated)) (?P<variant>[^ ]+) match, initial time: (?P<time>\d+) minutes, increment: (?P<inc>\d+) seconds\.\s*\n\rMove [A-z ]+\n\r[- ]+\n\r(?P<data>[^{]+)\{(?P<longresult>[^}]*)\} (?P<result>[^ \n\r]*)' % (reg.HANDLE, reg.HANDLE), re.DOTALL)
        self._icsbot = icsbot
        self._icsbot.send('iset movecase 1')
        self._icsbot.send('iset ms 1')
        self._icsbot.send('set tzone gmt')
        
        self.MOVE_REG = re.compile('([a-hBNKQPRx@+#=1-8O-]+)\s+\(([.:\d]+)\)')
        

    def get_moves(self, command, function, *args, **kwargs):
        """Executes the command, parses FICS output and runs the function
        with function(Move, *args, **kwargs). Where Move includes the following info:
            o Adds Move['white'] and Move['black'] as the handles.
            o Adds Move['longresult'] = 'black resignes' and Move['result'] = '1-0'
            o Adds Move['moves'] = ['e4', 'e5', ...]
            o Adds Move['times'] = [seconds, seconds, ...] corresponding times.
            o Adds Move['gamenumber'] = gamenumber or None if it was smoves and
               False if we got nothing.
            o Adds Move['loaded'] = time_in_epoch so you can register this!
               (And you should register to _only_ this and load it for update).
            o Adds Move['rated'] = True | False
            o Adds Move['type'] = wild/fr, standard, etc. (as in moves output)
            o Adds Move['time'] and move['inc'] as integers.
            o Adds Move['wrating'] and Move['brating'], the ratings at the start
               of the game.
            o Adds Move['start_time'] a (naive) datetime.datetime object in GMT.
                It is naive if pytz is not installed.
        Should no moves be retrieved, it executes function(None, *args, **kwargs).
        """
        self._icsbot.execute(command, self._gotten_moves, function, *args, **kwargs)
        

    def _gotten_moves(self, data, function, *args, **kwargs):
        matches = self.regex.match(data)
    
        if not matches:
            function(None, *args, **kwargs)

        d = matches.groupdict()
        
        if d['rated'] == 'Rated':
            d['rated'] = True
        else:
            d['rated'] = False
        
        d['time'] = int(d['time'])
        d['inc']  = int(d['inc'])
    
        try:
            d['start_time'] = datetime.datetime.strptime(d['start_time'], '%a %b %d, %H:%M GMT %Y')
            d['start_time'].replace(tzinfo=TZINFO)
        except:
            print 'The timezone of this account is not set to GMT, I need GMT for datetime.datetime'
        
        # Would use one liner ifs, but 2.4 compatibility ...        
        if d['wrating'] == 'UNR':
            d['wrating'] = None
        else:
            d['wrating'] = int(d['wrating'])

        if d['brating'] == 'UNR':
            d['brating'] = None
        else:
            d['brating'] = int(d['brating'])
        
        data = d['data']
        del d['data']
        
        d['moves'] = []
        d['times'] = []
        
        data = self.MOVE_REG.findall(data)
        
        for mov in data:
            d['moves'] += [mov[0]]
            spam = mov[1].split(':')[::-1]
            t = 0
            for i in xrange(len(spam)):
                t += float(spam[i]) * 60**i
            d['times'].append(t)

        function(d, *args, **kwargs)
