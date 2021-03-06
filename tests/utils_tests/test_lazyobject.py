from __future__ import unicode_literals

import copy
import pickle
import sys
from unittest import TestCase

from django.utils import six
from django.utils.functional import LazyObject, SimpleLazyObject, empty


class Foo(object):
    """
    A simple class with just one attribute.
    """
    foo = 'bar'

    def __eq__(self, other):
        return self.foo == other.foo


class LazyObjectTestCase(TestCase):
    def lazy_wrap(self, wrapped_object):
        """
        Wrap the given object into a LazyObject
        """
        class AdHocLazyObject(LazyObject):
            def _setup(self):
                self._wrapped = wrapped_object

        return AdHocLazyObject()

    def test_getattr(self):
        obj = self.lazy_wrap(Foo())
        self.assertEqual(obj.foo, 'bar')

    def test_setattr(self):
        obj = self.lazy_wrap(Foo())
        obj.foo = 'BAR'
        obj.bar = 'baz'
        self.assertEqual(obj.foo, 'BAR')
        self.assertEqual(obj.bar, 'baz')

    def test_setattr2(self):
        # Same as test_setattr but in reversed order
        obj = self.lazy_wrap(Foo())
        obj.bar = 'baz'
        obj.foo = 'BAR'
        self.assertEqual(obj.foo, 'BAR')
        self.assertEqual(obj.bar, 'baz')

    def test_delattr(self):
        obj = self.lazy_wrap(Foo())
        obj.bar = 'baz'
        self.assertEqual(obj.bar, 'baz')
        del obj.bar
        with self.assertRaises(AttributeError):
            obj.bar

    def test_cmp(self):
        obj1 = self.lazy_wrap('foo')
        obj2 = self.lazy_wrap('bar')
        obj3 = self.lazy_wrap('foo')
        self.assertEqual(obj1, 'foo')
        self.assertEqual(obj1, obj3)
        self.assertNotEqual(obj1, obj2)
        self.assertNotEqual(obj1, 'bar')

    def test_bytes(self):
        obj = self.lazy_wrap(b'foo')
        self.assertEqual(bytes(obj), b'foo')

    def test_text(self):
        obj = self.lazy_wrap('foo')
        self.assertEqual(six.text_type(obj), 'foo')

    def test_bool(self):
        # Refs #21840
        for f in [False, 0, (), {}, [], None, set()]:
            self.assertFalse(self.lazy_wrap(f))
        for t in [True, 1, (1,), {1: 2}, [1], object(), {1}]:
            self.assertTrue(t)

    def test_dir(self):
        obj = self.lazy_wrap('foo')
        self.assertEqual(dir(obj), dir('foo'))

    def test_len(self):
        for seq in ['asd', [1, 2, 3], {'a': 1, 'b': 2, 'c': 3}]:
            obj = self.lazy_wrap(seq)
            self.assertEqual(len(obj), 3)

    def test_class(self):
        self.assertIsInstance(self.lazy_wrap(42), int)

        class Bar(Foo):
            pass

        self.assertIsInstance(self.lazy_wrap(Bar()), Foo)

    def test_hash(self):
        obj = self.lazy_wrap('foo')
        d = {}
        d[obj] = 'bar'
        self.assertIn('foo', d)
        self.assertEqual(d['foo'], 'bar')

    def test_contains(self):
        test_data = [
            ('c', 'abcde'),
            (2, [1, 2, 3]),
            ('a', {'a': 1, 'b': 2, 'c': 3}),
            (2, {1, 2, 3}),
        ]
        for needle, haystack in test_data:
            self.assertIn(needle, self.lazy_wrap(haystack))

        # __contains__ doesn't work when the haystack is a string and the needle a LazyObject
        for needle_haystack in test_data[1:]:
            self.assertIn(self.lazy_wrap(needle), haystack)
            self.assertIn(self.lazy_wrap(needle), self.lazy_wrap(haystack))

    def test_getitem(self):
        obj_list = self.lazy_wrap([1, 2, 3])
        obj_dict = self.lazy_wrap({'a': 1, 'b': 2, 'c': 3})

        self.assertEqual(obj_list[0], 1)
        self.assertEqual(obj_list[-1], 3)
        self.assertEqual(obj_list[1:2], [2])

        self.assertEqual(obj_dict['b'], 2)

        with self.assertRaises(IndexError):
            obj_list[3]

        with self.assertRaises(KeyError):
            obj_dict['f']

    def test_setitem(self):
        obj_list = self.lazy_wrap([1, 2, 3])
        obj_dict = self.lazy_wrap({'a': 1, 'b': 2, 'c': 3})

        obj_list[0] = 100
        self.assertEqual(obj_list, [100, 2, 3])
        obj_list[1:2] = [200, 300, 400]
        self.assertEqual(obj_list, [100, 200, 300, 400, 3])

        obj_dict['a'] = 100
        obj_dict['d'] = 400
        self.assertEqual(obj_dict, {'a': 100, 'b': 2, 'c': 3, 'd': 400})

    def test_delitem(self):
        obj_list = self.lazy_wrap([1, 2, 3])
        obj_dict = self.lazy_wrap({'a': 1, 'b': 2, 'c': 3})

        del obj_list[-1]
        del obj_dict['c']
        self.assertEqual(obj_list, [1, 2])
        self.assertEqual(obj_dict, {'a': 1, 'b': 2})

        with self.assertRaises(IndexError):
            del obj_list[3]

        with self.assertRaises(KeyError):
            del obj_dict['f']

    def test_iter(self):
        # LazyObjects don't actually implements __iter__ but you can still
        # iterate over them because they implement __getitem__
        obj = self.lazy_wrap([1, 2, 3])
        for expected, actual in zip([1, 2, 3], obj):
            self.assertEqual(expected, actual)

    def test_pickle(self):
        # See ticket #16563
        obj = self.lazy_wrap(Foo())
        pickled = pickle.dumps(obj)
        unpickled = pickle.loads(pickled)
        self.assertIsInstance(unpickled, Foo)
        self.assertEqual(unpickled, obj)
        self.assertEqual(unpickled.foo, obj.foo)

    def test_deepcopy(self):
        # Check that we *can* do deep copy, and that it returns the right
        # objects.

        l = [1, 2, 3]

        obj = self.lazy_wrap(l)
        len(l)  # forces evaluation
        obj2 = copy.deepcopy(obj)

        self.assertIsInstance(obj2, list)
        self.assertEqual(obj2, [1, 2, 3])

    def test_deepcopy_no_evaluation(self):
        # copying doesn't force evaluation

        l = [1, 2, 3]

        obj = self.lazy_wrap(l)
        obj2 = copy.deepcopy(obj)

        # Copying shouldn't force evaluation
        self.assertIs(obj._wrapped, empty)
        self.assertIs(obj2._wrapped, empty)


