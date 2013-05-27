# -*- coding: utf-8 -*-

"""
allows apptools models to be efficiently
stored in and retrieved from redis.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# adapter API
from . import abstract
from .abstract import ModelAdapter

# apptools util
from apptools.util import json
from apptools.util import decorators

# resolve msgpack
try:
    import msgpack
except ImportError as e:  # pragma: no cover
    _MSGPACK = False  # indicate no msgpack support
else:  # pragma: no cover
    _MSGPACK = True  # indicate msgpack support

# resolve redis
try:
    ## force absolute import to avoid infinite recursion
    redis = _redis_client = __import__('redis', locals(), globals(), [], 0)
except ImportError as e:  # pragma: no cover
    _REDIS, _redis_client, redis = False, None, None
else:
    _REDIS = True

# resolve gevent
try:
    import gevent
except ImportError as e:  # pragma: no cover
    _GEVENT = False
else:
    _GEVENT = True
    if _REDIS and hasattr(redis.connection, 'socket') and hasattr(gevent, 'socket'):
        ## with Redis AND gevent, patch the connection socket / pool
        redis.connection.socket = gevent.socket


## Globals / Constants
_server_profiles = {}  # holds globally-configured server profiles
_default_profile = None  # holds the default redis instance mapping
_client_connections = {}  # holds instantiated redis connection clients
_profiles_by_model = {}  # holds specific model => redis instance mappings, if any


## RedisMode
# Enumerates available storage modes.
class RedisMode(object):

    ''' Map of hard-coded modes of internal operation for the `RedisAdapter`. '''

    hashkey_hash = 'hashkey'  # HSET <key>, <field> => <value> [...]
    hashkey_blob = 'hashblob'  # HSET <entity_group>, <key_id>, <entity>
    hashkind_blob = 'hashkind'  # HSET <kind>, <key_id>, <entity>
    toplevel_blob = 'toplevel'  # SET <key>, <entity>


## RedisAdapter
# Adapt apptools models to Redis.
class RedisAdapter(ModelAdapter):

    ''' Adapt model classes to Redis. '''

    # key encoding
    adapter = _redis_client
    connection_spec = None
    _config_path = 'apptools.model.adapters.redis.Redis'

    # magic string identifiers
    _id_prefix = '__id__'
    _meta_prefix = '__meta__'
    _kind_prefix = '__kind__'
    _magic_separator = '::'

    ## EngineConfig
    # Holds hard-coded configuration values for the `RedisAdapter` engine.
    class EngineConfig(object):

        ''' Configuration for the `RedisAdapter` engine. '''

        encoding = True  # encoding for keys and special values
        compression = False  # compression for serialized data values
        mode = RedisMode.toplevel_blob  # internal mode of operation

    ## Operations
    # Holds bound names for available Redis operations.
    class Operations(object):

        ''' Available datastore operations. '''

        ## Key Operations
        SET = 'SET'  # set a value at a key directly
        GET = 'GET'  # get a value by key directly
        KEYS = 'KEYS'  # get a list of all keys matching a regex
        DUMP = 'DUMP'  # dump serialized information about a key
        DELETE = 'DELETE'  # delete a key=> value pair, by key
        GETBIT = 'GETBIT'  # retrieve a specific bit from a key value
        GETSET = 'GETSET'  # set a value by key, and return the existing value at that key
        GETRANGE = 'GETRANGE'  # return the substring of str value at given key, determined by offsets

        ## Counter Operations
        INCREMENT = 'INCR'  # increment a key (`str` or `int`) by 1
        DECREMENT = 'DECR'  # decrement a key (`str` or `int`) by 1
        INCREMENT_BY = 'INCRBY'  # increment a key (`str` or `int`) by X
        DECREMENT_BY = 'DECRBY'  # decrement a key (`str` or `int`) by X
        INCREMENT_BY_FLOAT = 'INCRBYFLOAT'  # incremement a key (`str` or `int`) by X.X

        ## Hash Operations
        HASH_SET = 'HSET'  # set the value of an individual hash field
        HASH_GET = 'HGET'  # get the value of an individual hash field
        HASH_KEYS = 'HKEYS'  # get all the property names in a hash
        HASH_DELETE = 'HDEL'  # delete one or more individual hash fields
        HASH_LENGTH = 'HLEN'  # retrieve the number of fields in a hash
        HASH_VALUES = 'HVALS'  # get all values in a hash, without keys
        HASH_EXISTS = 'HEXISTS'  # determine if an individual hash field exists
        HASH_GET_ALL = 'HGETALL'  # get all fields and values of a hash
        HASH_SET_SAFE = 'HSETNX'  # set the value of a hash field, only if it doesn't exist
        HASH_MULTI_GET = 'HMGET'  # get the values of multiple hash fields
        HASH_MULTI_SET = 'HMSET'  # set the values of multiple hash fields
        HASH_INCREMENT = 'HINCRBY'  # increment an individual hash field by X
        HASH_INCREMENT_FLOAT = 'HINCRBYFLOAT'  # increment an individual hash field by float(X)

        ## String Commands
        APPEND = 'APPEND'  # append string data to to an existing key
        STRING_LENGTH = 'STRLEN'  # retrieve the length of a string value at a key

        ## List Operations
        LIST_SET = 'LSET'  # set a value in a list by its index
        LEFT_POP = 'LPOP'  # pop a value off the left side of a list
        RIGHT_POP = 'RPOP'  # pop a value off the right side of a list
        LEFT_PUSH = 'LPUSH'  # add a value to the right side of a list
        RIGHT_PUSH = 'RPUSH'  # add a value to the right side of a list
        LEFT_PUSH_X = 'LPUSHX'  # add a value to the left side of a list, only if it already exists
        RIGHT_PUSH_X = 'RPUSHX'  # add a value to the right side of a list, only if it already exists
        LIST_TRIM = 'LTRIM'  # truncate the list to only containing X values
        LIST_INDEX = 'LINDEX'  # get a value from a list by its index
        LIST_RANGE = 'LRANGE'  # get a range of values from a list
        LIST_LENGTH = 'LLEN'  # retrieve the current length of a list
        LIST_REMOVE = 'LREM'  # remove elements from an existing list
        BLOCK_LEFT_POP = 'BLPOP'  # same as lpop, but block until an item is available
        BLOCK_RIGHT_POP = 'BRPOP'  # same as rpop, but block until an item is available

        ## Set Operations
        SET_ADD = 'SADD'  # add a new member to a set
        SET_POP = 'SPOP'  # pop and remove an item from the end of a set
        SET_MOVE = 'SMOVE'  # move a member from one set to another
        SET_DIFF = 'SDIFF'  # calculate the difference/delta of two sets
        SET_UNION = 'SUNION'  # calculate the union/combination of two sets
        SET_REMOVE = 'SREM'  # remove one or more members from a set
        SET_MEMBERS = 'SMEMBERS'  # retrieve all members of a set
        SET_INTERSECT = 'SINTER'  # calculate the intersection of two sets
        SET_IS_MEMBER = 'SISMEMBER'  # determine if a value is a member of a set
        SET_DIFF_STORE = 'SDIFFSTORE'  # calculate the delta of two sets and store the result
        SET_CARDINALITY = 'SCARD'  # calculate the number of members in a set
        SET_UNION_STORE = 'SUNIONSTORE'  # calculate the union of two sets and store the result
        SET_RANDOM_MEMBER = 'SRANDMEMBER'  # retrieve a random member of a set
        SET_INTERSECT_STORE = 'SINTERSTORE'  # calculate the intersection of a set and store the result

        ## Sorted Set Operations
        SORTED_ADD = 'ZADD'  # add a member to a sorted set
        SORTED_RANK = 'ZRANK'  # determine the index o a member in a sorted set
        SORTED_RANGE = 'ZRANGE'  # return a range of members in a sorted set, by index
        SORTED_SCORE = 'ZSCORE'  # get the score associated with the given member in a sorted set
        SORTED_COUNT = 'ZCOUNT'  # count the members in a sorted set with scores within a given range
        SORTED_REMOVE = 'ZREM'  # remove one or more members from a sorted set
        SORTED_CARDINALITY = 'ZCARD'  # get the number of members in a sorted set (cardinality)
        SORTED_UNION_STORE = 'ZUNIONSTORE'  # compute the union of two sorted sets, storing the result at a new key
        SORTED_INCREMENT_BY = 'ZINCRBY'  # increment the score of a member in a sorted set by X
        SORTED_INDEX_BY_SCORE = 'ZREVRANK'  # determine the index of a member in a sorted set, scores ordered high=>low
        SORTED_RANGE_BY_SCORE = 'ZRANGEBYSCORE'  # return a range of members in a sorted set, by score
        SORTED_INTERSECT_STORE = 'ZINTERSTORE'  # intersect multiple sets, storing the result in a new key
        SORTED_MEMBERS_BY_INDEX = 'ZREVRANGE'  # get a range of members in a sorted set. by index, scores high=>low
        SORTED_MEMBERS_BY_SCORE = 'ZREVRANGEBYSCORE'  # remove all members in a sorted set within the given scores
        SORTED_REMOVE_RANGE_BY_RANK = 'ZREMRANGEBYRANK'  # remove members in a sorted set within a given range of ranks
        SORTED_REMOVE_RANGE_BY_SCORE = 'ZREMRANGEBYSCORE'  # remove members in a sorted set within a range of scores

        ## Pub/Sub Operations
        PUBLISH = 'PUBLISH'  # publish a message to a specific pub/sub channel
        SUBSCRIBE = 'SUBSCRIBE'  # subscribe to messages on an exact channel
        UNSUBSCRIBE = 'UNSUBSCRIBE'  # unsubscribe from messages on an exact channel
        PATTERN_SUBSCRIBE = 'PSUBSCRIBE'  # subscribe to all pub/sub channels matching a pattern
        PATTERN_UNSUBSCRIBE = 'PUNSUBSCRIBE'  # unsubscribe from all pub/sub channels matching a pattern

        ## Transactional Operations
        EXEC = 'EXEC'  # execute buffered commands in a pipeline queue
        MULTI = 'MULTI'  # start a new pipeline, where commands can be buffered
        WATCH = 'WATCH'  # watch a key, such that we can receive a notification in the event it is modified
        UNWATCH = 'UNWATCH'  # unwatch all currently watched keys
        DISCARD = 'DISCARD'  # discard buffered commands in a pipeline completely

        ## Scripting Operations
        EVALUATE = 'EVAL'  # evaluate a script inline, written in Lua
        EVALUATE_STORED = 'EVALSHA'  # execute an already-loaded script
        SCRIPT_LOAD = ('SCRIPT', 'LOAD')  # load a script into memory for future execution
        SCRIPT_KILL = ('SCRIPT', 'KILL')  # kill the currently running script
        SCRIPT_FLUSH = ('SCRIPT', 'FLUSH')  # flush all scripts from the script cache
        SCRIPT_EXISTS = ('SCRIPT', 'EXISTS')  # check existence of scripts in the script cache

        ## Connection Operations
        ECHO = 'ECHO'  # echo the given string from the server side - for testing
        PING = 'PING'  # 'ping' to receive a 'pong' from the server - for keepalive
        QUIT = 'QUIT'  # exit and close the current connection
        SELECT = 'SELECT'  # select the currently-active database
        AUTHENTICATE = 'AUTH'  # authenticate to a protected redis instance

        ## Server Operations
        TIME = 'TIME'  # get the current time, as seen by the server
        SYNC = 'SYNC'  # internal command - for master/slave propagation
        SAVE = 'SAVE'  # synchronously save the dataset to disk
        INFO = 'INFO'  # get information and statistics about the server
        DEBUG = ('DEBUG', 'OBJECT')  # get detailed debug information about an object
        DB_SIZE = 'DBSIZE'  # get the number of keys in a database
        SLOWLOG = 'SLOWLOG'  # manages the redis slow queries log
        MONITOR = 'MONITOR'  # listen for all requests received by the server in realtime
        SLAVE_OF = 'SLAVEOF'  # make the server a slave, or promote it to master
        SHUTDOWN = 'SHUTDOWN'  # synchronously save to disk and shutdown the server process
        FLUSH_DB = 'FLUSHDB'  # flush all keys and values from the current database
        FLUSH_ALL = 'FLUSHALL'  # flush all keys and values in all of redis
        LAST_SAVE = 'LASTSAVE'  # retrieve a UNIX timestamp indicating the last successful save to disk
        CONFIG_GET = ('CONFIG', 'GET')  # get the value of a redis configuration parameter
        CONFIG_SET = ('CONFIG', 'SET')  # set the value of a redis configuration parameter
        CLIENT_KILL = ('CLIENT', 'KILL')  # kill a client's active connection with redis
        CLIENT_LIST = ('CLIENT', 'LIST')  # list all the active client connctions with redis
        CLIENT_GET_NAME = ('CLIENT', 'GETNAME')  # get the name of the current connection
        CLIENT_SET_NAME = ('CLIENT', 'SETNAME')  # set the name of the current connection
        CONFIG_RESET_STAT = ('CONFIG', 'RESETSTAT')  # reset infostats that are served by "INFO"
        BACKGROUND_SAVE = 'BGSAVE'  # in the background, save the current dataset to disk
        BACKGROUND_REWRITE = 'BGREWRITEAOF'  # in the background, rewrite the current AOF

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment.
            :returns: The imported ``Redis`` driver, or ``False`` if it could not be found. '''

        return _REDIS

    @decorators.classproperty
    def serializer(cls):

        ''' Load and return the appropriate serialization codec.
            :returns: The currently ``serializer``. Defaults to ``msgpack``
                      with a fallback to built-in ``JSON``. '''

        ## Use msgpack if available, fall back to JSON
        if _MSGPACK:
            return msgpack
        return json

    @classmethod
    def acquire(cls, name, bases, properties):

        ''' Perform first initialization. This method overrides a
            hook by the same name in :py:class:`model.adapter.ModelAdapter`,
            and is invoked during :py:class:`model.Model` class construction
            before the final call to ``type``.

            Because this method is invoked *before* there is actually
            an existing :py:class:`model.Model`, it must accept the same
            parameter signature as ``type``.

            :param name: Name of the :py:class:`model.Model` to resolve
                         an adapter for.
            :param bases: Tupled base parents for the :py:class:`model.Model`
                          class-to-be.
            :param properties: Map of defined :py:class:`model.Model` data
                               properties.

            :raises ValueError: In the case that ``config`` requests a ``Redis``
                                connection profile which is invalid or missing.

            :returns: The acquired adapter, or ``None`` in the case of an empty
                      set of server profiles. '''

        global _server_profiles
        global _default_profile
        global _profiles_by_model

        ## Resolve default
        servers = cls.config.get('servers', False)

        if not _default_profile:

            ## Resolve Redis config
            if not servers:  # pragma: no cover
                return None  # no servers to connect to (on noez)

            for name, config in servers.items():
                if name == 'default' or (config.get('default', False) is True):
                    _default_profile = name
                elif not _default_profile:  # pragma: no cover
                    _default_profile = name
                _server_profiles[name] = config

        # Resolve specific adapter, if listed explicitly
        if '__redis__' in properties and isinstance(properties.get('__redis__'), basestring):
            if properties['__redis__'] not in servers:
                error = "Model \"%s\" mapped to non-existent Redis profile \"%s\"." % (name, properties['__redis__'])
                raise ValueError(error)
            else:
                _profiles_by_model['index'].add(name)
                _profiles_by_model['map'][name] = servers.get(properties['__redis__'], _default_profile)

        return super(RedisAdapter, cls).acquire(name, bases, properties)

    @classmethod
    def channel(cls, kind):

        ''' Retrieve a write channel to Redis.

            :param kind: String :py:class:`model.Model` kind to retrieve a channel for.
            :returns: Acquired ``Redis`` client connection, potentially specific to the
                      handed-in ``kind``. '''

        # convert to string kind if we got a model class
        if not isinstance(kind, basestring):
            kind = kind.kind()

        # check for existing connection
        if kind in _client_connections:

            # return cached connection
            return _client_connections[kind]

        # check kind-specific profiles
        if kind in _profiles_by_model.get('index', set()):
            client = _client_connections[kind] = cls.adapter.StrictRedis(**_profiles_by_model['map'].get(kind))
            ## @TODO: patch client with connection/workerpool (if gevent)
            return client

        ## @TODO: patch client with connection/workerpool (if gevent)

        # check for cached default connection
        if '__default__' in _client_connections:
            return _client_connections['__default__']

        # otherwise, build new default
        default_profile = _server_profiles[_default_profile]
        if isinstance(default_profile, basestring):
            profile = _server_profiles[default_profile]  # if it's a string, it's a pointer to a profile

        client = _client_connections['__default__'] = cls.adapter.StrictRedis(**profile)
        return client

    @classmethod
    def execute(cls, operation, kind, *args, **kwargs):

        ''' Acquire a channel and execute an operation, optionally buffering the command.

            :param operation: Operation name to execute (from :py:attr:`RedisAdapter.Operations`).
            :param kind: String :py:class:`model.Model` kind to acquire the channel for.
            :param args: Positional arguments to pass to the low-level operation selected.
            :param kwargs: Keyword arguments to pass to the low-level operation selected.
            :returns: Result of the selected low-level operation. '''

        if isinstance(operation, tuple):
            operation = '_'.join([operation])  # reduce (CLIENT, KILL) to 'client_kill' (for example)
        return getattr(cls.channel(kind), operation.lower())(*args, **kwargs)

    @classmethod
    def get(cls, key):

        ''' Retrieve an entity by Key from Redis.

            :param key: Target :py:class:`model.Key` to retrieve from storage.
            :returns: The deserialized and decompressed entity associated with
                      the target ``key``. '''

        joined, flattened = key
        if cls.EngineConfig.mode == RedisMode.toplevel_blob:

            # execute query
            result = cls.execute(cls.Operations.GET, flattened[1], joined)

            if isinstance(result, basestring):

                # account for none, optionally decompress
                if cls.EngineConfig.compression:
                    result = cls.compressor.decompress(result)

                # deserialize structures
                return cls.serializer.loads(result)

        elif cls.EngineConfig.mode == RedisMode.hashkind_blob:
            ## @TODO: `get` for `hashkind_blob` mode
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_blob:
            ## @TODO: `get` for `hashkey_blob`
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_hash:
            ## @TODO: `get` for `hashkey_hash`
            pass

        # @TODO: different storage internal modes

    @classmethod
    def put(cls, key, entity, model):

        ''' Persist an entity to storage in Redis.

            :param key: New (and potentially empty) :py:class:`model.Key` for
                        ``entity``. Must be assigned an ``ID`` by the driver
                        through :py:meth:`RedisAdapter.allocate_ids` in the case
                        of an empty (non-deterministic) :py:class:`model.Key`.
            :param entity: Object entity :py:class:`model.Model` to persist in
                           ``Redis``.
            :param model: Schema :py:class:`model.Model` associated with the
                          target ``entity`` being persisted.

            :returns: Result of the lower-level write operation. '''

        # reduce entity to dictionary
        serialized = entity.to_dict()
        joined, flattened = key

        if cls.EngineConfig.mode == RedisMode.toplevel_blob:

            # serialize + optionally compress
            serialized = cls.serializer.dumps(serialized)
            if cls.EngineConfig.compression:
                serialized = cls.compressor.compress(serialized)

            # delegate to redis client
            return cls.execute(cls.Operations.SET, flattened[1], joined, serialized)

        elif cls.EngineConfig.mode == RedisMode.hashkind_blob:
            ## @TODO: `put` for `hashkind_blob` mode
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_blob:
            ## @TODO: `put` for `hashkey_blob`
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_hash:
            ## @TODO: `put` for `hashkey_hash`
            pass

        # @TODO: different storage internal modes

    @classmethod
    def delete(cls, key):

        ''' Delete an entity by Key from Redis.

            :param key: Target :py:class:`model.Key`, whose associated
                        :py:class:`model.Model` is being deleted.

            :returns: The result of the low-level delete operation. '''

        joined, flattened = key.flatten(True)

        if cls.EngineConfig.mode == RedisMode.toplevel_blob:

            # delegate to redis client with encoded key
            return cls.execute(cls.Operations.DELETE, key.kind, cls.encode_key(joined, flattened))

        elif cls.EngineConfig.mode == RedisMode.hashkind_blob:
            ## @TODO: `delete` for `hashkind_blob` mode
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_blob:
            ## @TODO: `delete` for `hashkey_blob`
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_hash:
            ## @TODO: `delete` for `hashkey_hash`
            pass

        # @TODO: different storage internal modes

    @classmethod
    def allocate_ids(cls, key_class, kind, count=1):

        ''' Allocate new :py:class:`model.Key` IDs up to ``count``. Allocated
            IDs are guaranteed not to be provisioned or otherwise used by the
            underlying persistence engine, and thus can be used for uniquely
            identifying non-deterministic data.

            :param key_class: Descendent of :py:class:`model.Key`
                              to allocate IDs for.
            :param kind: String :py:class:`model.Model` kind name.
            :param count: The number of IDs to generate, which **must**
                          be greater than 1. Defaults to ``1``.

            :raises ValueError: In the case the ``count`` is less than ``1``.
            :returns: If **only one** ID is requested, an **integer ID**
                      suitable for use in a :py:class:`model.Key` directly.
                      If **more than one** ID is requested, a **generator**
                      is returned, which ``yields`` a set of provisioned
                      integer IDs, each suitable for use in a
                      :py:class:`model.Key` directly. '''

        if count < 1:
            raise ValueError("Cannot allocate less than 1 ID's.")

        # generate kinded key to resolve ID pointer
        kinded_key = key_class(kind)
        joined, flattened = kinded_key.flatten(True)

        if cls.EngineConfig.mode == RedisMode.toplevel_blob:
            key_root_id = cls._magic_separator.join([cls._meta_prefix, cls.encode_key(joined, flattened)])

            # increment by the amount desired
            value = cls.execute(cls.Operations.HASH_INCREMENT, kinded_key.kind, key_root_id, cls._id_prefix, count)

        elif cls.EngineConfig.mode == RedisMode.hashkind_blob:
            ## @TODO: `allocate_ids` for `hashkind_blob` mode
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_blob:
            ## @TODO: `allocate_ids` for `hashkey_blob`
            pass

        elif cls.EngineConfig.mode == RedisMode.hashkey_hash:
            ## @TODO: `allocate_ids` for `hashkey_hash`
            pass

        if count > 1:
            def _generate_range():

                ''' Generate a range of requested ID's.

                    :yields: Each item in a set of provisioned integer IDs,
                             suitable for use in a :py:class:`model.Key`. '''

                bottom_range = (value - count)
                for i in xrange(bottom_range, value):
                    yield i

            return _generate_range
        return value

    @classmethod
    def encode_key(cls, joined, flattened):

        ''' Encode a Key for storage in ``Redis``. Since we don't need to
            do anything fancy, just delegate this to the abstract (default)
            encoder, which is ``base64``.

            If :py:attr:`RedisEngine.EngineConfig.encoding` is disabled, this
            simply returns the ``joined`` :py:class:`model.Key` (for reference,
            see :py:meth:`model.Key.flatten`).

            :param joined: String-joined :py:class:`model.Key`.
            :param flattened: Tupled ("raw format") :py:class:`model.Key`.
            :returns: In the case that ``encoding`` is *on*, the encoded string
                      :py:class:`model.Key`, suitable for storage in ``Redis``.
                      Otherwise (``encoding`` is *off*), the cleartext ``joined``
                      key. '''

        if cls.EngineConfig.encoding:
            return abstract._encoder(joined)
        return joined

    def write_indexes(cls, writes):  # pragma: no cover

        ''' Write a batch of index updates generated earlier via
            :py:meth:`RedisAdapter.generate_indexes`.

            :param writes: Batch of writes to commit to ``Redis``.
            :raises: :py:exc:`NotImplementedError`, as this method is not yet implemented. '''

        raise NotImplementedError()

    def clean_indexes(cls, key):  # pragma: no cover

        ''' Clean indexes and index entries matching a particular
            :py:class:`model.Key`, and generated via the adapter method
            :py:meth:`RedisAdapter.generate_indexes`.

            :param key: Target :py:class:`model.Key` to clean from ``Redis`` indexes.
            :raises: :py:exc:`NotImplementedError`, as this method is not yet implemented. '''

        raise NotImplementedError()

    def execute_query(cls, spec):  # pragma: no cover

        ''' Execute a :py:class:`model.Query` across one (or multiple)
            indexed properties.

            :param spec: Descendent of :py:class:`model.Query` specifying the query to satisfy.
            :raises: :py:exc:`NotImplementedError`, as this method is not yet implemented. '''

        raise NotImplementedError()
