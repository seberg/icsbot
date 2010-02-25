"""Module for tell helper functions. Currently only includes the parse function.
"""
import re

def parse(string, short=False, argv_list=False, no_input=[]):
    """PARSING HELPER:
    
    If short=True the function will not look for -pa input, etc. -pa input
    will be considered as input and {p: [], a: []}, so that --pa option
    is necessary to get {pa: input}. (-- or - alone will give empty flag!)
    -pa will also not consider anything behind it. to be of importance then,
    but -p input will still be {p: input}
    
    Normally returns:([input, input, ...], {flag: [input, ...],
                                                   flag2: [input,...], ...})
    If argv_list, then it returns simply a list with literal strings parsed.
    
    It does recognice "asdf asdfasdf asdf" as one input string. Also "-a" would
    be seen as a string, and not a flag, so this is how to get around a - at
    the start. If you want to escape ", you can use \\".
    
    NOTE: This returns always empty lists, and not None (now.)
    """
    
    # Split to make sure that literal strings are taken as one.
    _re_str = re.compile(r"""((?:(?<!\\)".*?(?<!\\)")|(?:(?<!\\)'.*?(?<!\\)'))""")
    split = re.split(_re_str, string)
    
    argv = []
    is_raw = [] # True if string was inside of quotes.
    i = 0
    
    for spam in split:
        # if we got a literal string or not.
        if i%2 == 0:
            argv += spam.split()
            is_raw += [False] * len(spam.split())
        else:
            s = spam[1:-1]
            if s == '':
                continue
            argv.append(s)
            is_raw.append(True)
        i += 1
    
    if argv_list:
        return argv
    
    inputs = []
    flags  = {}
    
    # What we currently add stuff to.
    add_to = inputs
    
    argv_iter = argv.__iter__()
    is_raw_iter = is_raw.__iter__()
    while True:
        try:
            curr = argv_iter.next()
            raw = is_raw_iter.next()
        except StopIteration:
            break
        
        if raw:
            add_to.append(curr)
        elif curr.startswith('--') and len(curr)>=3:
            if curr[2:] in no_input:
                flags[curr[2:]] = []
            elif flags.has_key(curr[2:]):
                add_to = flags[curr[2:]]
            else:
                flags[curr[2:]] = []
                add_to = flags[curr[2:]]

        elif curr.startswith('-') and len(curr)>=2 and curr[1] != '-':
            if short and len(curr)>2:
                for i in curr[1:]:
                    flags[i] = []
            else:
                if curr[1:] in no_input:
                    flags[curr[1:]] = []
                elif flags.has_key(curr[1:]):
                    add_to = flags[curr[1:]]
                else:
                    flags[curr[1:]] = []
                    add_to = flags[curr[1:]]
        else:
            add_to.append(curr)
    
    return inputs, flags
