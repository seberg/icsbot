def emt(s, total_time, time, inc, moves, float_seconds=False, take_int=True):
    """Function to be given to make_pgn so that times are of %emt
    (Elapsed Move Time) format, rounding errors could potentiall stack:
    [%emt h:mm:ss]. If float_seconds is True, then format is
    [%emt h:mm:ss.fracs]

    If take_int is True (default). The clock shows the full seconds remaining,
    else the clock will show mathematically correct rounded seconds. This
    is of course ignored if float_seconds is True
    
    NOT TESTED. (but should be fine due to similarity to clk)
    """
    h = s // 3600
    s = s % 3600
    m = s // 60
    s = s % 60
    fs = s % 1
    if take_int:
        s = int(s)
    else:
        s = int(round(s))
    s = str(s).zfill(2)
    if float_seconds:
        s = '%s.%s' % (s, str(fs)[2:])
        
    return '[%%emt %s:%s:%s]' % (int(h), str(int(m)).zfill(2), s)


def clk(seconds, total_time, time, inc, moves, float_seconds=False, take_int=True):
    """Function to be given to make_pgn so that times are show the current
    clock time in the %clk format:
    [%clk h:mm:ss]. If float_seconds is True, then format is
    [%clk h:mm:ss.fracs]
    
    If take_int is True (default). The clock shows the full seconds remaining,
    else the clock will show mathematically correct rounded seconds. This
    is of course ignored if float_seconds is True
    """
    incs = moves - 1
    s = time + inc * incs - total_time
    
    h = s // 3600
    s = s % 3600
    m = s // 60
    s = s % 60
    fs = s % 1
    if take_int:
        s = int(s)
    else:
        s = int(round(s))
    s = str(s).zfill(2)
    if float_seconds:
        s = '%s.%s' % (s, str(fs)[2:])
        
    return '[%%clk %s:%s:%s]' % (int(h), str(int(m)).zfill(2), s)
    

