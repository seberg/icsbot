import gc

def _freeze_gc(func):
    """Decorator function to freeze the garbage collector if it was enabled.
    THIS SHOULD BE NOT NEEDED, AND INDEED I CANNOT REPRODUCE BUG RIGHT NOW.
    MAYBE CHECKED NOT ENOUGH THEN, OR BUGGY PYTHON.
    """
    def new_func(*args, **kwargs):
        status = gc.isenabled()
        gc.disable()
        output = func(*args, **kwargs)
        if status is True:
            gc.enable()
        return output
    return new_func

class _Item(object):
    """
    ITEM (USER) OBJECT. Do not create directly, only use it through the
     Data class!
        o item is a dictionary with currently set values. You can use this to:
            1. Circumvent all other checks ;) (other functions watching/setting)
            2. To edit a fields entry instead of setting it to a copy of itself
                (ie. I use this in the qtells class where the item is an
                iterator)
            3. To use with registered functions to set the value to something
                other then what was specified by the user. (see also Users)
        
    ARBITRARY ITEMS:
        o Go ahead and add any items you want to store on a user (like qtell
           does for example). BUT: info gets usually deleted on disconnect,
           and make sure not to conflict with other things, also an item might be
           dropped. So if you must be sure, buffer the parent so that the weakref
           won't drop it.
           
    NOTE:
        Items are weakrefed, however during __getitem__, __setitem__ and __delitem__
        operations which can trigger other things, the garbage collector is disbabled.
        This should make it save if a dataitem is temporarily unrefed.
    """    
    
    main_key = 'handle'

    ### Init and other functions:    
    
    def __init__(self, handle):
        # Note, do not load lots of things here. We want to load them
        # dynamically.
        
        self.items = {}
        self.items[self.main_key] = handle
     
        # Dictionary item -> [function, ...] to execute functions when the item
        # is updated. Use register(item, function) to use this.
        self._on_update = {}
        self.loader = {}


    def __str__(self):
        return str(self.items[self.main_key])
    
    def load(self, item):
        """
        load(item). This sets the item to its special _item_get function value.
        If this function does not exist, the item is deleted. The function
        does return the new value or None.
        """
        try:
            self.__class__._loader[item](self, item)
        except KeyError:
            pass
                    

    def register(self, item, function, persistent=False):
        """
        register(item, function, persistent=False, loader=False)
        Register a function to be executed when item gets updated next time.
        Multiple functions can be registered, all will update when this happens.
        NOTES:
            o Function must take (user_object, item_name, old, new) as arguments.
            o Do not mass use this, otherwise its probably better to
               add it to the _item_set()/_item_load() special function.
        """

        if self._on_update.has_key(item):
            self._on_update[item] += [[function, persistent]]
            return
        self._on_update[item] = [[function, persistent]]
        

    def unregister(self, item, function):
        """
        Unregister a function again ...
        """
        try:
            self._on_update[item].remove([function, True])
        except ValueError:
            self._on_update[item].remove([function, False])


    # Item setting base functions:
    
    def get(self, item, default=None):
        """
        get(item, [default]):
        Same as user[item]. Be _careful_ about defaults. With sql backend
        the backend would store None in any case just to make sure its not
        loaded again.
        """
        return self.__getitem__(item, default)

    @_freeze_gc
    def __getitem__(self, item, default=None):
        """Returns the item. (After loading it if necessary.)
        Be careful about editing the item. As this editing might be in place,
        nothing will be triggered in that case.
        """
        if self.items.has_key(item):
            return self.items[item]

        try:
            self.__class__._loader[item](self, item)
        except KeyError:
            pass
        
        return self.items.get(item, default)
    
    
    def has_key(self, item):
        """Return True if the item either is already set, or there is a loader
        for it.
        """
        return self.items.has_key(item) or item in self.loader or item in self.__class__._loader
    
    
    def copy(self):
        """Return a copy of the currently stored values. (This is a dictionary)
        """
        return self.items.copy()
    
    def reset(self, item):
        """
        Calls the current _loader handler on the item. If none is defined
        delete the item.
        """
        try:
            self.__class__._loader[item](self, item)
        except KeyError:
            pass
    
    
    @_freeze_gc
    def __setitem__(self, item, new):
        """
        Set the value of the specific item, or execute the special function
        and set the value to its result.
        """
        try:
            old = self.items[item]
        except KeyError:
            old = None

        # Should be able to store it as None, even if we default to None.
        self.items[item] = new
        if old == new:
            return

        if self.__class__._on_update.has_key(item):
            to_del = []
            for function, pers in self.__class__._on_update[item]:
                if not pers:
                    to_del += [function]
                function(self, item, old, new)
        

            for function in to_del:
                self.__class__._on_update[item].remove([function, False])
        
            if not self.__class__._on_update[item]:
                del self.__class__._on_update[item]
        
        if self._on_update.has_key(item):
            to_del = []    
            for function, pers in self._on_update.get(item, []):
                if not pers:
                    to_del += [function]
                function(self, item, old, new)    

            for function in to_del:
                self._on_update[item].remove([function, False])
        
            if not self._on_update[item]:
                del self._on_update[item]        
    
    
    @_freeze_gc
    def __delitem__(self, item):
        """Delete the specific item or execute the special function for it and then
        delete it. (Do nothing if item doesn't exist).
        """
        if not self.items.has_key(item):
            return

        del self.items[item]

        for function in self.__class__._on_update.get(item, []):
            function(self, old, None)
        
        for function in self._on_update.get(item, []):
            function(self, old, None)



