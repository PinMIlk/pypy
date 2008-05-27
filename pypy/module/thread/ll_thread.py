
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.extfunc import genericcallable
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import llmemory
import py, os
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rlib.debug import ll_assert
from pypy.tool import autopath
from distutils import sysconfig
python_inc = sysconfig.get_python_inc()

class error(Exception):
    pass

eci = ExternalCompilationInfo(
    includes = ['src/thread.h'],
    separate_module_sources = [''],
    include_dirs = [str(py.path.local(autopath.pypydir).join('translator', 'c')),
                    python_inc],
    export_symbols = ['RPyThreadGetIdent', 'RPyThreadLockInit',
                      'RPyThreadAcquireLock', 'RPyThreadReleaseLock',
                      'RPyThreadFusedReleaseAcquireLock',]
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           **kwds)

def _emulated_start_new_thread(func):
    import thread
    try:
        ident = thread.start_new_thread(func, ())
    except thread.error:
        ident = -1
    return rffi.cast(rffi.INT, ident)

CALLBACK = lltype.Ptr(lltype.FuncType([], lltype.Void))
c_thread_start = llexternal('RPyThreadStart', [CALLBACK], rffi.INT,
                            _callable=_emulated_start_new_thread)
c_thread_get_ident = llexternal('RPyThreadGetIdent', [], rffi.INT)

TLOCKP = rffi.COpaquePtr('struct RPyOpaque_ThreadLock',
                          compilation_info=eci)

c_thread_lock_init = llexternal('RPyThreadLockInit', [TLOCKP], lltype.Void)
c_thread_acquirelock = llexternal('RPyThreadAcquireLock', [TLOCKP, rffi.INT],
                                  rffi.INT)
c_thread_releaselock = llexternal('RPyThreadReleaseLock', [TLOCKP], lltype.Void)

# another set of functions, this time in versions that don't cause the
# GIL to be released.  To use to handle the GIL lock itself.
c_thread_acquirelock_NOAUTO = llexternal('RPyThreadAcquireLock',
                                         [TLOCKP, rffi.INT], rffi.INT,
                                         threadsafe=False)
c_thread_releaselock_NOAUTO = llexternal('RPyThreadReleaseLock',
                                         [TLOCKP], lltype.Void,
                                         threadsafe=False)
c_thread_fused_releaseacquirelock_NOAUTO = llexternal(
     'RPyThreadFusedReleaseAcquireLock', [TLOCKP], lltype.Void,
                                         threadsafe=False)

def allocate_lock():
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw')
    res = c_thread_lock_init(ll_lock)
    if res == -1:
        lltype.free(ll_lock, flavor='raw')
        raise error("out of resources")
    return Lock(ll_lock)

def allocate_lock_NOAUTO():
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw')
    res = c_thread_lock_init(ll_lock)
    if res == -1:
        lltype.free(ll_lock, flavor='raw')
        raise error("out of resources")
    return Lock_NOAUTO(ll_lock)

def ll_start_new_thread(func):
    ident = c_thread_start(func)
    if ident == -1:
        raise error("can't start new thread")
    return ident

# wrappers...

def get_ident():
    return rffi.cast(lltype.Signed, c_thread_get_ident())

def start_new_thread(x, y):
    """In RPython, no argument can be passed.  You have to use global
    variables to pass information to the new thread.  That's not very
    nice, but at least it avoids some levels of GC issues.
    """
    assert len(y) == 0
    return rffi.cast(lltype.Signed, ll_start_new_thread(x))

class Lock(object):
    """ Container for low-level implementation
    of a lock object
    """
    def __init__(self, ll_lock):
        self._lock = ll_lock

    def acquire(self, flag):
        return bool(c_thread_acquirelock(self._lock, int(flag)))

    def release(self):
        # Sanity check: the lock must be locked
        if self.acquire(False):
            c_thread_releaselock(self._lock)
            raise error("bad lock")
        else:
            c_thread_releaselock(self._lock)

    def __del__(self):
        lltype.free(self._lock, flavor='raw')

class Lock_NOAUTO(object):
    """A special lock that doesn't cause the GIL to be released when
    we try to acquire it.  Used for the GIL itself."""

    def __init__(self, ll_lock):
        self._lock = ll_lock

    def acquire(self, flag):
        return bool(c_thread_acquirelock_NOAUTO(self._lock, int(flag)))

    def release(self):
        ll_assert(not self.acquire(False), "Lock_NOAUTO was not held!")
        c_thread_releaselock_NOAUTO(self._lock)

    def fused_release_acquire(self):
        ll_assert(not self.acquire(False), "Lock_NOAUTO was not held!")
        c_thread_fused_releaseacquirelock_NOAUTO(self._lock)

    def __del__(self):
        lltype.free(self._lock, flavor='raw')
