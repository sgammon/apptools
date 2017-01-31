# -*- coding: utf-8 -*-

'''

    apptools model: queries

    this module provides functionality to the :py:mod:`apptools` model layer
    for querying across datastores and adapters that support the interface
    :py:class:`IndexedModelAdapter`.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''


__version__ = 'v2'


# stdlib
import abc
import operator

# apptools utils
from apptools.util import datastructures


## Globals / Constants

# Filter components
_TARGET_KEY = datastructures.Sentinel('KEY')
PROPERTY = datastructures.Sentinel('PROPERTY')
KEY_KIND = datastructures.Sentinel('KEY_KIND')
KEY_ANCESTOR = datastructures.Sentinel('KEY_ANCESTOR')

# Sort directions
ASCENDING = ASC = datastructures.Sentinel('ASCENDING')
DESCENDING = DSC = datastructures.Sentinel('DESCENDING')

# Query operators
EQUALS = EQ = datastructures.Sentinel('EQUALS')
NOT_EQUALS = NE = datastructures.Sentinel('NOT_EQUALS')
LESS_THAN = LT = datastructures.Sentinel('LESS_THAN')
LESS_THAN_EQUAL_TO = LE = datastructures.Sentinel('LESS_THAN_EQUAL_TO')
GREATER_THAN = GT = datastructures.Sentinel('GREATER_THAN')
GREATER_THAN_EQUAL_TO = GE = datastructures.Sentinel('GREATER_THAN_EQUAL_TO')
CONTAINS = IN = datastructures.Sentinel('CONTAINS')

# Operator Constants
_operator_map = {
    EQUALS: operator.eq,
    NOT_EQUALS: operator.ne,
    LESS_THAN: operator.lt,
    LESS_THAN_EQUAL_TO: operator.le,
    GREATER_THAN: operator.gt,
    GREATER_THAN_EQUAL_TO: operator.ge,
    CONTAINS: operator.contains
}

_operator_strings = {
    EQUALS: '==',
    NOT_EQUALS: '!=',
    LESS_THAN: '<',
    LESS_THAN_EQUAL_TO: '<=',
    GREATER_THAN: '>',
    GREATER_THAN_EQUAL_TO: '>=',
    CONTAINS: 'IN'
}


## QueryOptions
# Holds a reusable set of options for a :py:class:`Query`.
class QueryOptions(object):

    ''' Holds a re-usable set of options for a
        :py:class:`Query`. '''

    # == Options == #
    __slots__ = options = frozenset((
        '_keys_only',
        '_ancestor',
        '_limit',
        '_offset',
        '_projection',
        '_hint',
        '_plan',
        '_cursor'
    ))

    # == Option Defaults == #
    _defaults = {
        '_keys_only': False,
        '_ancestor': None,
        '_limit': -1,
        '_offset': 0,
        '_projection': None,
        '_hint': None,
        '_plan': None,
        '_cursor': None
    }

    ## == Internal Methods == ##
    def __init__(self, **kwargs):

        ''' Initialize this :py:class:`QueryOptions`.
            Map ``kwargs`` into local data properties
            that are abstracted behind getters/setters
            at the class level.

            :param **kwargs: Keyword argument options.
            Valid keys are listed in :py:attr:`__slots__`.

            :raises AttributeError: In the case that
            an invalid config key is found in ``kwargs``.
            Passed-up from :py:meth:`_set_option`.

            :returns: Nothing, as this is a constructor. '''

        map(lambda bundle: self._set_option(*bundle),
            map(lambda slot: (slot, kwargs.get(slot, datastructures._EMPTY)), self.__slots__))

    ## == Protected Methods == ##
    def _set_option(self, name, value=datastructures._EMPTY):

        ''' Set the value of an option local to this
            :py:class:`QueryOptions` object. Calling
            without a ``value`` (which defaults to
            ``None``) resets the target key's value.

            :param name: Name (``str``) of the internal
            property we're setting.

            :param value: Value to set the property to.
            Defaults to ``None``.

            :raises ValueError: If ``name`` is not a
            ``basestring`` descendent.

            :raises AttributeError: If ``name`` is not
            a valid internal property name.

            :returns: ``self``, for chainability. '''

        if not isinstance(name, basestring):
            raise ValueError('Argument `name` of `_set_option` must '
                             'be a string internal propery name. Got: "%s".' % str(name))

        name = '_' + name if name[0] != '_' else name  # build internal name

        if name not in self.__slots__:
            raise AttributeError('`QueryOptions` object has no option by '
                                 'the name "%s".' % name)

        setattr(self, name, value)  # set value and return
        return self

    def _get_option(self, name, default=datastructures._EMPTY):

        ''' Get the value of an option local to this
            :py:class:`QueryOptions` object.

            :param name: Name (``str``) of the internal
            property we're getting.

            :param default: Default value to return
            if no value was found at ``name``. Defaults
            to ``None``.

            :raises ValueError: If ``name`` is not
            a ``basestring`` descendent.

            :raises AttributeError: If ``name`` is not
            a valid internal property name.

            :returns: Configuration value at ``name``,
            or ``default`` if no value was found. '''

        if not isinstance(name, basestring):
            raise ValueError('Argument `name` of `_get_option` must '
                             'be a string internal property name. Got: "%s".' % str(name))

        name = '_' + name  # build internal name

        if name not in self.__slots__:
            raise AttributeError('`QueryOptions` object has no option by '
                                 'the name "%s".' % name)

        val = getattr(self, name)  # get value

        # return default value if empty slot was found, otherwise return value
        if val is datastructures._EMPTY:
            if default is datastructures._EMPTY:
                return self._defaults.get(name, None)
            return default
        return val

    ## == Public Properties == ##

    # ``keys_only`` flag - return keys instead of entities
    keys_only = property(lambda self: self._get_option('keys_only'))

    # ``ancestor`` filter - restrict results by key ancestry
    ancestor = property(lambda self: self._get_option('ancestor'))

    # ``limit`` - return a limited number of query results
    limit = property(lambda self: self._get_option('limit'))

    # ``offset`` - skip an amount of records before building results
    offset = property(lambda self: self._get_option('offset'))

    # ``projection`` - retrieve entity values from indexes while fulfilling query
    projection = property(lambda self: self._get_option('projection'))

    # ``plan`` - cached plan to fulfill the query (optional)
    plan = property(lambda self: self._get_option('plan'),
                    lambda self, value: self._set_option('plan', value))

    # ``cursor`` - result cursor, for paging or long queries (optional)
    cursor = property(lambda self: self._get_option('cursor'),
                      lambda self, value: self._set_option('cursor', value))


## AbstractQuery
# Specifies the interface for an ``apptools`` model API query class.
class AbstractQuery(object):

    ''' Specifies base structure and interface for all
        apptools query classes. '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def filter(self, expression):

        ''' Add a filter to the active :py:class:`Query`
            at ``self``.

            :param expression: Filter expression to apply during query planning.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`filter` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def sort(self, expression):

        ''' Add a sort directive to the active :py:class:`Query`
            at ``self``.

            :param expression: Sort expression to apply to the target result set.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`sort` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def hint(self, directive):

        ''' Pass a hint to the query-planning subsystem for how
            this query could most efficiently be satisfied.

            :param expression: Hint expression to take into consideration.
            :raises NotImplementedError: Always, as this method is abstract.
            :returns: ``self``, for chainability. '''

        raise NotImplementedError('`hint` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def fetch(self, **options):

        ''' Fetch results for a :py:class:`Query`, via the
            underlying driver's :py:meth:`execute_query` method.

            :param **options: Query options to build into
            a :py:class:`QueryOptions` object.

            :raises NotImplementedError: Always, as this
            method is abstract.

            :returns: Iterable (``list``) of matching :py:class:`model.Model`
            entities (or :py:class:`model.Key` objects if ``keys_only`` is
            truthy) yielded from current :py:class:`Query`, or an empty ``list``
            if no results were found. '''

        raise NotImplementedError('`fetch` is abstract and may not be invoked directly.')

    @abc.abstractmethod
    def get(self, **options):

        ''' Get a single result (by default, the first)
            matching a :py:class:`Query`.

            :param **options: Query options to build into
            a :py:class:`QueryOptions` object.

            :raises NotImplementedError: Always, as this
            method is abstract.

            :returns: Single result :py:class:`model.Model`
            (or :py:class:`model.Key` if ``keys_only`` is truthy)
            matching the current :py:class:`Query`, or ``None``
            if no matching entities were found. '''

        raise NotImplementedError('`fetch` is abstract and may not be invoked directly.')


## Query
# Top-level specification class for a datastore query.
class Query(AbstractQuery):

    ''' Top-level class representing a specification for
        a query across data accessible to the apptools
        model layer, using an adapter that supports the
        :py:class:`IndexedModelAdapter` interface. '''

    kind = None  # model kind
    sorts = None  # sort directives
    options = None  # attached query options
    filters = None  # filter directives

    def __init__(self, kind=None, filters=None, sorts=None, **kwargs):

        ''' Initialize this :py:class:`Query`, assigning
            any properties/config passed in via ``kwargs``
            and such.

            :returns: Nothing, as this is an initializer. '''

        if filters:
            if not isinstance(filters, (list, tuple)):
                filters = [filters]
        if sorts:
            if not isinstance(sorts, (list, tuple)):
                sorts = [sorts]

        options = kwargs.get('options', QueryOptions(**kwargs))
        self.kind, self.filters, self.sorts, self.options = kind, filters or [], sorts or [], options

    def __repr__(self):

        ''' Generate a string representation
            of this :py:class:`Query`.

            :returns: String representation of
            the current :py:class:`Query`. '''

        return "Query(%s, filter=%s, sort=%s)" % (
            self.kind.kind(),
            '[' + ','.join((str(f) for f in self.filters)) + ']',
            '[' + ','.join((str(s) for s in self.sorts)) + ']'
        )

    # @TODO(sgammon): async methods to execute
    def _execute(self, **options):

        ''' Internal method to execute a query,
            optionally along with some override
            options.

            .. note: This method will eventually
                     accompany an async equivalent,
                     which this will make use of
                     under-the-hood.

            :param **options: Keyword arguments
            of query config (i.e. valid and registered
            on :py:class:`QueryOptions`) to pass
            to the options object built to execute
            the query.

            :raises AttributeError: In the case that
            an invalid/unknown query configuration
            key is encountered. Passed up from
            :py:class:`QueryOptions`.

            :raises NotImplementedError: In the case
            that a ``kindless`` or ``projection``
            query is encountered, as those features
            are not yet supported.

            :returns: Synchronously-retrieved results
            to this :py:class:`Query`. '''

        ## build query options
        options = options.get('options', QueryOptions(**options))

        ## fail for projection queries
        if options.projection:
            raise NotImplementedError('Projection queries are not yet supported.')

        if self.kind:  # kinded query

            # delegate to driver
            return self.kind.__adapter__.execute_query(self.kind, (self.filters, self.sorts), options)

        else:

            # kindless queries are not yet supported
            raise NotImplementedError('Kindless queries are not yet supported.')

    def filter(self, expression):

        ''' Add a filter to this :py:class:`Query`.

            :param expression: Expression descriptor of
            type :py:class:`Filter`.

            :raises:
            :returns: '''

        if isinstance(expression, Filter):
            self.filters.append(expression)
        else:
            raise NotImplementedError('Query method `filter` does not yet support non-'
                                      '`Filter` component types.')
        return self

    def sort(self, expression):

        ''' Add a sort order to this :py:class:`Query`.

            :param expression: Expression descriptor of
            type :py:class:`Sort`.

            :raises:
            :returns: '''

        if isinstance(expression, Sort):
            self.sorts.append(expression)
        else:
            raise NotImplementedError('Query method `sort` does not yet support non-'
                                      '`Sort` component types.')
        return self

    def hint(self, directive):

        ''' Provide an external hint to the query
            planning logic about how to plan the
            query.

            Currently stubbed.

            :raises NotImplementedError: Always,
            as this method is currently stubbed.

            :returns: ``self``, for chainability. '''

        # @TODO(sgammon): fill out query hinting logic
        raise NotImplementedError('Query method `hint` is currently stubbed.')

    def get(self, **options):

        ''' Get a single result (by default, the first)
            matching a :py:class:`Query`.

            :param **options: Accepts any valid and
            registered options on :py:class:`QueryOptions`.

            :returns: Single result :py:class:`model.Model`
            (or :py:class:`model.Key` if ``keys_only`` is truthy)
            matching the current :py:class:`Query`, or ``None``
            if no matching entities were found. '''

        return self._execute(options=QueryOptions(**options))

    def fetch(self, **options):

        ''' Fetch results for the currently-built
            :py:class:`Query`, executing it across
            the attached ``kind``'s attached model
            adapter.

            :param **options: Accepts any valid and
            registered options on :py:class:`QueryOptions`.

            :returns: Iterable (``list``) of matching model
            entities. '''

        return self._execute(options=QueryOptions(**options))

    def fetch_page(self, **options):

        ''' Fetch a page of results, potentially
            as the next in a sequence of page
            requests.

            :param **options: Accepts any valid and
            registered options on :py:class:`QueryOptions`.

            :param page: '''

        # @TODO(sgammon): build out paging support
        raise NotImplementedError('Query method `fetch_page` is currently stubbed.')


## QueryComponent
# Abstract parent for components of a :py:class:`Query`.
class QueryComponent(object):

    ''' Top-level abstract class for a component of a
        :py:class:`Query`, which is usually an attached
        specification like a :py:class:`Filter` or
        :py:class:`Sort`. '''

    __metaclass__ = abc.ABCMeta

    ## == Component State == ##
    kind = None  # kind of property
    target = None  # property to operate on
    operator = None  # operator selection

    ## == Constants == ##
    PROPERTY = PROPERTY
    KEY_KIND = KEY_KIND
    KEY_ANCESTOR = KEY_ANCESTOR


## Filter
# Expresses an individual filter in a :py:class:`Query`.
class Filter(QueryComponent):

    ''' Query component specification parent for a generic
        filter, used to traverse indexes and find entities
        to return that match. '''

    ## == Filter State == ##
    value = None  # value to match

    ## == Operators == ##
    EQUALS = EQ = EQUALS
    NOT_EQUALS = NEQ = NOT_EQUALS
    LESS_THAN = LT = LESS_THAN
    LESS_THAN_EQUAL_TO = LE = LESS_THAN_EQUAL_TO
    GREATER_THAN = GT = GREATER_THAN
    GREATER_THAN_EQUAL_TO = GE = GREATER_THAN_EQUAL_TO
    CONTAINS = IN = CONTAINS

    def __init__(self, property, value, type=PROPERTY, operator=EQUALS):

        ''' Initialize this :py:class:`Filter`. '''

        from apptools import model
        value = model.AbstractModel._PropertyValue(value, False)  # make a value
        self.target, self.value, self.kind, self.operator = prop, value, type, operator

    def __repr__(self):

        ''' Generate a string representation of
            this :py:class:`Filter`. '''

        return 'Filter(%s %s %s)' % (self.target.name, _operator_strings[self.operator], str(self.value))


## KeyFilter
# Expresses a filter that applies to an entity's :py:class:`Key`.
class KeyFilter(Filter):

    ''' Expresses a filter that applies to an entity's
        associated :py:class:`model.Key`, or one of the
        member components thereof. '''

    # == Constants == #
    KIND = KEY_KIND
    ANCESTOR = KEY_ANCESTOR


## Sort
# Expresses a sort directive to apply to the target resultset.
class Sort(QueryComponent):

    ''' Expresses a directive to sort resulting entities
        by a property in a given direction. '''

    ## == Sort Orders == ##
    ASC = ASCENDING = ASC
    DSC = DESCENDING = DSC

    def __init__(self, prop, type=PROPERTY, operator=ASC):

        ''' Initialize this :py:class:`Sort`. '''

        self.target, self.kind, self.operator = prop, type, operator

    def __repr__(self):

        ''' Generate a string representation of
            this :py:class:`Sort`. '''

        return 'Sort(%s, %s)' % (self.target.name, self.direction)
