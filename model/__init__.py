# -*- coding: utf-8 -*-

'''

AppTools Models

Exports useful utils/classes for data modelling, along with builtin models
and tools for working with polymorphic persistent data.

-sam (<sam@momentum.io>)

'''

## Base Imports
try:
    import cPickle as pickle
except ImportError, e:
    import pickle

import config
import webapp2
import weakref
import inspect
import datetime
import collections

## AppTools Util
from apptools.util import json
from apptools.util import debug
from apptools.util import platform
from apptools.util import _loadModule
from apptools.util import ObjectProxy
from apptools.util import datastructures

## Constants
_MODEL_PROPERTIES = frozenset([
    '_getModelPath',
    '_getClassPath',
    '_use_cache',
    '_use_memcache',
    '_use_datastore',
    '_post_put_hook',
    '_post_delete_hook'
])

_DEFAULT_ENGINE = None
_STORAGE_ENGINES = {}
__flattened_properties = None
__unflattened_properties = None
logging = debug.AppToolsLogger(path='apptools', name='model')._setcondition(config.debug)

## Defaults
_DEFAULT_PROP_OPTS = {}


## _AppToolsModel
# This model class mixes in a few utilities to all submodels.
class _AppToolsModel(object):

    ''' Root, master, polymorphic-capable thin data model. Everything lives under this class. '''

    def __init__(self, key=None, **kwargs):

        ''' Receive a newly inflated model. '''

        self.__key__ = key
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def _getModelPath(self, seperator=None):

        ''' Retrieve a path for this model's polymorphic class chain. '''

        path = [i for i in str(self.__module__ + '.' + self.__class__.__name__).split('.')]

        if seperator is not None:
            return seperator.join(path)

        return path

    def _getClassPath(self, seperator=None):

        ''' Retrieve an importable path for this model's class. '''

        if hasattr(self, '__class_hierarchy__'):
            path = [cls.__name__ for cls in self.__class_hierarchy__]

            if seperator is not None:
                return seperator.join(path)
            return path
        else:
            return []

    def __enter__(self):

        ''' Sets an internal flag to indicate emptiness without `None`, when a model is used as a context manager. '''

        self.__sentinel__ = True

    def __exit__(self, *args, **kwargs):

        ''' Resets internal flags. '''

        self.__sentinel__ = False

    def to_dict(self, exclude=None, include=None):

        ''' Reduce this model to a dictionary. '''

        props = {}
        with self:
            for name, dtype, opts in self.__pmap__:
                    if exclude and name in exclude:
                        continue
                    elif include and name not in include:
                        continue
                    else:
                        value = getattr(self, name)
                        if value != datastructures._EMPTY:
                            props[name] = value
        return props

try:
    # App Engine Imports
    from google.appengine.ext import db as ldb
    from google.appengine.ext import blobstore

    # NDB Imports (New DataBase)
    from google.appengine.ext import ndb as nndb
    from google.appengine.ext.ndb import key, model

except ImportError:

    # No NDB :(
    _NDB = False
    _GAE = False

    logging.debug('NDB/LDB is not supported in this environment.')

    ## AbstractModelFactory
    # Without NDB, we just present an abstract parent.
    class AbstractModelFactory(type):

        ''' Abstract parent to model factory metaclasses. '''

        pass

    ## _ModelPathProperty
    # Subclass `str`, for use with ThinModel, without NDB present.
    class _ModelPathProperty(str):
        pass

    ## _ClassKeyProperty
    # Subclass `str`, for use with ThinModel, without NDB present.
    class _ClassKeyProperty(list):
        pass

else:

    # We have NDB!
    _NDB = True
    _GAE = True

    logging.debug('NDB/LDB is supported in this environment.')

    ## AbstractModelFactory
    # Mixes in NDB's metaclass, if available.
    class AbstractModelFactory(nndb.MetaModel):

        ''' Abstract parent to model factory metaclasses. '''

        pass

    ## _ModelPathProperty
    # This property is used in PolyPro to store the model's type inheritance path.
    class _ModelPathProperty(ldb.StringProperty):

        ''' Stores the Python package import path from the application root, for lazy-load on search. '''

        def __init__(self, name, **kwargs):
            super(_ModelPathProperty, self).__init__(name=name, default=None, **kwargs)

        def __set__(self, *args):
            raise ldb.DerivedPropertyError('Model-path is a derived property and cannot be set.')

        def __get__(self, model_instance, model_class):
            if model_instance is None:
                return self
            return model_instance._getModelPath(':')

    ## _ClassKeyProperty
    # This property is used in PolyPro to store the model's class path.
    class _ClassKeyProperty(ldb.ListProperty):

        ''' Stores the polymodel class inheritance path. '''

        def __init__(self, name):
            super(_ClassKeyProperty, self).__init__(name=name, item_type=str, default=None)

        def __set__(self, *args):
            raise ldb.DerivedPropertyError('Class-key is a derived property and cannot be set.')

        def __get__(self, model_instance, model_class):
            if model_instance is None:
                return self
            return model_instance._getClassPath()

