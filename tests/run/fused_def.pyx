# mode: run

"""
Test Python def functions without extern types
"""

cy = __import__("cython")
cimport cython

cdef class Base(object):
    def __repr__(self):
        return type(self).__name__


cdef class ExtClassA(Base):
    pass

cdef class ExtClassB(Base):
    pass

cdef enum MyEnum:
    entry0
    entry1
    entry2
    entry3
    entry4

ctypedef fused fused_t:
    str
    int
    long
    complex
    ExtClassA
    ExtClassB
    MyEnum


f = 5.6
i = 9

def opt_func(fused_t obj, cython.floating myf = 1.2, cython.integral myi = 7):
    """
    Test runtime dispatch, indexing of various kinds and optional arguments

    >>> opt_func("spam", f, i)
    str object double long
    spam 5.60 9 5.60 9
    >>> opt_func[str, float, int]("spam", f, i)
    str object float int
    spam 5.60 9 5.60 9
    >>> opt_func["str, double, long"]("spam", f, i)
    str object double long
    spam 5.60 9 5.60 9
    >>> opt_func[str, float, cy.int]("spam", f, i)
    str object float int
    spam 5.60 9 5.60 9


    >>> opt_func(ExtClassA(), f, i)
    ExtClassA double long
    ExtClassA 5.60 9 5.60 9
    >>> opt_func[ExtClassA, float, int](ExtClassA(), f, i)
    ExtClassA float int
    ExtClassA 5.60 9 5.60 9
    >>> opt_func["ExtClassA, double, long"](ExtClassA(), f, i)
    ExtClassA double long
    ExtClassA 5.60 9 5.60 9

    >>> opt_func(ExtClassB(), f, i)
    ExtClassB double long
    ExtClassB 5.60 9 5.60 9
    >>> opt_func[ExtClassB, cy.double, cy.long](ExtClassB(), f, i)
    ExtClassB double long
    ExtClassB 5.60 9 5.60 9

    >>> opt_func(10, f)
    long double long
    10 5.60 7 5.60 9
    >>> opt_func[int, float, int](10, f)
    int float int
    10 5.60 7 5.60 9

    >>> opt_func(10 + 2j, myf = 2.6)
    double complex double long
    (10+2j) 2.60 7 5.60 9
    >>> opt_func[cy.py_complex, float, int](10 + 2j, myf = 2.6)
    double complex float int
    (10+2j) 2.60 7 5.60 9
    >>> opt_func[cy.doublecomplex, cy.float, cy.int](10 + 2j, myf = 2.6)
    double complex float int
    (10+2j) 2.60 7 5.60 9

    >>> opt_func(object(), f)
    Traceback (most recent call last):
      ...
    TypeError: Function call with ambiguous argument types
    >>> opt_func[ExtClassA, cy.float, cy.long](object(), f)
    Traceback (most recent call last):
      ...
    TypeError: Argument 'obj' has incorrect type (expected fused_def.ExtClassA, got object)
    """
    print cython.typeof(obj), cython.typeof(myf), cython.typeof(myi)
    print obj, "%.2f" % myf, myi, "%.2f" % f, i


def test_opt_func():
    """
    >>> test_opt_func()
    str object double long
    ham 5.60 4 5.60 9
    """
    opt_func("ham", f, entry4)

def args_kwargs(fused_t obj, cython.floating myf = 1.2, *args, **kwargs):
    """
    >>> args_kwargs("foo")
    str object double
    foo 1.20 5.60 () {}

    >>> args_kwargs("eggs", f, 1, 2, [], d={})
    str object double
    eggs 5.60 5.60 (1, 2, []) {'d': {}}

    >>> args_kwargs[str, float]("eggs", f, 1, 2, [], d={})
    str object float
    eggs 5.60 5.60 (1, 2, []) {'d': {}}

    """
    print cython.typeof(obj), cython.typeof(myf)
    print obj, "%.2f" % myf, "%.2f" % f, args, kwargs
