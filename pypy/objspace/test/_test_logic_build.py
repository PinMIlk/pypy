import inspect

def raises(exception, call, *args):
    try:
        call(*args)
    except exception:
        return True
    except:
        pass
    return False

class Skip(Exception): pass

def skip(desc):
    print "skipping because", desc
    raise Skip

def get_test_classes():
    return [obj for name, obj in inspect.getmembers(tm)
            if isinstance(obj, type)]

def get_test_methods(klass):
    return [(name, meth)
            for name, meth in inspect.getmembers(klass())
            if not name.startswith('_')]

def run_tests(tm):
    
    tm.raises = raises
    tm.skip = skip
    
    successes = []
    failures = []
    skipped = []

    for tests in [get_test_methods(cl) for cl in get_test_classes()] :
        for name, meth in tests:
            if name == 'setup_class': continue
            try:
                meth()
            except Skip:
                skipped.append(name)
            except Exception, e:
                failures.append((name, meth, e))
            else:
                successes.append(name)

    if successes:
        print "Successes :"
        print '', '\n '.join(successes)
        print
    if failures:
        print "Failures :"
        for name, _, exc in failures:
            print '', name, "failed because", str(exc)
        print
    if skipped:
        print "Skipped"
        print '', '\n '.join(skipped)

    # replay failures with more info
    switch_debug_info()
    for name, meth, _ in failures:
        meth()
        
if __name__ == __name__:
    import sys
    tm = __import__(sys.argv[1])
    run_tests(tm)