try:
    import pipeline

except ImportError:

    # No pipelines :(
    _PIPELINES = False

    ## PipelineTrigger
    # Placeholder trigger mixin, in case pipelines aren't supported in our current environment.
    class PipelineTrigger(object):

        ''' Placeholder class, used when pipelines is not supported. '''

        pass

    logging.debug('Pipelines are not supported in this environment.')

else:

    # Pipelines are supported!
    _PIPELINES = True

    logging.debug('Pipelines are supported in this environment.')

    ## PipelineTrigger
    # Allows bound pipelines to be constructed and started automatically when NDB hooks fire on models.
    class PipelineTrigger(object):

        ''' Mixin class that provides pipeline-based model triggers. '''

        _pipeline_class = None

        ### === Internal Properties === ###
        __config = config.config.get('apptools.model.integration.pipelines', {})
        __logging = debug.AppToolsLogger('apptools.model.mixins', 'PipelineTriggerMixin')._setcondition(__config.get('logging', False))

        ### === Internal Methods === ###
        @classmethod
        def _construct_hook_pipeline(cls, action, **kwargs):

            ''' Conditionally trigger a hooked model-driven pipeline. '''

            if hasattr(cls, '_pipeline_class'):
                if cls._pipeline_class is not None:
                    if issubclass(cls._pipeline_class, ModelPipeline):
                        cls.__logging.info('Valid pipeline found for model `%s`.' % cls)
                        if hasattr(cls._pipeline_class, action):
                            cls.__logging.info('Pipeline has hook for action `%s`.' % action)

                            ## build pipeline params
                            kwargs['action'] = action

                            ## build pipeline
                            return cls._pipeline_class(**kwargs)

                        else:
                            cls.__logging.info('Pipeline does not have a hook defined for action `%s`.' % action)
                            return

                    else:
                        cls.__logging.error('Model-attached pipeline (on model "%s") is not an instance of ModelPipeline (of type "%s").' % (cls, cls._pipeline_class))
                        return
            else:
                cls.__logging.info('No hooked pipeline detected for model "%s" on action "%s".' % (cls, action))
            return

        @classmethod
        def _trigger_hook_pipeline(cls, action, start=False, **kwargs):

            ''' Try to construct a pipeline for a given trigger hook, and optionally start it. '''

            if action not in frozenset(['put', 'delete']):
                cls.__logging.warning('Triggered NDB hook action is not `put` or `delete`. Ignoring.')
                return
            else:
                cls.__logging.info('Valid hook action for potential pipeline hook. Trying to construct/resolve.')
                p = cls._construct_hook_pipeline(action, **kwargs)
                cls.__logging.info('Got back pipeline: `%s`.' % p)
                if p:
                    if start:
                        cls.__logging.info('Starting hooked pipeline...')

                        running_tests = os.environ.get('RUNNING_TESTS')
                        if running_tests:
                            pipeline = p.start_test(queue_name=cls.__config.get('trigger_queue', 'default'))
                        else:
                            pipeline = p.start(queue_name=cls.__config.get('trigger_queue', 'default'))

                        cls.__logging.info('Hooked pipeline away: "%s"' % pipeline)
                        return pipeline
                    cls.__logging.info('Autostart is off. NOT starting constructed pipeline.')
                    return p
                else:
                    cls.__logging.error('Could not construct pipeline! :(')
                    return
            return

        ### === Hook Methods === ###
        def _pipelines_post_put_hook(self, future):

            ''' This hook is run after an AppModel is put using NDB. '''

            cls = self.__class__
            if cls.__config.get('enable', False):
                cls.__logging.info('Pipelines-NDB integration hooks enabled.')
                cls._trigger_hook_pipeline('put', cls.__config.get('autostart', False), key=self.key.urlsafe())
            else:
                cls.__logging.info('Pipelines-NDB integration hooks disabled.')
            return

        @classmethod
        def _pipelines_post_delete_hook(cls, key, future):

            ''' This hook is run after an AppModel is deleted using NDB. '''

            if cls.__config.get('enable', False):
                cls.__logging.info('Pipelines-NDB integration hooks enabled.')
                cls._trigger_hook_pipeline('delete', cls.__config.get('autostart', False), key=key.urlsafe())
            else:
                cls.__logging.info('Pipelines-NDB integration hooks disabled.')
            return

        ### === Model Hooks === ###
        def _post_put_hook(self, future):

            ''' Post-put hook. '''

            self._pipelines_post_put_hook(future)

        @classmethod
        def _post_delete_hook(cls, key, future):

            ''' Post-delete hook. '''

            cls._pipelines_post_delete_hook(key, future)

