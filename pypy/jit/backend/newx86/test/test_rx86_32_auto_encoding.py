import os, random, struct
import py
from pypy.jit.backend.newx86 import rx86
from pypy.rlib.rarithmetic import intmask
from pypy.tool.udir import udir

INPUTNAME = 'checkfile_%s.s'
FILENAME = 'checkfile_%s.o'
BEGIN_TAG = '<<<rx86-test-begin>>>'
END_TAG =   '<<<rx86-test-end>>>'

class CodeCheckerMixin(object):
    def __init__(self, expected):
        self.expected = expected
        self.index = len(expected)
        self.insn = []

    def writechar(self, char):
        self.insn.append(char)

    def stop(self, op):
        got = ''.join(self.insn[::-1])
        end = self.index
        start = max(end - len(self.insn), 0)
        expected = self.expected[start:end]
        if got != expected:
            print op
            print "\x09from rx86.py: ", hexdump(got)
            print "\x09from 'as':    ", hexdump(expected)
            raise Exception("Differs")
        self.index = start
        self.insn = []

    def done(self):
        assert self.index == 0

def hexdump(s):
    return ' '.join(["%02X" % ord(c) for c in s])

# ____________________________________________________________

COUNT1 = 15
suffixes = {0:'', 1:'b', 2:'w', 4:'l', 8:'q'}