def make_pgn(info, format_time=clk, utc_tag=True, default_site='FICS, San Jose, California USA', default_event='Casual Game', elo='Elo', max_width=80, first_move_inc=False):
    """Create a pgn from the dict info, which should be similar to the
    parser.moves information. This means it should/can include the following
    items (items with value of None are generally ignored):
        o tourney or event. Either one is OK and will be used for the
            PGN Event field.
        o round
        o site
        o startpos or start_pos or fen. String used to set FEN field
            NOTE unless fen, " w KQkq - 0 1" is appended to make FEN complete.
        o start_time Will be used to set Date and Time field. Must be either
            2008-03-23 14:30:30 format or a datetime.datetime object.
            (also 2008.03.23 ...) is valid.
        o white
        o black
        o time (minutes) \_  used to set TimeControl field.
        o inc  (seconds) /  
        o wrating (both integers)
        o brating
        o moves = ['e4', 'e5', ...] alternatively a string 'e4 e5 Nf3'.
        o times = [12.3, 23.2] # time in seconds alternativelay '12.3 23.2 21.'
        o variant
        o result (can be float with 1.0 being 1-0, 0.5 being 1/2, etc. too)
        o longresult # Will be inserted as comment.
    
    This function does not support variations or such as it is. Any of the above
    infos can be left away.
    
    The format_time argument can be used to change how the time is printed.
        If set to None, it is ignored. Otherwise it must be a function returing
        the correct string when given the times (usually time in seconds as floats)
        as input. (ie. use fritz_time from this module). This function is given
        (move_time, total_time_used, time, inc) all in seconds. If you want
        to change the args of those functions, use lambdas or similar.
    
    If utc_tag is True, the times are added as UTC times too. If a string is given
        There is assumed to be no difference (a hint to clients), else, the
        .astimezone utc is used. You need to have pytz installed for this.
    
    elo is the string put to indicate the rating type. Because some programs
        might expect Elo, the default is here "Elo" making the tag WhiteElo and
        BlackElo. Practically this could be USCF or FICS as well though.
    
    max_width=80 is there so that we don't put all moves into one line.
    
    first_move_inc = False. This sets if after the first move a time increment
        was done or not. The format_time function will get the number of
        moves played. If first_move_inc is False (ie. FICS has this), the moves
        will be -1. In other words, both the first move and the second move
        are 1, as the second move saw up until then no increment just the like
        first move usually does. The number of increments done is thus always
        moves - 1.
    """

    result = info.get('result', '*')
    if type(result) is float:
        if result == 1.0:
            result = '1-0'
        elif result == 0.5:
            result = '1/2-1/2'
        elif result == 0.0:
            result = '0-1'
        else:
            result = '*'

    # List to add all the pgn lines.
    pgn = []
    if info.has_key('event') and info['event'] is not None:
        pgn.append('[Event "%s"]' % info['event'])
    elif info.has_key('tourney') and info['tourney'] is not None:
        pgn.append('[Event "%s"]' % info['tourney'])
    elif default_event is not None:
        pgn.append('[Event "%s"]' % default_event)
    
    if info.has_key('site') and info['site'] is not None:
        pgn.append('[Site "%s"]' % info['site'])
    elif default_site is not None:
        pgn.append('[Site "%s"]' % default_site)
   
    if info.has_key('round') and info['round'] is not None:
        pgn.append('[Round "%s"]' % info['round'])

    if info.has_key('time') and info.has_key('inc') and info['time'] is not None and info['inc'] is not None:
        pgn.append('[TimeControl "%i+%i"]' % (info['time']*60, info['inc']))

    if info.has_key('white') and info['white'] is not None:
        pgn.append('[White "%s"]' % info['white'])

    if info.has_key('black') and info['black'] is not None:
        pgn.append('[Black "%s"]' % info['black'])
    
    if info.has_key('wrating') and info['wrating'] is not None:
        pgn.append('[White%s "%s"]' % (elo, int(info['wrating'])))

    if info.has_key('brating') and info['brating'] is not None:
        pgn.append('[Black%s "%s"]' % (elo, int(info['brating'])))    

    if info.has_key('start_time') and info['start_time'] is not None:
        t = info['start_time']
        if type(t) is str or type(t) is unicode:
            t = t.split()[0].replace('-', '.')
        else:
            t = t.strftime('%Y.%m.%d')
        pgn.append('[Date "%s"]' % t)

    
    if info.has_key('start_time') and info['start_time'] is not None:
        t = info['start_time']
        if type(t) is str or type(t) is unicode:
            t = t.split()[1]
        else:
            t = t.strftime('%H:%M:%S')
        pgn.append('[Time "%s"]' % t)
    
    if utc_tag:
        if info.has_key('start_time') and info['start_time'] is not None:
            t = info['start_time']
            if type(t) is str or type(t) is unicode:
                t = t.split()[0].replace('-', '.')
            else:
                import pytz; utc = pytz.timezone('UTC')
                t = t.astimezone(utc).strftime('%Y.%m.%d')
            pgn.append('[UTCDate "%s"]' % t)
        if info.has_key('start_time') and info['start_time'] is not None:
            t = info['start_time']
            if type(t) is str or type(t) is unicode:
                t = t.split()[1]
            else:
                import pytz; utc = pytz.timezone('UTC')
                t = t.astimezone(utc).strftime('%H:%M:%S')
            pgn.append('[UTCTime "%s"]' % t)
    
    if info.has_key('variant') and info['variant'] is not None:
        v = info['variant']
        if v != 'blitz' and v != 'standard' and v != 'lightning' and v != 'bullet':
            pgn.append('[Variant "%s"]' % v)
    
    pgn.append('[Result "%s"]' % result)

    if info.has_key('fen') and info['fen'] is not None:
        pgn.append('[FEN "%s"]' % info['fen'])
    elif info.has_key('startpos') and info['startpos'] is not None:
        pgn.append('[FEN "%s w KQkq - 0 1"]' % info['startpos'])
    elif info.has_key('start_pos') and info['start_pos'] is not None:
        pgn.append('[FEN "%s w KQkq - 0 1"]' % info['start_pos'])

    
    pgn.append('') # blank line before we start adding moves.
    
    w_used = 0
    b_used = 0
    
    moves = info['moves']
    times = info['times']
    
    if moves:
        if type(moves) is str or type(moves) is unicode:
            moves = moves.split()
        if type(times) is str or type(times) is unicode:
            times = [float(time) for time in times.split()]
        
        l = []
        for i in xrange(len(moves)):
            if i % 2 == 0:
                l.append('%s. %s' % (i//2 + 1, moves[i]))
            else:
                l.append(moves[i])
            if i % 2 == 0:
                if times and format_time is not None:
                    w_used += times[i]
                    l.append('{%s}' % format_time(times[i], w_used, info.get('time', 0)*60, info.get('inc', 0), i//2 + 1 - first_move_inc))
            else:
                if times and format_time is not None:
                    b_used += times[i]
                    l.append('{%s}' % format_time(times[i], b_used, info.get('time', 0)*60, info.get('inc', 0), i//2 + 1 - first_move_inc))
        
               
        length = len(l[0])
        last = 0
        i = 1
        len_l = len(l)
        while i < len_l:
            length += len(l[i]) + 1
            if length > max_width:
                pgn.append(' '.join(l[last:i-1]))
                i -= 1
                last = i
                length = len(l[i])
            
            i += 1
        
        if last < len(l):
            pgn.append(' '.join(l[last:]))

    if info.has_key('longresult'):
        pgn.append('{%s} %s' % (info['longresult'], result))
    else:
        pgn.append('%s' % result)
    
    return '\n'.join(pgn)