try:
    from apptools import services
    from protorpc import messages as pmessages

except ImportError as e:

    raise

    # ProtoRPC is not supported
    _PROTORPC = False

    logging.debug('ProtoRPC is not supported in this environment.')

    # Empty out our globals and indicate ProtoRPC isn't supported in the current environment.
    _PROTORPC, _MESSAGE_FIELDS, _MESSAGE_FIELD_LOOKUP, _MESSAGE_FIELD_TO_BASETYPE = False, frozenset([]), frozenset([]), frozenset([])

    ## MessageConverterMixin
    # Placeholder class, used when ProtoRPC is not supported in the current environment.
    class MessageConverter(object):

        ''' Placeholder class, used when ProtoRPC is not supported in the current environment. '''

        pass

else:

    # ProtoRPC is supported
    _PROTORPC = True

    logging.debug('ProtoRPC is supported in this environment.')

    ## MessageConverterMixin
    # Allows us to automatically convert an NDB model to or from a bound ProtoRPC message class.
    class MessageConverter(object):

        ''' Mixin class for automagically generating a ProtoRPC Message class from a model. '''

        _message_class = None

        @classmethod
        def to_message_model(cls, exclude=None, include=None, property_set=None):

            ''' Convert this model to a ProtoRPC message class. '''

            if not _PROTORPC:
                raise RuntimeError("ProtoRPC is not supported in this environment.")
            if exclude:
                property_set = [k for k in cls.__pmap__ if k[0] not in exclude]
            elif include:
                property_set = [k for k in cls.__pmap__ if k[0] in include]
            elif property_set is None:
                property_set = cls.__pmap__[:]
            lookup_s = tuple([k[0] for k in property_set])

            if lookup_s in cls.__messages__:
                return cls.__messages__.get(lookup_s)

            props = map(lambda g: (g[0], convert_basetype_to_field(g[1], g[2]), g[2]) if ('impl' not in g[2] and 'field' not in g[2]) else (g[0], resolve_fieldtype(g[1], g[2]), g[2]), property_set)

            field_props = []
            for i, group in enumerate(props):
                name, prop, opts = group

                if 'indexed' in opts:
                    del opts['indexed']

                if 'required' in opts:
                    del opts['required']

                if prop in frozenset([pmessages.MessageField, pmessages.EnumField]):

                    ## TODO: Recursive generation of messages
                    raise ValueError("Automatic model => message conversion does not currently support submessages or enums. Please author an explicit message class for the model '%s' and link it via the classmember '_message_class'." % cls.__name__)

                else:
                    args = [i+1]  # ID's need to be 1-indexed
                    field_props.append((name, prop, args, opts))

            msg_impl = pmessages.Message.__metaclass__(*[
                cls.__name__, tuple([pmessages.Message]), dict([(k, v(*a, **o)) for k, v, a, o in field_props])])

            cls.__messages__[lookup_s] = msg_impl
            return msg_impl

        def to_message(self, include=None, exclude=None, strict=False, message_class=None):

            ''' Convert an entity instance into a message instance. '''

            if message_class:
                response = message_class()
            else:
                if self._message_class is not None:
                    response = self._message_class()
                else:
                    response = self.to_message_model(exclude, include)

            if hasattr(response, 'key'):
                if self.key is not None:
                    response.key = unicode(self.key.urlsafe())
                else:
                    response.key = None

            def _convert_prop(v):

                ''' Helper method to convert a property to be assigned to a message. '''

                if isinstance(v, nndb.Key):
                    return v.urlsafe()

                elif isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                    return v.isoformat()

                # TODO: Activate this code and write a test for it.
                elif isinstance(v, ndb.Model):
                    if hasattr(v, '_message_class'):
                        return v.to_message()
                    else:
                        model_dict = {}
                        for k, v in v.to_dict().items():
                            model_dict[k] = _convert_prop(v)
                        return model_dict

                else:
                    if isinstance(v, (tuple, list)):
                        values = []
                        for i in v:
                            values.append(_convert_prop(i))
                        return values
                    if isinstance(v, (int, basestring, float, bool)):
                        return v
                    if v == None:
                        if strict:
                            return v

            def _convert_to_message_field(message_class, v):

                ''' Helper method to convert a value to the provided message type. '''

                if isinstance(v, list):
                    if not len(v):
                        return []
                    if isinstance(v[0], nndb.Key):
                        objs = ndb.get_multi(v)
                        return [obj.to_message() for obj in objs]
                    else:
                        messages = []
                        for i in v:
                            messages.append(_convert_to_message_field(message_class, i))
                        return messages

                elif isinstance(v, dict):
                    message = message_class()
                    for key, val in v.items():
                        if hasattr(message, key):
                            setattr(message, key, _convert_prop(val))
                    return message

                else:
                    # Not list or dict, attempt to convert with other methods.
                    return _convert_prop(v)

            # Convert each property and assign it to the response message.
            msg_struct = {}
            for k, v in self.to_dict(include=include, exclude=exclude).items():
                if hasattr(response, k):
                    v = getattr(self, k)
                    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                        v = v.isoformat()
                    msg_struct[k] = v

            return response(**msg_struct)

        @classmethod
        def from_message(cls, message, key=None, **kwargs):

            ''' Convert a message instance to an entity instance. '''

            if (hasattr(message, 'key') and message.key) and key is None:
                obj = cls(key=nndb.key.Key(urlsafe=message.key), **kwargs)
            elif key is not None and isinstance(key, ndb.key.Key):
                obj = cls(key=nndb.key.Key(urlsafe=key.urlsafe()), **kwargs)
            elif key is not None and isinstance(key, basestring):
                obj = cls(key=nndb.key.Key(urlsafe=key), **kwargs)
            else:
                obj = cls(**kwargs)

            for k, v in cls._properties.items():
                if k == 'key':
                    continue
                if hasattr(message, k):
                    try:
                        setattr(obj, str(k), getattr(message, k))

                    except TypeError:
                        if k is not None and k not in [False, True, '']:

                            try:
                                setattr(obj, str(k), str(getattr(message, k)))
                            except TypeError:
                                continue

                    else:
                        continue
            return obj

        def mutate_from_message(self, message, exclude=[]):

            ''' Copy all the attributes except the key from message to this object. '''

            for k in [f.name for f in message.all_fields()]:
                if k == 'key' or (exclude and k in exclude):
                    continue
                if hasattr(self, k) and getattr(message, k):
                    try:
                        setattr(self, str(k), getattr(message, k))
                    except TypeError:
                        if k is not None and k not in [False, True, '']:
                            try:
                                setattr(self, str(k), str(getattr(message, k)))
                            except TypeError:
                                continue

                    except:
                        try:
                            # Is it an iso-formatted date?
                            date = datetime.datetime(*map(int, re.split('[^\d]', getattr(message, k))[:-1]))
                            setattr(self, str(k), date)
                        except (TypeError, ValueError):
                            # TODO: Handle other errors here?
                            try:
                                key = nndb.key.Key(urlsafe=getattr(message, k))
                                setattr(self, str(k), key)
                            except (TypeError, ProtocolBufferDecodeError):
                                continue
                    else:
                        continue
            return self


    if _NDB:
        # Message Field Mappings
        _MESSAGE_FIELD_TO_BASETYPE = frozenset([

            ((basestring, str, unicode, model.StringProperty), pmessages.StringField),
            ((int, model.IntegerProperty), pmessages.IntegerField),
            ((float, model.FloatProperty), pmessages.FloatField),
            ((bool, model.BooleanProperty), pmessages.BooleanField),
            ((bytearray, model.BlobProperty), pmessages.BytesField),
            ((datetime.datetime, model.DateTimeProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.date, model.DateProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.time, model.TimeProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((model.GeoPt, model.GeoPtProperty), pmessages.StringField, lambda x: str(x)),
            ((key.Key, model.KeyProperty), pmessages.StringField, lambda x: x.urlsafe()),
            ((blobstore.BlobKey, model.BlobKeyProperty), pmessages.StringField, lambda x: x.urlsafe()),
            (model.UserProperty, pmessages.StringField, lambda x: x.email()),
            ((_AppToolsModel, model.StructuredProperty, model.LocalStructuredProperty), pmessages.MessageField, lambda x: x.to_message()),
            ((object, dict, model.JsonProperty), pmessages.StringField, json.dumps),
            ((object, dict, model.PickleProperty), pmessages.StringField, pickle.dumps),
            ((None, model.GenericProperty, model.ComputedProperty), services.VariantField)

        ])

    else:
        _MESSAGE_FIELD_TO_BASETYPE = frozenset([

            ((basestring, str, unicode), pmessages.StringField),
            ((int), pmessages.IntegerField),
            ((float), pmessages.FloatField),
            ((bool), pmessages.BooleanField),
            ((bytearray), pmessages.BytesField),
            ((datetime.datetime), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.date), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.time), pmessages.StringField, lambda x: x.isoformat()),
            ((_AppToolsModel), pmessages.MessageField, lambda x: x.to_message()),
            ((object, dict), pmessages.StringField, json.dumps),
            ((object, dict), pmessages.StringField, pickle.dumps),
            ((None), services.VariantField)

        ])


    def get_fields():

        ''' Build a set of all available ProtoRPC message fields. '''

        names_to_classes, lookup = {}, set([])
        for bundle in _MESSAGE_FIELD_TO_BASETYPE:
            if len(bundle) == 2:
                basetypes, field = bundle
            elif len(bundle) == 3:
                basetypes, field, converter = bundle
            names_to_classes[field.__name__] = field
            lookup.add(field.__name__)
        return names_to_classes, lookup

    _MESSAGE_FIELDS, _MESSAGE_FIELD_LOOKUP = get_fields()


    def resolve_fieldtype(name, options, fail=False):

        ''' Resolve a field type by name, usually from an `impl` property. '''

        if 'field' in options:
            # resolve by an explicitly-declared ProtoRPC message field
            if options['field'] in _MESSAGE_FIELD_LOOKUP:
                return _MESSAGE_FIELDS.get(options['field'])

        elif 'impl' in options:
            # resolve by an explicity-declared NDB implementation property
            proptype = resolve_proptype(name, options, True)
            for prop_c, field_c in _MODEL_PROP_TO_FIELD:
                if prop_c.__name__ == proptype.__class__.__name__:
                    return field_c

        if not fail:
            return services.VariantField
        else:
            return False


    def convert_basetype_to_field(basetype, options, fail=False):

        ''' Convert a basetype to a suitable ProtoRPC message field. '''


        candidate_f = []
        for basegroup in _MESSAGE_FIELD_TO_BASETYPE:
            if basegroup is None:
                continue  # this field has no basetype conversion path

            if len(basegroup) == 2:
                basetypes, field = basegroup

            elif len(basegroup) == 3:
                basetypes, field, converter = basegroup

            if not isinstance(basetypes, tuple):
                basetypes = (basetypes,)
            if basetype in basetypes:
                candidate_f.append(field)

        # if we have no candidates
        if not candidate_f and candidate_f == []:
            if not fail:
                return services.VariantField
            else:
                return False  # :( indicate we couldn't resolve the message field

        # if we only have one candidate
        elif len(candidate_f) == 1:
            return candidate_f[0]

        # if there are many candidates
        else:
            # return the first, the specification order goes compatible => restrictive
            return candidate_f[0][1]

