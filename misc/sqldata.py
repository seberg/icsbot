import pysqlite2.dbapi2 as db

class SqlData(object):
    """
    This class provides a simple database backend to store flat values
    of a icsbot[dataset] dataset into a sqlite3 databse.
    
    TO USE A DIFFERENT DATABAES ENGINE, YOU _SHOULD_ JUST HAVE TO
    IMPORT A DIFFERENT MODULE.
    """
    
    def __init__(self, database=None, dataset=None, table=None, joins='', columns='*', join_columns='', lower_ext='_lower', load_all=True):
        """Initialize a class giving it a database='icsbot.db', the dataset
        (an icsbot[dataset] object.) the table=tablename, which should
        be the datasets name for simplicity.
        The class will make sure that all values gotten are gotten from the
        db, and all values changed, are stored to the db.
        
        'rowid' is the always the row of the database entry. To get all
        entries loaded at once, load 'rowid' and it will happen.
        
        KWARGS:
            database = Database to use. Either string, or open connection.
            dataset  = dataset to work with. (IcsBot[dataset] dataset.)
            table    = name of the table.
            load_all = If we should always load all columns. (default: True
                         Other not tested.)
        
        Also defines icsbot[dataset].sql to be this connection class making
        icsbot[dataset].sql.cursor and icsbot[dataset].sql.cursor.dcursor
        available to you. (dcursor is a dictionary cursor)
        
        NOTE: 
            o If there is a column named <main_key>_lower this is used for
                comparisons (or some other lower_ext)
            o You only use this for simple things like strings or numbers
                stored on the user.
            o The column/item rowid is reserved.
            o Load all ONLY makes a rowid event, others won't get events!!!
            o I will automatically get all the necessary items from the table.
            o The class will never create a new entry in the database when
                something is set to a _new_ value.
            o You can define join_columns and joins. Joins will be inserted
                into the SQL and should be "LEFT JOIN ...", join_columns should
                be all the columns you want to extract from joined tables.
                These are read only! If you give joins, you must also
                give columns.
        """

        assert dataset, 'No dataset=icsbot dataset item given.'
        assert table, 'Must give table=tablename string.'
        if joins != '' and (columns == '*' or join_columns==''):
                assert False, 'If joins are given, columns and join_columns must be specified.'
        
        if join_columns:
            self.all_columns = columns + ', ' + join_columns
        else:
            self.all_columns = columns
        self.columns = columns
        self.join_columns = join_columns
        
        self.table = table
        self.table_joins = table + ' ' + joins
        
        self.dataset = dataset
        self.main_key = dataset.main_key

        if type(database) is str or type(database) is unicode: 
            self.db = db.connect(database)
        else:
            self.db = database
        
        # Setting autocommit. No idea if this is actually good or not :)
        self.db.isolation_level = None
        
        self.cursor = self.db.cursor()

        stored = self.cursor.execute('SELECT %s.rowid as rowid, %s FROM %s LIMIT 0' % (self.table, self.all_columns, self.table_joins))
        self.store_values = set([col[0] for col in stored.description])
        
        if self.main_key + lower_ext in self.store_values:
            self.main_key_lower = self.main_key + lower_ext
            self.store_values.remove(self.main_key_lower)
            self.lower = True
        else:
            self.lower = False
        
        if self.join_columns:
            stored = self.cursor.execute('SELECT %s FROM %s LIMIT 0' % (self.join_columns, self.table_joins))
            self.joined_values = [col[0] for col in stored.description]
        else:
            self.joined_values = []
        
        # Snipplet from the pysqlite user guide so I can have a dictionary
        # cursor:
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
    
        self.db.row_factory = dict_factory
        self.dcursor = self.db.cursor()

        # Register with the values:
        if not load_all:
            for value in self.store_values:
                self.dataset.register(value, self._item_changed)
                self.dataset.register(value, self._load_item, loader=True)
        else:
            for value in self.store_values:
                self.dataset.register(value, self._item_changed)
                self.dataset.register(value, self._load_all, loader=True)        
        
        self.store_values.remove(self.main_key)
        self.dataset.register('rowid', self._load_all, loader=True)
        self.dataset.sql = self
        
    
    def _load_item(self, data_set, item):
        assert item not in self.joined_values, 'The item loaded directly cannot be from a joined table unfortunatly.'
        if not self.lower:
            self.cursor.execute('SELECT %s.%s from %s WHERE %s.%s=?' % (self.table, item, self.table_joins, self.table, self.main_key), (data_set.items[self.main_key],))
        else:
            self.cursor.execute('SELECT %s.%s from %s WHERE %s.%s=?' % (self.table, item, self.table_joins, self.table, self.main_key_lower), (data_set.items[self.main_key].lower(),))
        
        result = self.cursor.fetchone()
        if not result:
            # We set it to None anyways, so that we don't have to worry about
            # it being loaded too often. Set items that are not yet set.
            # If it exists, we don't want to overwrite it just in case.
            if not data_set.items.has_key(item):
                data_set.items[item] = None
            return

        data_set.items[item] = result[0]
        
        
    def _load_all(self, data_set, item=None):
        if not self.lower:
            self.dcursor.execute('SELECT %s.rowid as rowid, %s FROM %s WHERE %s.%s=?' % (self.table, self.all_columns, self.table_joins, self.table, self.main_key), (data_set.items[self.main_key],))
        else:
            self.dcursor.execute('SELECT %s.rowid as rowid, %s FROM %s WHERE %s.%s=?' % (self.table, self.all_columns, self.table_joins, self.table, self.main_key_lower), (data_set.items[self.main_key].lower(),))
        data = self.dcursor.fetchone()
        if not data:
            # We need to fill it up with None in any case, so that we don't
            # load it again lateron.
            data_set.items.update((key, None) for key in self.store_values)
            data_set.items['rowid'] = None
            return
            
        # Remove rowid, so that changing it will create an event.
        id_ = data.pop('rowid')
        
        data_set.items.update(data)
        data_set.items['rowid'] = id_
        
    
    def _item_changed(self, data_set, item, old, new):
        # Dummy check in case I change internal API of the _data.Item.
        if old == new:
            return
        
        if item in self.joined_values:
            TypeError('The item is not a native Item for the database, and thus cannot be changed.')
        
        if item == self.main_key:
            if self.lower:
                if old.lower() != new.lower():
                    TypeError('The main key of a table may not be changed.')
            else:
                TypeError('The main key of a table may not be changed.')
        
        # This is some fun. If someone changes something that the database should
        # be storing, we assume the item should be added.
        # THIS CAN DO SERIOUS CRAP IF YOU ARE NOT CAREFUL, ie in status
        # there was user['handle'] = handle. Creating an event and storing here.
        if not self.lower:
            self.cursor.execute('SELECT count(*) FROM %s WHERE %s.%s=?' % (self.table_joins, self.table, self.main_key), (data_set[self.main_key],))
        else:
            self.cursor.execute('SELECT count(*) FROM %s WHERE %s.%s=?' % (self.table_joins, self.table, self.main_key_lower), (data_set[self.main_key].lower(),))
        c = self.cursor.fetchone()
        
        if c[0] == 0:
            if not self.lower:
                self.cursor.execute('INSERT INTO %s (%s, %s) VALUES (?, ?)' % (self.table, self.main_key, item), (data_set[self.main_key], new))
            else:
                self.cursor.execute('INSERT INTO %s (%s, %s, %s) VALUES (?, ?, ?)' % (self.table, self.main_key_lower, self.main_key, item), (data_set[self.main_key].lower(), data_set[self.main_key], new))
            # we need to reload rowid, etc. becuase we got now default values.
            self._load_all(data_set)
            return False
        elif c[0] != 1:
            assert 'More then one match in database, this should be impossible.'
        
        if not self.lower:
            self.cursor.execute('UPDATE %s SET %s=? WHERE %s=?' % (self.table, item, self.main_key), (new, data_set[self.main_key]))
        else:
            self.cursor.execute('UPDATE %s SET %s=? WHERE %s=?' % (self.table, item, self.main_key_lower), (new, data_set[self.main_key].lower()))
        # We reload all the info, just in case.
        self._load_all(data_set)
        
        
