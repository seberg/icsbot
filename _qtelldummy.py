"""
This is a Qtell replacement module.
"""
class QtellDummy():
    """
    This is a simple class to provide functionality/compatibility if qtells are
    not available.
    
    It does not provide such a fancy things as Qtell. Does NOT provide the next
    function.
    """
    def set_header(self, header):
        self.width = 170
        pass

    def __call__(self, user, data):
        return self.split(user, data)

    def split(self, usr, data):
        data = data.split('\n')
        
        new_data = []
        
        for line in data:
            for i in xrange(0, len(line)/self.width + 1):
                new_data += [line[self.width*i: self.width*(i+1)]]
        
        handle = usr['handle']
        return ('tell %s %s' % (handle, line) for line in new_data)
        
    
    def send(self, usr):
        return 'tell %s Next command not available in qtell_dummy mode. This bot probably has no qtell rights. If you did not use next, the programmer did something weird ...' % usr['handle']
    
    
    def send_list(self, usr, data):
        new_data = []
        for split in (i.split('\n') for i in data):
            new_data += split
        
        handle = usr['handle']
        return ('tell %s %s' % (handle, line) for line in new_data)
    
    