if _NDB:
    _MODEL_PROP_TO_BASETYPE = frozenset([

        ((basestring, str, unicode), (model.StringProperty, model.TextProperty), lambda x: model.StringProperty if len(x) < 500 else model.TextProperty),
        (int, model.IntegerProperty),
        (float, model.FloatProperty),
        (bool, model.BooleanProperty),
        (bytearray, model.BlobProperty),
        (datetime.datetime, model.DateTimeProperty),
        (datetime.date, model.DateProperty),
        (datetime.time, model.TimeProperty),
        (model.GeoPt, model.GeoPtProperty),
        (key.Key, model.KeyProperty),
        (blobstore.BlobKey, model.BlobKeyProperty),
        (None, model.UserProperty),
        (_AppToolsModel, model.StructuredProperty),
        (_AppToolsModel, model.LocalStructuredProperty),
        (object, model.JsonProperty, json.loads),
        (object, model.PickleProperty, pickle.loads),
        (None, model.GenericProperty, None),
        (None, model.ComputedProperty, None)

    ])
else:
    _MODEL_PROP_TO_BASETYPE = frozenset([])

if _PROTORPC and _NDB:
    _MODEL_PROP_TO_FIELD = frozenset([

        (model.StringProperty, pmessages.StringField),
        (model.TextProperty, pmessages.StringField),
        (model.FloatProperty, pmessages.FloatField),
        (model.IntegerProperty, pmessages.IntegerField),
        (model.BooleanProperty, pmessages.BooleanField),
        (model.DateTimeProperty, (pmessages.StringField, lambda x: str(x))),  # TODO: datetime/date/time conversion
        (model.DateProperty, (pmessages.StringField, lambda x: str(x))),
        (model.TimeProperty, (pmessages.StringField, lambda x: str(x))),
        (model.GeoPtProperty, (pmessages.StringField, lambda x: str(x))),
        (model.KeyProperty, (pmessages.StringField, lambda x: x.urlsafe())),
        (model.BlobKeyProperty, (pmessages.StringField, lambda x: x.urlsafe())),
        (model.UserProperty, (pmessages.StringField, lambda x: x.email())),
        (model.StructuredProperty, pmessages.MessageField),
        (model.LocalStructuredProperty, pmessages.MessageField),
        (model.JsonProperty, pmessages.MessageField),
        (model.PickleProperty, pmessages.MessageField),
        (model.GenericProperty, None),
        (model.ComputedProperty, None)

    ])

