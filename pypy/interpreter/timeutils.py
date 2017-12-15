"""
Access to the time module's high-resolution monotonic clock
"""
import math
from rpython.rlib.rarithmetic import (
    r_longlong, ovfcheck, ovfcheck_float_to_longlong)
from pypy.interpreter.error import oefmt

SECS_TO_NS = 10 ** 9
MS_TO_NS = 10 ** 6
US_TO_NS = 10 ** 3

def monotonic(space):
    from pypy.module.time import interp_time
    if interp_time.HAS_MONOTONIC:
        w_res = interp_time.monotonic(space)
    else:
        w_res = interp_time.gettimeofday(space)
    return space.float_w(w_res)   # xxx back and forth

def timestamp_w(space, w_secs):
    if space.isinstance_w(w_secs, space.w_float):
        secs = space.float_w(w_secs)
        result_float = math.ceil(secs * SECS_TO_NS)
        try:
            return ovfcheck_float_to_longlong(result_float)
        except OverflowError:
            raise oefmt(space.w_OverflowError,
                "timestamp %R too large to convert to C _PyTime_t", w_secs)
    else:
        sec = space.int_w(w_secs)
        try:
            result = ovfcheck(sec * SECS_TO_NS)
        except OverflowError:
            raise oefmt(space.w_OverflowError,
                "timestamp too large to convert to C _PyTime_t")
        return r_longlong(result)
