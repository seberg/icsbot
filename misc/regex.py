"""Module solely to store some regexes in to help parsing for the command
Instances. Maybe some more to follow ...
"""

import re

HANDLE  = r'[a-zA-Z]{3,17}'
CHANNEL = r'\(\d{1,3}\)'
GAME    = r'\[\d+\]'
TAGS    = r'(?:\([A-Z*]{1,2}\))*'
STYLE12_re = re.compile(r'^(?:(?P<spam>.+?)\n\r)?(?:\x07\n\r)?<12> (?P<position>(?:[-A-Za-z]{8,8} ){8,8})(?P<to_move>(?:B|W)) (?P<ep_file>(?:-1|[1-8])) (?P<w_k_castle>(?:0|1)) (?P<w_q_castle>(?:0|1)) (?P<b_k_castle>(?:0|1)) (?P<b_q_castle>(?:0|1)) (?P<irr_ply>\d+) (?P<game>\d+) (?P<white>[a-zA-Z]{3,17}) (?P<black>[a-zA-Z]{3,17}) (?P<relation>-?\d) (?P<time>\d+) (?P<inc>\d+) (?P<w_material>\d+) (?P<b_material>\d+) (?P<w_time>\d+) (?P<b_time>\d+) (?P<move_num>\d+) (?P<move_coord>[^ ]+) \((?P<move_time>(\d+:)+[.\d]+)\) (?P<move_san>[^ ]+) (?P<flip>(?:0|1)) (?P<clock_running>(?:0|1)) (?P<lag>\d+)(?:\n\r<b1> game \d+ white \[(?P<white_stack>[A-Za-z]*)\] black \[(?P<black_stack>[A-Za-z]*)\])?(?:\n\r\n\rGame \d+: (?P<longresult>[a-zA-Z ]*) (?P<result>(?:0-1|1-0|1/2-1/2|\*)))?$', re.DOTALL)