else:
    _MODEL_PROP_TO_FIELD = frozenset([])

def get_basetypes():

    ''' Flatten the _MODEL_PROP_TO_BASETYPE structure into a hashable list of basetypes. '''

    # calculate basetype
    _t = [t for t in
            filter(lambda x: x not in frozenset([None, object]),
                [t[0] for t in _MODEL_PROP_TO_BASETYPE])]

    # expand tuples
    for i, t in enumerate(_t):
        if isinstance(t, tuple):
            for v in t[1:]:
                _t.append(v)
            _t[i] = t[0]

    return frozenset(_t)

_BASE_TYPES = get_basetypes()

def property_classes(flatten=False):

    ''' Return a mapping of all property classes, optionally flattened into a single list. '''

    global __flattened_properties
    global __unflattened_properties

    if flatten is False:
        if __unflattened_properties is not None:
            return __unflattened_properties
    else:
        if __flattened_properties is not None:
            return __flattened_properties

    class_lists = [db, ndb]
    p_list = []
    for class_list in class_lists:
        for p_name, p_class in class_list.items():
            if flatten is True:
                p_list.append(p_name)
            if flatten is False:
                p_list.append((p_name, p_class))

    if flatten: __flattened_properties = p_list
    else: __unflattened_properties = p_list

    return p_list

