"""
Module to include a basic tell parsing functionality. As usually, it defines
the a register and unregister tell handlers.
"""

import os
import re

class PrivateTells(object):
    def __init__(self, icsbot=None, tell_logger=None):
        """Initialize Tells class with icsbot instance.
        
        (command_string, execution_function, priviledge_check=lambda *arg: True)
        
        Unregistering works via the command_string.
        
        Note:
            o The priviledge function will make a command invisible for all
                not allowed to use it.
            o If there is not helpfile for a command in the helpfile folder,
                the documentation of that function is used instead if it exists.
                In this case the priviledge of the user is checked as well!
                IMPORTANT: For correct printing the documentation must fullfill
                    the Docstring Conventions for good printing. (in owther
                    words, the last line is used to determine the size of
                    indent)
                
        For now no alias support, but of course completion.
        
        The class defines the two commands:
            o help -> get a helpfile from the help folder.
            o =commands -> list all commands available to a person.
        """

        self._registered = {'=commands': (self._listcommands, lambda *arg: True),
                            'help': (self._help, lambda *arg: True),
                            'next': (self._next, lambda *arg: True)}
        
        self.tell_logger = tell_logger
        self._icsbot = icsbot
        self._users = self._icsbot['users']
        
        import misc.regex as reg
        
        regex = '^(?P<handle>%s)(?P<tags>%s)? tells you: (?P<message>.*)$' % (reg.HANDLE, reg.TAGS)
        self._icsbot.reg_comm(regex, self)
        
        self.qtell = self._icsbot.qtell
        

    def __call__(self, match):
        """
        Call the instance with the mach object.
        """
        usr = self._users[match.group('handle')]
        tags = match.group('tags')
        # Get the message and strip it and split of the first argument.
        mess = match.group('message').strip().split(None, 1)
        
        if self.tell_logger is not None:
            self.tell_logger('%s%s tells you: %s\n' % (usr, tags, match.group('message')))
        
        comm = mess[0].lower()
        if len(mess) == 2:
            args = mess[1]
        else:
            args = ''
        
        #if len(comm) == 1:
        #    return self.qtell.split(usr, 'A command must be more then one character long.')
        
        matches = []
        for (c, v) in self._registered.items():
            f, p = v
            if c.startswith(comm) and p(usr, tags):
                if c == comm:
                    matches = [(c, f)]
                    continue
                matches += [(c, f)]
        if len(matches) > 1:
            to_tell = 'The following commands all match your input:\n'+'\n'.join((c for c, f in matches))
            return self.qtell.split(usr, to_tell)
        elif len(matches) == 0:
            return self.qtell.split(usr, 'No corresponding command found. Please use'\
                                    ' the =commands command to get a list of '\
                                    'all commands that are available to you. '\
                                    'Or try the helpfiles.')
        return matches[0][1](usr, args, tags)
        
    
    def register(self, command_str, function, priv=lambda *arg: True):
        """Register a function to be executed when the command_str fits.
        register(string, function, [check]), where function is the
        actual command, and check is a function to check wether a user
        is allowed to use the command. Gets:
           function(user, arguments, tags)
           check(user)
        Where tags is just a string so that handle+tags looks like it should.
        """
        self._registered[command_str.lower()] = (function, priv)
    
    
    def decorate(self, command_str, priv=lambda *arg: True):
        def newfunc(func):
            self.register(command_str, func, priv)
            return func
        return newfunc
    
    
    def _listcommands(self, usr, args, tags):
        """=commands lists all commands available to you."""
        commands = []
        for (c, v) in self._registered.items():
            f, p = v
            if p(usr, tags):
                commands += [c]    
        commands.sort()
        to_tell = 'The following commands are accesseble for you:\n' + '\n'.join(commands)
        return self.qtell.split(usr, to_tell)
        
        
    def _help(self, usr, args, tags):
        """Prints a helpfile.
        EXAMPLES:
            o help
            o help =commands
            o help help
        """
        args = args.strip()
        if not args:
            h = 'help_overview'
        else:
            h = args.split(None, 1)[0].lower()

        try:
            help_file = file('help'+os.path.sep+'%s.txt' % h)
        except IOError:
            if h in self._registered:
                if self._registered[h][0].__doc__ and self._registered[h][1](usr, tags):
                    s = self._registered[h][0].__doc__
                    res =  re.findall(re.compile('(\n\s*).*$'), s)
                    if res:
                        s = s.replace(res[0], '\n')
                    return self.qtell.split(usr, s.rstrip())
            return self.qtell.split(usr, 'Helpfile "%s" was not found' % h)
        
        return self.qtell.split(usr, help_file.read().rstrip())
        
    
    def _next(self, usr, args, tags):
        """The next command prints the next page for long output.
        """
        return self.qtell.send(usr)
