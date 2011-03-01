"""
This module is designed to create and handle Qtells send by a bot. The basic
usage is using the functions:

split -> To send a text as wrapped Qtell, that will fit within WIDTH=79
          characters width. (Unless you want the user to change width, I
          advise to keep it at 79.)
          
__call__ -> Same as split.

send_list -> In case you already got a list of lines to send and don't want
          the module to handle splitting it down. (No extra newlines please.)

send -> To send any buffered text, that has not been send yet (Too high.)

clear -> Clear the buffer of things not send to a certain user.
          (The user module will clear variables of offline users automatically,
          so you can use this to clear, but no need to worry really)

There are the two variables _HEADER and NEXT_NOTE, which are strings to
go before any Qtell (HEADER) or after it if not all was shown. Note that
HEADER should include one newline (Its send seperatly, so one is always
included).
Use set_header(string) to change the header. Newlines will be replaced
correctly.

All sending things support use_next, so you can have it ignore the height.
(set it to 9999 for that qtell.)
"""

try:
    import unidecode as _unidecode
except:
    print 'No unidecode found, will not try to transliterate utf-8'
    print 'To get unidecode search for it on pypi, this function is not needed!'
    _unidecode = None


class Qtell(object):
    _HEADER_LEN = 0
    NEXT_NOTE = '\\nPlease tell me next to get more.'
    _HEADER = None
    
    def __init__(self, height=25, width=78, header=None, users=None):        
        self.WIDTH = width
        self.HEIGHT = height
        self.users = users
        
    
    def set_header(self, header):
        if not header:
            self.__class__._HEADER = None
            return
        self.__class__._HEADER = header.replace('\n', '\\n')
        if not self._HEADER:
            _HEADER_LEN = 0
        else:
            _HEADER_LEN = 1 + self.__class__._HEADER.count('\\n')
    
    
    def set_next_note(self, next):
        self.__class__.NEXT_NOTE = next
    
    
    def clear(self, user):
        """
        Arbitrary command that just deletes the users qtell_buffer.
        """
        del user['qtell_buffer']


    def __call__(self, user, data, use_next=True):
        return self.split(user, data, use_next=use_next)


    def split(self, user, data, use_next=True, transliterate=False):
        """
        split(handle/user, data). Returns same as send(handle/user) which
        gives a generator object over things that need to be send to FICS.
        """
        if type(data) != unicode:
            data = unicode(data, 'utf-8')
        if transliterate and _unidecode is not None:
            # Make sure we have unicode
            data =  _unidecode.unidecode(data.encode('utf-8').decode('utf-8'))
        
        lines = self._auto_split(data)
        if type(user) is str:
            if self.users is None:
                raise TypeError('Must give a user type not a string, or init qtell with users.')
            user = self.users[user]

        # Would be cool to make _auto_split work on iterators too.
        user['qtell_buffer'] = (i for i in lines)
        return self.send(user, use_next=use_next)
            
            
    def _auto_split(self, text):
        if type(text) != unicode:
            text = unicode(text, 'utf-8')
        parts = text.split('\n')
        lines = []
        for part in parts:
            part = part.strip('\r')
            
            words  = part.split(' ')
            line_length = 1
            line = []
            # append first word, so its not indented.
            line.append(words[0])
            line_length += len(words[0])
            del words[0]

            for word in words:
                line_length += len(word) + 1    # add word and whitespace in front

                # maximum length WIDTH, at least one word (this will look ugly, but I don't care)
                if line_length <= self.WIDTH or len(line) == 0:
                    line.append(' ')
                    line.append(word)    # append the word.
                else:
                    lines.append('%s' % ''.join(line).strip())

                    line_length = 1
                    line = ['']
                    line.append(word)
                    line_length += len(word)
        
            if len(line) > 0:
                lines.append('%s' % ''.join(line))
        
        return lines


    def send_list(self, user, data, use_next=True, transliterate=False):
        """
        send_list(handle/user, data (list/iterator of strings))
        Accepts a list of strings and replaces all \\n's with \\\\n's and returns
        a generator (same as send(handle, height)) over it.
        NOTE: Using newlines in send_list is BAD. It will confuse the height.
        """
        data = (i.replace('\n', '\\n') for i in data)
        if type(user) is str:
            user = users[user]
        
        if transliterate and _unidecode is not None:
            # Transliterate all:
            data = (_unidecode.unidecode(unicode(i, 'utf-8')) for i in data)
        
        user['qtell_buffer'] = data
        return self._send(user, use_next=use_next)


    def send(self, user, use_next=True):
        """
        send(handle/user). Returns a generator object over all things
        that need to be send.
        """
        return self._send(user, use_next=use_next)


    def _send(self, user, use_next=True):
        # Take the users height settings and HEIGHT if not set.
        height = user['height'] or self.HEIGHT
        if use_next == False:
            height = 9999 # a large number ...
        
        handle = user['handle']
    
        totell = ['qtell %s ' % handle]
        lines_sent = 0
        length = 0
    
        if self._HEADER:
            length += len(self._HEADER) + 2
            lines_sent += self._HEADER_LEN
            totell.append(self._HEADER)
            totell.append('\\n')
            first = True
        else:
            first = False
        
        if not user.items.has_key('qtell_buffer') or not user.items['qtell_buffer']:
            yield 'qtell %s Nothing more to show.' % user['handle']
            return
        
        # Careful, qtell_buffer is an iterator, not a list, accessing directly here.
        for line in user.items['qtell_buffer']:
            if type(line) is unicode:
                # If we encode as utf-8, the len function will return the byte
                # length we need for this function.
                line = line.encode('utf-8')
            
            length += len(line) + 2
        
            # 999 to make sure that it cannot be longer then 1024 characters.
            if length > 999:
                yield ''.join(totell[:-1])
                first = False
                length = len(line) + 2 
                totell = ['qtell %s ' % handle]

            totell.append(line[0:999])
            totell.append('\\n')
            lines_sent += 1

            if lines_sent >= height:
                break
    
        try:
            line = user.items['qtell_buffer'].next()
        except StopIteration:
            del user['qtell_buffer']
            yield ''.join(totell[:-1])
            return    
    
        # I hope this is not too ugly a hack just for using generators.
        def new_iter(i, j):
            yield i
            while True:
                yield j.next()
    
        user.items['qtell_buffer'] = new_iter(line, user.items['qtell_buffer'])
    
        totell = ''.join(totell[:-1])
        if len(self.NEXT_NOTE) + len(totell) +2 <= 1024:
            yield '%s\\n%s' % (totell, self.NEXT_NOTE)
        else:
            yield totell
            yield 'qtell %s %s' % (handle, self.NEXT_NOTE)