def resolve_proptype(name, options, fail=False):

    ''' Resolve a property type by name, usually from an `impl` option. '''

    if 'impl' in options:
        basetype, name = name, options.get('impl')
        del options['impl']
    else:
        basetype = name
    if name in ndb:
        return getattr(nndb, name)(**options)
    elif name in db:
        return getattr(ldb, name)(**options)
    else:
        if fail is False:
            return nndb.GenericProperty(**options)
        else:
            return False

def convert_basetype_to_ndb(basetype, options, fail=False):

    ''' Convert a basetype to an NDB property. '''

    candidate_p = []
    for basegroup in _MODEL_PROP_TO_BASETYPE:
        if basegroup is None:
            continue  # this prop has no basetype conversion path

        if not isinstance(basegroup, tuple):
            basegroup = (basegroup,)
        else:
            if basegroup[0] == None:
                continue # this prop has no basetype conversion path

            if len(basegroup) == 2:
                basetypes, proptypes = basegroup
            else:
                basetypes, proptypes, converter = basegroup

        if not isinstance(basetypes, tuple):
            basetypes = (basetypes,)
        if basetype in basetypes:
            candidate_p.append(proptypes)

    # if we have no candidates
    if not candidate_p and candidate_p == []:
        if not fail:
            return nndb.GenericProperty(**options)
        else:
            return False  # :( indicate we couldn't resolve the property type

    # if we only have one candidate
    elif len(candidate_p) == 1:
        if isinstance(candidate_p[0], tuple):
            if len(candidate_p[0]) == 3:
                # if there's a converter, use it
                return candidate_p[0][2](**options)
            else:
                # have to default to the first (most compatible)
                return candidate_p[0][0](**options)
        else:
            # there's only one candidate proptype
            return candidate_p[0](**options)
    else:
        return candidate_p[0][0](**options)


