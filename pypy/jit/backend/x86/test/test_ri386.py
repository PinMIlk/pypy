import py
from pypy.jit.backend.x86.ri386 import *

class CodeBuilder(I386CodeBuilder):
    def __init__(self):
        self.buffer = []

    def writechar(self, c):
        self.buffer.append(c)    # append a character

    def getvalue(self):
        return ''.join(self.buffer)


def test_mov_ri():
    s = CodeBuilder()
    s.MOV_ri(ecx, -2)
    assert s.getvalue() == '\xB9\xFE\xFF\xFF\xFF'

def test_mov_si():
    s = CodeBuilder()
    s.MOV_si(-36, 1<<24)
    assert s.getvalue() == '\xC7\x45\xDC\x00\x00\x00\x01'

def test_mov_rr():
    s = CodeBuilder()
    s.MOV_rr(ebx, ebp)
    assert s.getvalue() == '\x89\xEB'

def test_mov_sr():
    s = CodeBuilder()
    s.MOV_sr(-36, edx)
    assert s.getvalue() == '\x89\x55\xDC'

def test_mov_rs():
    s = CodeBuilder()
    s.MOV_rs(edx, -36)
    assert s.getvalue() == '\x8B\x55\xDC'

def test_mov_rm():
    s = CodeBuilder()
    s.MOV_rm(edx, reg_offset(edi, 0))
    s.MOV_rm(edx, reg_offset(edi, -128))
    s.MOV_rm(edx, reg_offset(edi, 128))
    assert s.getvalue() == '\x8B\x17\x8B\x57\x80\x8B\x97\x80\x00\x00\x00'

def test_mov_mr():
    s = CodeBuilder()
    s.MOV_mr(reg_offset(edi, 0), edx)
    s.MOV_mr(reg_offset(edi, -128), edx)
    s.MOV_mr(reg_offset(edi, 128), edx)
    assert s.getvalue() == '\x89\x17\x89\x57\x80\x89\x97\x80\x00\x00\x00'

def test_mov_ra():
    s = CodeBuilder()
    s.MOV_ra(edx, reg_reg_scaleshift_offset(esi, edi, 2, 0))
    s.MOV_ra(edx, reg_reg_scaleshift_offset(esi, edi, 2, -128))
    s.MOV_ra(edx, reg_reg_scaleshift_offset(esi, edi, 2, 128))
    assert s.getvalue() == ('\x8B\x14\xBE' +
                            '\x8B\x54\xBE\x80' +
                            '\x8B\x94\xBE\x80\x00\x00\x00')

def test_mov_ar():
    s = CodeBuilder()
    s.MOV_ar(reg_reg_scaleshift_offset(esi, edi, 2, 0), edx)
    s.MOV_ar(reg_reg_scaleshift_offset(esi, edi, 2, -128), edx)
    s.MOV_ar(reg_reg_scaleshift_offset(esi, edi, 2, 128), edx)
    assert s.getvalue() == ('\x89\x14\xBE' +
                            '\x89\x54\xBE\x80' +
                            '\x89\x94\xBE\x80\x00\x00\x00')

def test_nop_add_rr():
    s = CodeBuilder()
    s.NOP()
    s.ADD_rr(eax, eax)
    assert s.getvalue() == '\x90\x01\xC0'

def test_lea_rs():
    s = CodeBuilder()
    s.LEA_rs(ecx, -36)
    assert s.getvalue() == '\x8D\x4D\xDC'

def test_lea32_rs():
    s = CodeBuilder()
    s.LEA32_rs(ecx, -36)
    assert s.getvalue() == '\x8D\x8D\xDC\xFF\xFF\xFF'