class SimpleLazyObjectTestCase(LazyObjectTestCase):
    # By inheriting from LazyObjectTestCase and redefining the lazy_wrap()
    # method which all testcases use, we get to make sure all behaviors
    # tested in the parent testcase also apply to SimpleLazyObject.
    def lazy_wrap(self, wrapped_object):
        return SimpleLazyObject(lambda: wrapped_object)

    def test_repr(self):
        # First, for an unevaluated SimpleLazyObject
        obj = self.lazy_wrap(42)
        # __repr__ contains __repr__ of setup function and does not evaluate
        # the SimpleLazyObject
        six.assertRegex(self, repr(obj), '^<SimpleLazyObject:')
        self.assertIs(obj._wrapped, empty)  # make sure evaluation hasn't been triggered

        self.assertEqual(obj, 42)  # evaluate the lazy object
        self.assertIsInstance(obj._wrapped, int)
        self.assertEqual(repr(obj), '<SimpleLazyObject: 42>')

    def test_trace(self):
        # See ticket #19456
        old_trace_func = sys.gettrace()
        try:
            def trace_func(frame, event, arg):
                frame.f_locals['self'].__class__
                if old_trace_func is not None:
                    old_trace_func(frame, event, arg)
            sys.settrace(trace_func)
            self.lazy_wrap(None)
        finally:
            sys.settrace(old_trace_func)

    def test_none(self):
        i = [0]

        def f():
            i[0] += 1
            return None

        x = SimpleLazyObject(f)
        self.assertEqual(str(x), "None")
        self.assertEqual(i, [1])
        self.assertEqual(str(x), "None")
        self.assertEqual(i, [1])

    def test_dict(self):
        # See ticket #18447
        lazydict = SimpleLazyObject(lambda: {'one': 1})
        self.assertEqual(lazydict['one'], 1)
        lazydict['one'] = -1
        self.assertEqual(lazydict['one'], -1)
        self.assertIn('one', lazydict)
        self.assertNotIn('two', lazydict)
        self.assertEqual(len(lazydict), 1)
        del lazydict['one']
        with self.assertRaises(KeyError):
            lazydict['one']

    def test_list_set(self):
        lazy_list = SimpleLazyObject(lambda: [1, 2, 3, 4, 5])
        lazy_set = SimpleLazyObject(lambda: {1, 2, 3, 4})
        self.assertIn(1, lazy_list)
        self.assertIn(1, lazy_set)
        self.assertNotIn(6, lazy_list)
        self.assertNotIn(6, lazy_set)
        self.assertEqual(len(lazy_list), 5)
        self.assertEqual(len(lazy_set), 4)