## ThinModelFactory
# Metaclass for converting thin model classes to midway objects that can be expressed as models, messages, dictionaries, etc.
class ThinModelFactory(AbstractModelFactory):

    ''' Root AppTools model metaclass and factory. '''

    def __new__(cls, name, bases, properties, expando=False):

        ''' Create a ThinModel object if supported, otherwise duck out. '''

        global _DEFAULT_ENGINE
        global _STORAGE_ENGINES

        if name == 'ThinModel' or name == 'AppModel':  # don't init abstract models
            return type(name, bases, properties)

        # scan for thin mode, enact it if supported
        thinmode = True
        c_special = []
        c_properties = []

        # filter out/scan for properties
        for k, v in properties.items():
            if k.startswith('__'):
                c_special.append((k, v))
                continue

            if _NDB:
                if isinstance(v, nndb.Property):
                    thinmode = False
                    break
            c_properties.append((k, v))

        # if we're not in thinmode, send it over to NDB
        if not thinmode and _NDB:
            if expando:
                return nndb.Expando.__metaclass__.__new__(name, bases, properties)
            return nndb.Model.__metaclass__.__new__(name, bases, properties)

        # otherwise, generate an internal schema and midway object
        else:

            # resolve our storage engines
            _DEFAULT_ENGINE, _STORAGE_ENGINES = ThinModelFactory.resolve_storage_engines()

            obj = {}
            schema = []

            obj = {
                '__name__': name,
                '__pmap__': [],
                '__bases__': bases,
                '__lookup__': [],
                '__pclass__': [],
                '__ndb__': {},
                '__impl__': [],
                '__adapt__': {},
                '__internal__': None,
                '__messages__': {},
                '__expando__': expando,
                '__sentinel__': False
            }

            obj.update(c_special)

            if '__metaclass__' in properties:
                obj['__metaclass__'] = properties.get('__metaclass__')

            if '_message_class' in properties or '_pipeline_class':
                obj['__impl__'] = tuple([i for i in obj['__impl__'] + [properties.get('_message_class', False), properties.get('_pipeline_class', False)]])

            for k, v in c_properties:

                # if we have explicitly set opts, overlay them on the defaults
                if isinstance(v, tuple):
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()])
                    proptype, l_opts = v
                    opts.update(l_opts)

                # just a type and no explicit options
                elif v in _BASE_TYPES:
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()])

                elif inspect.isclass(v) or inspect.isfunction(v) or inspect.ismethod(v) or inspect.ismodule(v):

                    # inline bound classes
                    if (inspect.isclass(v) and k == v.__name__) or not (inspect.isclass(v)):
                        obj[k] = v
                        continue

                else:
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()[:]])

                if propname not in obj['__lookup__']:
                    obj['__lookup__'].append(propname)
                    obj['__pmap__'].append((propname, proptype, opts))
                    obj[propname] = datastructures.PropertyDescriptor(propname, proptype, opts)
                    obj['__pclass__'].append(weakref.ref(obj[propname]))

            # freeze property lookup
            obj['__internal__'] = collections.namedtuple(name, obj['__lookup__'])
            obj['__slots__'] = tuple()

            # create adapters for impl management
            if _STORAGE_ENGINES is not None:

                obj['__adapt__'] = datastructures.DictProxy(dict([(k.lower(), v) for k, v in _STORAGE_ENGINES.items()]))

                # mix in default adapter
                if _DEFAULT_ENGINE is not None:
                    bases = obj['__bases__'] = tuple([_DEFAULT_ENGINE.model] + list(bases[:]))
                    obj['__default__'] = _DEFAULT_ENGINE.__class__.__name__.lower()

            # construct class and return
            return type(name, bases, obj)

    @classmethod
    def expando(cls, name, bases, obj):

        ''' Expando entrypoint. '''

        return cls.__new__(name, bases, obj, expando=True)

    @staticmethod
    def resolve_storage_engines():

        ''' Construct installed storage engines. '''

        global _DEFAULT_ENGINE
        global _STORAGE_ENGINES

        if len(_STORAGE_ENGINES) > 0:

            # if we've already resolved our engines, return
            return _DEFAULT_ENGINE, _STORAGE_ENGINES

        logging.info('Platform storage support enabled... considering storage adapters.')

        # load storage config
        mconfig = config.config.get('apptools.model', {})
        if 'engines' in mconfig:
            storage_engines = mconfig.get('engines')

            # import and construct each engine
            installed_engines = []
            for engine in storage_engines:
                logging.debug('Considering storage engine "%s"...' % engine.get('name'))

                # make sure this engine is enabled
                if engine.get('enabled', False):
                    epath = engine.get('path').split('.')
                    epath, ename = '.'.join(epath[0:-1]), epath[-1]

                    logging.debug('Engine "%s" is enabled. Importing.' % engine.get('name'))

                    # import the engine
                    try:
                        engine_impl_class = _loadModule((epath, ename))

                    except webapp2.ImportStringError as e:
                        logging.error("Failed to import storage adapter at name/path %s:%s." % (epath, ename))
                        if config.debug and config.strict:
                            raise

                        else:
                            continue

                    else:
                        logging.debug("Successfully imported storage adapter.")

                        if engine_impl_class.supported():
                            # construct and prepare engine
                            logging.info("Engine '%s' is supported." % ename)
                            engine_impl = engine_impl_class()
                        else:
                            logging.info("Engine '%s' is not supported in this environment." % ename)
                            continue  # advance if this engine isn't supported

                        if not hasattr(engine_impl, 'name'):
                            engine_impl.name = engine.get('name').lower()

                        if hasattr(engine_impl, 'supported'):
                            if not engine_impl.supported():
                                logging.warning('Loaded storage engine "%s" not supported in this environment.' % ename)
                                continue

                        # it's valid and constructed
                        installed_engines.append((ename, engine_impl))

                else:
                    continue

            # if there's any engines at all, copy 'em over
            if len(installed_engines) > 0:
                _STORAGE_ENGINES = dict([(k, v) for k, v in installed_engines[:]])

                if 'default' in mconfig:
                    for name, engine in _STORAGE_ENGINES.items():
                        if name.lower() == mconfig.get('default').lower():
                            _DEFAULT_ENGINE = engine
                            break

                elif 'default' not in mconfig or _DEFAULT_ENGINE is None:
                    try:
                        from google.appengine.ext import ndb
                        assert 'ndb' in _STORAGE_ENGINES

                    except (ImportError, AssertionError) as e:
                        _DEFAULT_ENGINE = _STORAGE_ENGINES.items()[0][1]

            return _DEFAULT_ENGINE, _STORAGE_ENGINES


