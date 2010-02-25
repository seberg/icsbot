"""This class should provide further parsing functions for games. It also
provides the style12 parsing function. Please note that some information can
come together with style 12 that is mostly unrelated (if it is your game it can
include the gin notification). The function returns "spam", which is split
on \\n and can be send to IcsBot.parse_block to make sure that all is good.
"""

import re
import icsbot.misc.regex as _regex

def style12(data):
    """Process style 12 output, data can either be a match object (of the regex
    in icsbot.misc.regex) or a string.
    
    ep_file can be None,
    ep_square will be "-" then.
    
    Check dict returned for all the stuff it gets, most is converted to more
    readable and integer or float output.
    
    for an isolated position the game number may or may not be of interest
    (It is correct for ongoing games, ie. the refresh command used on games
    you are not observing/playing/examining, but will be a bogus unused one for
    the spos command.)
    
    All times in seconds. The function does work for (iset) ms=1 and 0 the same.
    """
    if type(data) is str or type(data) is unicode:
        matches = _regex.STYLE12_re.match(data)
    else:
        matches = data
    
    if not matches:
        return
    
    d = matches.groupdict()
    ms = '.' in d['move_time']
    
    fen = d['position'].strip()
    fen = fen.replace(' ', '/')

    r = re.compile('(-+)')

    l = r.split(fen)
    for i in xrange(1, len(l),2):
        l[i] = str(len(l[i]))
    fen = ''.join(l)
    
    d['fen_pos'] = fen
    
    d['to_move'] = d['to_move'].lower()
    if d['move_san'] == 'none':
        d['move_san'] = None
    
    if d['move_coord'] == 'none':
        d['move_coord'] = None
    
    files = {'-1':None, '0':'a', '1':'b', '2':'c', '3':'d', '4':'e', '5':'f', '6':'g', '7':'h'}
    d['ep_file'] = files[d['ep_file']]
    if d['ep_file']:
        d['ep_square'] = d['ep_file'] + ('6' if d['to_move'] == 'B' else '3')
    else:
        d['ep_square'] = '-'
    
    castles = ''
    
    d['w_k_castle'] = int(d['w_k_castle'])
    d['w_q_castle'] = int(d['w_q_castle'])
    d['b_k_castle'] = int(d['b_k_castle'])
    d['b_q_castle'] = int(d['b_q_castle'])
    
    d['w_time'] = int(d['w_time'])
    d['b_time'] = int(d['b_time'])
    if ms:
        d['w_time'] = d['w_time']/1000.0
        d['b_time'] = d['b_time']/1000.0
    
    if d['w_k_castle']:
        castles += 'K'
    if d['w_q_castle']:
        castles += 'Q'
    if d['b_k_castle']:
        castles += 'k'
    if d['b_q_castle']:
        castles += 'q'
    if castles == '':
        castles = '-'
    
    d['fen'] = fen + ' %s %s %s %s %s' % (d['to_move'], castles, d['ep_square'], d['irr_ply'], d['move_num'])
    
    d['spam'] = d['spam'].split('\n')
    d['flip'] = (True if d['flip']==1 else False)
    d['clock_running'] = (True if d['clock_running']==1 else False)
    d['lag'] = int(d['lag'])/1000.0
    d['time'] = int(d['time'])/60.0
    d['inc'] = int(d['inc'])
    d['irr_ply'] = int(d['irr_ply'])
    d['move_num'] = int(d['move_num'])
    d['ply'] = d['move_num'] * 2 - (d['to_move'] == 'w')
    
    spam = d['move_time'].split(':')[::-1]
    d['move_time'] = 0
    for i in xrange(len(spam)):
        d['move_time'] += float(spam[i]) * 60**i
    
    d['game'] = int(d['game'])
    
    # The relation to the game:
    if d['relation'] == '-3':
        # We check the spam that came before
        for spam in d['spam']:
            if 'Position of stored game' in spam:
                d['relation'] = ('isolated', 'stored')
        d['relation'] = ('isoltated', 'game')
    elif d['relation'] == '-2':
        d['relation'] = ('observeing', 'examined')
    elif d['relation'] == '2':
        d['relation'] = ('examiner', 'examined')
    elif d['relation'] == '0':
        d['relation'] = ('observeing', 'played')
    elif d['relation'] == '-1':
        d['relation'] = ('playing', 'opponents move')
    elif d['relation'] == '1':
        d['relation'] = ('playing', 'my move')
    else:
        print 'Warning: unknown game relation'
        d['relation'] = ('unknown',)
    
    return d


def GameInfo(object):
    """The class registeres with bot['games'] and fills them with information
    from style 12. Right now parsing is only supported for:
        WORK IN PROGRESS
    """
    def __init__(self, icsbot):
        pass
