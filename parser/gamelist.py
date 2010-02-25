"""This Moves class provides parsing and saving for the moves/smoves command.
For this it defines/gets the icsbot['moves'] dataset.
"""

import re, time, datetime

import icsbot.misc.regex as reg

class GameList(object):
    """This class defines the 'sgames' dataset, for a list of games on the
    server. This does not actually fetch all the running games yet. The list
    will build up as time goes on. Games that finish will not be dropped
    immdiatly (but also not forced to stay). Register the dropping by registering
    the result and start_time or end_time. NOTE: start_time and end_time
    are times as recored by the bot and not the server, use the moves.py to
    get the server start time for example. Also you can use update_time, if you
    must be sure to use something on all starting and running games. (update_time
    notifies of already running when logged, or other updates).
    
    The two times are set with event triggering, so register them.
    DATA STORED, on the gamenumber as handle (an integer):
        o whites and blacks handle
        o rated/unrated
        o variant
        o result
        o longresult
        o start_time as recorded by me
        o end_time as recorded by me as datetime.datetime utctime.
        o update_time When a "game" command output on FICS was parsed.
        (o game = game number again. Is the handle/main_key!)
    
    NOTE: games command parsing is right now only done to get a starting list
        of games. Updates are at this time not done.
    
    REQUIRES STATUS TO WORK (REMOVE THE games PARSING IF YOU DON'T WANT THAT)
    
    Module also adds a ["__status__"]["got_all"] item to the games Data object.
    This will be set from False to True, when all games (or hopefully all) are
    correctly grabbed. (Due to FICS and me not hacking around it there is a
    _very_ small chance that a game cannot be uniquely identified with a player
    and is thus dropped. This can only happen with games going on when I
    connect)
    """
    
    
    def __init__(self, icsbot, always_trigger_ending=True, get_games=True):
        """Use always_trigger_ending to get an game ending event even if bot
        did not see game start. Note then in this case _variant_, start_time
        and rated are set to None (we cannot get the info directly).
        """
        self._ate = always_trigger_ending
        reg_start = re.compile('^\{Game (?P<game>\d+) \((?P<white>[a-zA-Z]{3,17}) vs. (?P<black>[a-zA-Z]{3,17})\) (Creating|Continuing) (?P<rated>[^ ]*) (?P<variant>[^ ]*) match.\}$')
        reg_end   = re.compile('^\{Game (?P<game>\d+) \((?P<white>[a-zA-Z]{3,17}) vs. (?P<black>[a-zA-Z]{3,17})\) (?P<longresult>.*)\} (?P<result>.*)$')
        
        self._icsbot = icsbot
        
        self._icsbot.send('set gin 1')
        self._icsbot.send('iset allresults 1')
        
        # We will use games to save a set of for all objects, keeping them
        # in memory.
        self._games = set()
        
        self._sgames = self._icsbot['sgames', 'game', 0]
        
        self.status = self._sgames['__status__']
        self.status['got_all'] = False
        
        self._icsbot.reg_comm(reg_start, self._start)
        self._icsbot.reg_comm(reg_end, self._end)
        if get_games:
            self._icsbot.execute('games', self._grab_games)
        
    
    def _start(self, matches):
        t = time.time()
        d = matches.groupdict()
        d['end_time'] = None
        d['result'] = '*'
        d['longresult'] = 'game in progress'
        
        game = int(d['game'])
        del d['game']
        
        if d['rated'] == 'rated':
            d['rated'] = True
        else:
            d['rated'] = False
        
        # Not that this must go first because we have no buffer.
        self._games.add(self._sgames[game])
        # Then we can:
        self._sgames[game].items.update(d)
        self._sgames[game]['start_time'] = t
    
    
    def _grab_games(self, data):
        reg_games = re.compile('((^(?P<data>.*)\n\r  (?P<displayed>\d+) games? displayed( \(of (?P<progress>\d+) in progress\))?\.$)|(^No matching games were found \(of \d+ in progress\)\.$))', re.MULTILINE | re.DOTALL)
        matches = reg_games.match(data)
        variants = {'n': 'non standard', 'w': 'wild', 'b': 'blitz', 's': 'standard', 'l': 'lightning', 'B': 'bughouse', 'x': 'atomic', 'z': 'crazyhouse', 'L': 'losers', 'S': 'suicide', 'u': 'untimed'}
        M = matches.groupdict()

        if M.has_key('data'):
            data = M['data']
            r = re.compile('^\s*(?P<gamenumber>[\d]+) +(?P<w_rating>(?:\d+|\+{4,4}|-{4,4})) (?P<white>[a-zA-Z]+) +(?P<b_rating>(?:\d+|\+{4,4}|-{4,4})) (?P<black>[a-zA-Z]+) +\[(?P<private>(?:p| ))(?P<variant>[A-z])(?P<rated>(?:r|u)) *(?P<time>[\d]+) +(?P<inc>[\d]+)\][^(]+\( ?(?P<w_material>[\d]+)- ?(?P<b_material>[\d]+)\) .: *(?P<move>[\d]+)\s*$', re.MULTILINE)
            
            matches = r.findall(data)
            
            handles = [user['handle'] for user in self._icsbot['users'].online]
            handles.sort()

            white = {}
            black = {}
            for handle in handles:
                if white.has_key(handle[:11].lower()):
                    # In this case we cannot uniquely say who is playing the
                    # game. We will just drop those rare games lateron.
                    white[handle[:11].lower()] = None
                else:
                    white[handle[:11].lower()] = handle
                
                if black.has_key(handle[:10].lower()):
                    # In this case we cannot uniquely say who is playing the
                    # game. We will just drop those rare games lateron.
                    black[handle[:10].lower()] = None
                else:
                    black[handle[:10].lower()] = handle
            
            for match in matches:
                d = {}
                d['game'] = int(match[0])
                if match[1] == '++++' or match[1] == '----':
                    d['w_rating'] = None
                else:
                    d['w_rating'] = int(match[1])
                
                d['white'] = white[match[2].lower()]
                if d['white'] is None:
                    print 'Warning: Game %s is considered not existent because of ambiguous whites handle: %s' % (d['game'], match[2])
                    continue
                
                if match[3] == '++++' or match[3] == '----':
                    d['b_rating'] = None
                else:
                    d['b_rating'] = int(match[3])
                
                d['black'] = black[match[4].lower()]
                if d['black'] is None:
                    print 'Warning: Game %s is considered not existent because of ambiguous blacks handle: %s' % (d['game'], match[4])
                    continue  
                
                if matches[5] == 'p':
                    d['private'] = True
                else:
                    d['private'] = False
                
                d['variant'] = variants[match[6]]
                
                if matches[7] == 'r':
                    d['rated'] = True
                else:
                    d['rated'] = False
                
                d['time'] = int(match[8])
                d['inc'] = int(match[9])
                d['w_material'] = int(match[10])
                d['b_material'] = int(match[11])
                d['moves']    = int(match[12])     
                
                game = self._sgames[d['game']]
                # I update d, so that it overwrites anything here thats worse info.
                d.update(game.items)
                game.items.update(d)
                game['update_time'] = time.time()
                self._games.add(game)
            
            # In case this was not the first time, we need to check what the
            # status is.
            if not self.status['got_all']:
                # We will only update if all games were displayed. Otherwise
                # we assume there is something wrong, this is the case if:
                if M['progress'] is None:
                    self.status['got_all'] = True
        
    
    def _end(self, matches):
        t = time.time()
        d = matches.groupdict()
        game = int(d['game'])
        game = self._sgames[game]
        if game not in self._games:
            # overwriting in case there is something else still cached.
            game.items.update({'white': d['white'], 'black': d['black'], 'start_time': None, 'variant': None, 'rated': None})
            if not self._ate:
                return

        game['result'] = d['result']
        game['longresult'] = d['longresult']
        game['end_time'] = datetime.datetime.utcnow()
        
        try:
            self._games.remove(game)
        except:
            pass
