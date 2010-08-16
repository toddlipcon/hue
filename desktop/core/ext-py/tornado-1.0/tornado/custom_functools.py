# This code is taken from tornado/compat.py from rbu/tornado on github
# The URL for this file is http://github.com/rbu/tornado/blob/master/tornado/compat.py
# The URL for the repository is http://github.com/rbu/tornado.git
def partial(func, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = keywords.copy()
        newkeywords.update(fkeywords)
        return func(*(args + fargs), **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc

# ---- copied from Python 2.6 functools ------------------------------------
# Written by Nick Coghlan <ncoghlan at gmail.com>
# Copyright (C) 2006 Python Software Foundation.
# Distributed under the terms of the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
WRAPPER_UPDATES = ('__dict__',)
def update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    for attr in assigned:
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper

def wraps(wrapped,
          assigned = WRAPPER_ASSIGNMENTS,
          updated = WRAPPER_UPDATES):
    return partial(update_wrapper, wrapped=wrapped,
                   assigned=assigned, updated=updated)
