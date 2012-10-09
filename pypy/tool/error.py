
""" error handling features, just a way of displaying errors
"""

from pypy.tool.ansi_print import ansi_log
from pypy.objspace.flow.model import Variable
import sys

import py
log = py.log.Producer("error")
py.log.setconsumer("error", ansi_log)

SHOW_TRACEBACK = False
SHOW_ANNOTATIONS = True
SHOW_DEFAULT_LINES_OF_CODE = 0

from pypy.interpreter.pytraceback import offset2lineno

def source_lines1(graph, block, operindex=None, offset=None, long=False, \
    show_lines_of_code=SHOW_DEFAULT_LINES_OF_CODE):
    if block is not None:
        if block is graph.returnblock:
            return ['<return block>']
    try:
        source = graph.source
    except AttributeError:
        return ['no source!']
    else:
        graph_lines = source.split("\n")
        if offset is not None:
            linestart = offset2lineno(graph.func.func_code, offset)
            linerange = (linestart, linestart)
            here = None
        else:
            if block is None or not block.operations:
                return []
            def toline(operindex):
                return offset2lineno(graph.func.func_code, block.operations[operindex].offset)
            if operindex is None:
                linerange =  (toline(0), toline(-1))
                if not long:
                    return ['?']
                here = None
            else:
                operline = toline(operindex)
                if long:
                    linerange =  (toline(0), toline(-1))
                    here = operline
                else:
                    linerange = (operline, operline)
                    here = None
        lines = ["Happened at file %s line %d" % (graph.filename, here or linerange[0]), ""]
        for n in range(max(0, linerange[0]-show_lines_of_code), \
            min(linerange[1]+1+show_lines_of_code, len(graph_lines)+graph.startline)):
            if n == here:
                prefix = '==> '
            else:
                prefix = '    '
            lines.append(prefix + graph_lines[n-graph.startline])
        lines.append("")
        return lines

def source_lines(graph, *args, **kwds):
    lines = source_lines1(graph, *args, **kwds)
    return ['In %r:' % (graph,)] + lines

class AnnotatorError(Exception):
    pass

class NoSuchAttrError(Exception):
    pass

def gather_error(annotator, graph, block, operindex):
    msg = [""]

    if operindex is not None:
        oper = block.operations[operindex]
        if oper.opname == 'simple_call':
            format_simple_call(annotator, oper, msg)
    else:
        oper = None
    msg.append(" " + str(oper))
    msg += source_lines(graph, block, operindex, long=True)
    if oper is not None:
        if SHOW_ANNOTATIONS:
            msg.append("Known variable annotations:")
            for arg in oper.args + [oper.result]:
                if isinstance(arg, Variable):
                    try:
                        msg.append(" " + str(arg) + " = " + str(annotator.binding(arg)))
                    except KeyError:
                        pass
    return "\n".join(msg)

def format_blocked_annotation_error(annotator, blocked_blocks):
    text = []
    for block, (graph, index) in blocked_blocks.items():
        text.append('-+' * 30)
        text.append("Blocked block -- operation cannot succeed")
        text.append(gather_error(annotator, graph, block, index))
    return '\n'.join(text)

def format_simple_call(annotator, oper, msg):
    msg.append("Simple call of incompatible family:")
    try:
        descs = annotator.bindings[oper.args[0]].descriptions
    except (KeyError, AttributeError), e:
        msg.append("      (%s getting at the binding!)" % (
            e.__class__.__name__,))
        return
    for desc in list(descs):
        func = desc.pyobj
        if func is None:
            r = repr(desc)
        else:
            try:
                if isinstance(func, type):
                    func_name = "%s.__init__" % func.__name__
                    func = func.__init__.im_func
                else:
                    func_name = func.func_name
                r = "function %s <%s, line %s>" % (func_name,
                       func.func_code.co_filename, func.func_code.co_firstlineno)
            except (AttributeError, TypeError):
                r = repr(desc)
        msg.append("  %s returning" % (r,))
        if hasattr(desc, 'getuniquegraph'):
            graph = desc.getuniquegraph()
            r = annotator.binding(graph.returnblock.inputargs[0],
                                  "(no annotation)")
        else:
            r = '?'
        msg.append("      %s" % (r,))
        msg.append("")

def debug(drv, use_pdb=True):
    # XXX unify some code with pypy.translator.goal.translate
    from pypy.translator.tool.pdbplus import PdbPlusShow
    from pypy.translator.driver import log
    t = drv.translator
    class options:
        huge = 100

    tb = None
    import traceback
    errmsg = ["Error:\n"]
    exc, val, tb = sys.exc_info()

    errmsg.extend([" %s" % line for line in traceback.format_exception(exc, val, [])])
    block = getattr(val, '__annotator_block', None)
    if block:
        class FileLike:
            def write(self, s):
                errmsg.append(" %s" % s)
        errmsg.append("Processing block:\n")
        t.about(block, FileLike())
    log.ERROR(''.join(errmsg))

    log.event("start debugger...")

    if use_pdb:
        pdb_plus_show = PdbPlusShow(t)
        pdb_plus_show.start(tb)
