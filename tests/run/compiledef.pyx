__doc__ = u"""
    >>> dt
    True
    >>> df
    False
    >>> t
    True
    >>> f
    False
    >>> boolexpr
    True
    >>> num6
    6
    >>> intexpr
    10
"""

DEF c_t = True
DEF c_f = False
DEF c_boolexpr = c_t and True and not (c_f or False)

DEF c_num6 = 2*3
DEF c_intexpr = c_num6 + 4

dt = c_dt
df = c_df

t = c_t
f = c_f
boolexpr = c_boolexpr
num6 = c_num6
intexpr = c_intexpr