################################################################################
    
class Data(object):
    """
    Class to handle Data, especailly Users:
      Data[item] -> returns a item object.
    If item is a string, it is case insensitive, but item can be anything.
    The item is stored as "handle" into the Item object, probably often
    just flying around, sometimes meaning you have double entries (with db).
      
    You can change self.main_key to change the default item to a name 
    different from 'handle'. For example the ID in the database, or whatever.
      
    AS USER IS THE MAIN INTEREST, ALL HELP MAY REFER TO Users==Data
    and User == Item!
    
    Other things (ie, users.online) are added from outside.
      
    NOTES:
        o Use Registered functions to add functionality to user class.
           The registered function can change the items value by directly
           editing the User.items dictionary.
        o Registered functions are executed in the order that they are
           gotten. Classes ones are executed before Instance ones, so that
           they could modify the value before the instance thinks it changed.
           Instance ones _will_ also be executed if old == new.
    
    TIPS:
        o Instead of registering say "rating" which would be set when a
           function parsed the finger of a user, have it set
           "finger_update" = time.time() and register to that. That way you
           get notified even if the rating does not change AND always know
           when it was last updated.
        o For the same example, you might have a loader regestration for your
           database backend. The status module will set the items, but if a
           user is not connected, he does not have it set, so that loader
           gets called when you cannot get it through FICS. Yes, that means
           that you will need the dummy "finger_update" to force a reload
           through the finger function. (Of course this is rather
           hypethetical, afterall finger is always more up to date ;))
           
    Maybe the buffer should be improved ...
    """

    def __init__(self, main_key='handle', buffer_size = 20):
        # Define a dummy class and self.Item to make sure that each Users class
        # has its own child User class.
        class Items(_Item):
            _on_update = {}
            _loader = {}

        self.main_key = main_key
        Items.main_key = main_key
        self.Item = Items

        # Buffer to make sure we don't discard items that often ...
        # As long as the item has a reference stored here or ANYWHERE else
        # he will not be discarted.
        if buffer_size < 1:
            self._buffer = None
        else:
            self._buffer = [None]*buffer_size

        # dictionary mapping item_name -> item object. This is a WEAKREF!
        from weakref import WeakValueDictionary
        self._loaded_items = WeakValueDictionary()
    

    def register(self, item, function, persistent=True, loader=False):
        """
        register(item, function, persistent=True)
        Register a function to be executed when item gets updated next time.
        Multiple functions can be registered, all will update when this happens.
        NOTES:
            o Function must take (item_object, item_name, old, new) as arguments.
            o Do not mass use this, otherwise its probably better to
               add it to the _item_set()/_item_load() special function.
            o loader keyword: The funciton is not called on set, but on a
               get event. (First time load). Only one function can be
               assigned. quietly overwrites all existing ones.
               Always persistent. The function MUST set the item.
        This will register for ALL items.
        """
        if loader == True:
            self.Item._loader[item] = function
            return
            
        if self.Item._on_update.has_key(item):
            self.Item._on_update[item].append([function, persistent])
            return
        self.Item._on_update[item] = [[function, persistent]]

    
    def unregister(self, item, function, loader):
        """
        Unregister a function again ...
        """
        if loader:
            del self.Item._loader[item]
            return
        try:
            self.Item._on_update[item].remove([function, True])
        except ValueError:
            self.Item._on_update[item].remove([function, False])


    def __getitem__(self, handle):
        try:
            ident = handle.lower()
        except AttributeError:
            ident = handle
        if not self._loaded_items.has_key(ident):
            return self._load(handle)
        #print handle, ident, self._loaded_items[ident].items
        return self._loaded_items[ident]


    def _load(self, handle):
        new_item = self.Item(handle)
        try:
            ident = handle.lower()
        except AttributeError:
            ident = handle
        
        self._loaded_items[ident] = new_item
        if self._buffer is not None:
            del self._buffer[0]
            self._buffer += [new_item]
        return new_item        


    def iteritems(self):
        """Iterator over all stored items.
        """
        return self._loaded_items.iteritems()
        
    def iterkeys(self):
        """Iterator over all stored keys.
        """
        return self._loaded_items.iterkeys()

    def itervalues(self):
        """Iterator over all stored items.
        """
        return self._loaded_items.itervalues()

    def __iter__(self):
        return self._loaded_items.__iter__()
