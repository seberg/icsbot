#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""The eco.txt is from: http://www.geocities.com/siliconvalley/lab/7378/eco.htm
"""

try:
    import cPickle as pickle
except ImportError:
    import pickle

import re

ecos_txt = file('eco.txt')

ecos = []
eco_dict = {}
for eco in ecos_txt:
    l = eco.split('\t')
    if not l[0]:
        break
    ecos.append([l[0].strip(), l[1].strip(), l[2].strip()])
    
ecos.insert(0, ['***', 'No moves, or not chess.', ''])

number = re.compile('\d+\.')
move_reg = re.compile('([a-hBNKQPRx@+#=1-8O-]+)')

tree = {}

prev_eco = None

for eco in ecos:
    if prev_eco == eco[0]:
        prev_var += 1
    else:
        prev_eco = eco[0]
        prev_var = 0
        eco_dict[eco[0]] = []
    
    moves = number.sub('', eco[2])
    moves = move_reg.findall(moves)
  
    eco[2] = moves
    code = eco[0] + '.%s' % prev_var

    eco_dict[eco[0]].append((code, eco[1], eco[2])) 
        
    branch = tree
    for move in moves:
        if branch.has_key(move):
            branch = branch[move]
        else:
            branch[move] = {}
            branch = branch[move]
    if branch.has_key(None):
        branch[None].append((code, eco[1]))
    else:
        branch[None] = [(code, eco[1])]

pickle.dump(('This eco was created from http://www.geocities.com/siliconvalley/lab/7378/eco.htm, it includes %s codes' % (len(ecos)-1), tree, eco_dict), file('eco.dat', 'w'))
