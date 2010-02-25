"""
Provides a functionf or simple tables.
"""
import string
def table(data=[], *args):
	"""
	data = [[row1col1, row1col2, col3], [row2col1, ...]]
	Args should be always a tuple of:
	(Heading, adjustment (r|l|c), width)
	"""
	just = {'r': string.rjust, 'l': string.ljust, 'c': string.center}

	lin = []
	ins = []
	header = []
	for i in args:
		lin += ['-' * i[2]]
		header += [just[i[1]](i[0], i[2])]

	lin = '+-%s-+' % '-+-'.join(lin)
	ins = '| %s |' % ' | '.join(['%s']*len(args))
	
	t = [lin] + [ins % tuple(header)] + [lin]
	
	t += (ins % tuple(just[i[1]](str(col), i[2]) for (col, i) in zip(row, args)) for row in data)
	t += [lin]
	return t