class TestRx86_32(object):
    WORD = 4
    TESTDIR = 'rx86_32'
    X86_CodeBuilder = rx86.X86_32_CodeBuilder
    REGNAMES = ['%eax', '%ecx', '%edx', '%ebx', '%esp', '%ebp', '%esi', '%edi']
    XMMREGNAMES = ['%%xmm%d' % i for i in range(16)]
    REGS = range(8)
    NONSPECREGS = [rx86.R.eax, rx86.R.ecx, rx86.R.edx, rx86.R.ebx,
                   rx86.R.esi, rx86.R.edi]
    methname = '?'

    def reg_tests(self):
        return self.REGS

    def stack_bp_tests(self, count=COUNT1):
        return ([0, 4, -4, 124, 128, -128, -132] +
                [random.randrange(-0x20000000, 0x20000000) * 4
                 for i in range(count)])

    def stack_sp_tests(self, count=COUNT1):
        return ([0, 4, 124, 128] +
                [random.randrange(0, 0x20000000) * 4
                 for i in range(count)])

    def memory_tests(self):
        return [(reg, ofs)
                    for reg in self.NONSPECREGS
                    for ofs in self.stack_bp_tests(5)
                ]

    def array_tests(self):
        return [(reg1, reg2, scaleshift, ofs)
                    for reg1 in self.NONSPECREGS
                    for reg2 in self.NONSPECREGS
                    for scaleshift in [0, 1, 2, 3]
                    for ofs in self.stack_bp_tests(1)
                ]

    def imm8_tests(self):
        v = ([-128,-1,0,1,127] +
             [random.randrange(-127, 127) for i in range(COUNT1)])
        return v

    def imm32_tests(self):
        v = ([-0x80000000, 0x7FFFFFFF, 128, 256, -129, -255] +
             [random.randrange(-32768,32768)<<16 |
                 random.randrange(0,65536) for i in range(COUNT1)] +
             [random.randrange(128, 256) for i in range(COUNT1)])
        return self.imm8_tests() + v

    def relative_tests(self):
        py.test.skip("explicit test required for %r" % (self.methname,))

    def get_all_tests(self):
        return {
            'r': self.reg_tests,
            'b': self.stack_bp_tests,
            's': self.stack_sp_tests,
            'm': self.memory_tests,
            'a': self.array_tests,
            'i': self.imm32_tests,
            'j': self.imm32_tests,
            'l': self.relative_tests,
            }

    def assembler_operand_reg(self, regnum):
        if self.is_xmm_insn:
            return self.XMMREGNAMES[regnum]
        else:
            return self.REGNAMES[regnum]

    def assembler_operand_stack_bp(self, position):
        return '%d(%s)' % (position, self.REGNAMES[5])

    def assembler_operand_stack_sp(self, position):
        return '%d(%s)' % (position, self.REGNAMES[4])

    def assembler_operand_memory(self, (reg1, offset)):
        if not offset: offset = ''
        return '%s(%s)' % (offset, self.REGNAMES[reg1])

    def assembler_operand_array(self, (reg1, reg2, scaleshift, offset)):
        if not offset: offset = ''
        return '%s(%s,%s,%d)' % (offset, self.REGNAMES[reg1],
                                 self.REGNAMES[reg2], 1<<scaleshift)

    def assembler_operand_imm(self, value):
        return '$%d' % value

    def assembler_operand_imm_addr(self, value):
        return '%d' % value

    def get_all_assembler_operands(self):
        return {
            'r': self.assembler_operand_reg,
            'b': self.assembler_operand_stack_bp,
            's': self.assembler_operand_stack_sp,
            'm': self.assembler_operand_memory,
            'a': self.assembler_operand_array,
            'i': self.assembler_operand_imm,
            'j': self.assembler_operand_imm_addr,
            }

    def run_test(self, methname, instrname, argmodes, args_lists):
        global labelcount
        labelcount = 0
        oplist = []
        testdir = udir.ensure(self.TESTDIR, dir=1)
        inputname = str(testdir.join(INPUTNAME % methname))
        filename  = str(testdir.join(FILENAME  % methname))
        g = open(inputname, 'w')
        g.write('\x09.string "%s"\n' % BEGIN_TAG)
        for args in args_lists:
            suffix = ""
    ##        all = instr.as_all_suffixes
    ##        for m, extra in args:
    ##            if m in (i386.MODRM, i386.MODRM8) or all:
    ##                suffix = suffixes[sizes[m]] + suffix
            if argmodes and not self.is_xmm_insn:
                suffix = suffixes[self.WORD]

            following = ""
            if False:   # instr.indirect:
                suffix = ""
                if args[-1][0] == i386.REL32: #in (i386.REL8,i386.REL32):
                    labelcount += 1
                    following = "\nL%d:" % labelcount
                elif args[-1][0] in (i386.IMM8,i386.IMM32):
                    args = list(args)
                    args[-1] = ("%d", args[-1][1])  # no '$' sign
                else:
                    suffix += " *"
                k = -1
            else:
                k = len(args)
            #for m, extra in args[:k]:
            #    assert m != i386.REL32  #not in (i386.REL8,i386.REL32)
            assembler_operand = self.get_all_assembler_operands()
            ops = []
            for mode, v in zip(argmodes, args):
                ops.append(assembler_operand[mode](v))
            ops.reverse()
            op = '\t%s%s %s%s' % (instrname.lower(), suffix,
                                  ', '.join(ops), following)
            g.write('%s\n' % op)
            oplist.append(op)
        g.write('\t.string "%s"\n' % END_TAG)
        g.close()
        os.system('as --%d "%s" -o "%s"' % (self.WORD*8, inputname, filename))
        try:
            f = open(filename, 'rb')
        except IOError:
            raise Exception("Assembler error")
        data = f.read()
        f.close()
        i = data.find(BEGIN_TAG)
        assert i>=0
        j = data.find(END_TAG, i)
        assert j>=0
        as_code = data[i+len(BEGIN_TAG)+1:j]
        return oplist, as_code

    def make_all_tests(self, methname, modes, args=[]):
        if modes:
            tests = self.get_all_tests()
            m = modes[0]
            lst = tests[m]()
            random.shuffle(lst)
            result = []
            for v in lst:
                result += self.make_all_tests(methname, modes[1:], args+[v])
            return result
        else:
            # special cases
            if methname in ('ADD_ri', 'AND_ri', 'CMP_ri', 'OR_ri',
                            'SUB_ri', 'XOR_ri'):
                if args[0] == rx86.R.eax:
                    return []     # ADD EAX, constant: there is a special encoding
            if methname == 'MOV_rj' and args[0] == rx86.R.eax:
                return []   # MOV EAX, [immediate]: there is a special encoding
            if methname == 'MOV_jr' and args[1] == rx86.R.eax:
                return []   # MOV [immediate], EAX: there is a special encoding
            if methname == 'SET_ir':
                py.test.skip("SET_ir: must be tested manually")
            return [args]

    def get_code_checker_class(self):
        class X86_CodeBuilder(CodeCheckerMixin, self.X86_CodeBuilder):
            pass
        return X86_CodeBuilder

    def complete_test(self, methname):
        if methname.split('_')[0][-1].isdigit():
            print "artificial instruction: %r" % (methname,)
            return
        if '_' in methname:
            instrname, argmodes = methname.split('_')
        else:
            instrname, argmodes = methname, ''
        print "Testing %s with argmodes=%r" % (instrname, argmodes)
        self.methname = methname
        self.is_xmm_insn = getattr(getattr(rx86.AbstractX86CodeBuilder,
                                           methname), 'is_xmm_insn', False)
        ilist = self.make_all_tests(methname, argmodes)
        oplist, as_code = self.run_test(methname, instrname, argmodes, ilist)
        cc = self.get_code_checker_class()(as_code)
        for i in range(len(oplist)-1, -1, -1):
            op = oplist[i]
            if op:
                getattr(cc, methname)(*ilist[i])
                cc.stop(op)
        cc.done()

    def setup_class(cls):
        import os
        g = os.popen('as -version </dev/null -o /dev/null 2>&1')
        data = g.read()
        g.close()
        if not data.startswith('GNU assembler'):
            py.test.skip("full tests require the GNU 'as' assembler")

    def test_all(self):
        for name in rx86.all_instructions:
            yield self.complete_test, name
