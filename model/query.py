# -*- coding: utf-8 -*-

"""
This module provides functionality to the :py:mod:`apptools` model layer
for querying across datastores and adapters that support the interface
:py:class:`IndexedModelAdapter`.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

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


## Query
# Top-level specification class for a datastore query.
class Query(AbstractQuery):

    ''' Top-level class representing a specification for
        a query across data accessible to the apptools
        model layer, using an adapter that supports the
        :py:class:`IndexedModelAdapter` interface. '''

    kind = None  # model kind
    sorts = None  # sort directives
    config = None  # arbitrary config
    filters = None  # filter directives

    def __init__(self, kind=None, filters=None, sorts=None, **kwargs):

        ''' Initialize this :py:class:`Query`, assigning
            any properties/config passed in via ``kwargs``
            and such.

            :returns: Nothing, as this is an initializer. '''

        self.kind, self.filters, self.sorts, self.config = kind, filters or [], sorts or [], kwargs

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

    def fetch(self, limit=1000, offset=0):

        ''' Fetch results for the currently-built
            :py:class:`Query`, executing it across
            the attached ``kind``'s attached model
            adapter.

            :param limit: Numerical (``int`` or ``long``)
            limit of results to return.

            :param offset: Numerical (``int`` or ``long``)
            results to skip before returning.

            :returns: Iterable (``list``) of matching model
            entities. '''

        import pdb; pdb.set_trace()


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

    def __init__(self, prop, value, type=PROPERTY, operator=EQUALS):

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