## ThinKey
# Base class used for ThinModel keys.
class ThinKey(object): pass


## ThinModel
# Base class for flexible, universal, efficient datamodels.
class ThinModel(_AppToolsModel, MessageConverter, PipelineTrigger):

    ''' Base model class for all AppTools models. '''

    __metaclass__ = ThinModelFactory


## BaseModel
# This is the root base model for all AppTools-based models.
class BaseModel(ThinModel):

    ''' This is the root base model for all AppTools-based models. '''

## BaseExpando
# This is the root base expando for all expando-based models.
class BaseExpando(ThinModel):

    ''' This is the root base model for all AppTools-based expandos. '''


if _GAE:

    ## Property, Key & Model Classes

    if _NDB:

        # NDB/New Style
        ndb = ObjectProxy({

                'key': key.Key,
                'model': ThinModel,
                'Property': nndb.Property,
                'StringProperty': nndb.StringProperty,
                'TextProperty': nndb.TextProperty,
                'BlobProperty': nndb.BlobProperty,
                'IntegerProperty': nndb.IntegerProperty,
                'FloatProperty': nndb.FloatProperty,
                'BooleanProperty': nndb.BooleanProperty,
                'BlobKeyProperty': nndb.BlobKeyProperty,
                'DateTimeProperty': nndb.DateTimeProperty,
                'TimeProperty': nndb.TimeProperty,
                'GeoPt': nndb.GeoPt,
                'GeoPtProperty': nndb.GeoPtProperty,
                'KeyProperty': nndb.KeyProperty,
                'UserProperty': nndb.UserProperty,
                'JsonProperty': nndb.JsonProperty,
                'PickleProperty': nndb.PickleProperty,
                'StructuredProperty': nndb.StructuredProperty,
                'LocalStructuredProperty': nndb.LocalStructuredProperty,
                'ComputedProperty': nndb.ComputedProperty,
                'GenericProperty': nndb.GenericProperty

        }, case_sensitive=False)

    # DB/Old Style
    db = ObjectProxy({

            'key': ldb.Key,
            'model': BaseModel,
            'StringProperty': ldb.StringProperty,
            'ByteStringProperty': ldb.ByteStringProperty,
            'BooleanProperty': ldb.BooleanProperty,
            'IntegerProperty': ldb.IntegerProperty,
            'FloatProperty': ldb.FloatProperty,
            'DateTimeProperty': ldb.DateTimeProperty,
            'DateProperty': ldb.DateProperty,
            'TimeProperty': ldb.TimeProperty,
            'ListProperty': ldb.ListProperty,
            'StringListProperty': ldb.StringListProperty,
            'ReferenceProperty': ldb.ReferenceProperty,
            'BlobReferenceProperty': blobstore.BlobReferenceProperty,
            'UserProperty': ldb.UserProperty,
            'BlobProperty': ldb.BlobProperty,
            'TextProperty': ldb.TextProperty,
            'CategoryProperty': ldb.CategoryProperty,
            'LinkProperty': ldb.LinkProperty,
            'EmailProperty': ldb.EmailProperty,
            'GeoPtProperty': ldb.GeoPtProperty,
            'IMProperty': ldb.IMProperty,
            'PhoneNumberProperty': ldb.PhoneNumberProperty,
            'PostalAddressProperty': ldb.PostalAddressProperty,
            'RatingProperty': ldb.RatingProperty

    }, case_sensitive=False)

