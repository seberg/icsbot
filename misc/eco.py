"""
"""

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    info, tree, ecos  = pickle.load(file('eco.dat'))
except:
    raise ImportError('Failed to load eco.dat, please create it with create_eco_dat.py')

def from_moves(moves):
    """Returns a list of tuples
    (ECO code, Name). The ECO code is A00.0 for example, appended number is to
    ensure that all ECO codes given are unique. There are fiew openings with
    two names (and two extension numbers), but you can just use the first
    result of the list.
    
    An opening without any matches is considered "***", "No moves or not chess."
    
    moves can be a (unicode) string or an iterable.
    """
    if type(moves) is str or type(moves) is unicode:
        moves = moves.split()
    
    branch = tree
    prev = branch[None]
    for move in moves:
        if branch.has_key(move):
            branch = branch[move]
            if branch.has_key(None):
                prev = branch[None]
        else:
            return prev
    
    return prev
    

def eco(code):
    """Return the information on an eco, or return a list of all ecos, ordered
    by variation number.
    """
    code = code.split('.')
    if len(code) == 1:
        return ecos[code[0]]
    else:
        return ecos[code[0]][int(code[1])]
