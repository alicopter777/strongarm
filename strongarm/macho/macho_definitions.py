import struct

from enum import IntEnum
from ctypes import (
    Union,
    Structure,
    c_char,
    c_char_p,
    c_int16,
    c_uint8,
    c_uint16,
    c_uint32,
    c_uint64,
)


class StaticFilePointer(int):
    """A pointer analogous to a file offset within the Mach-O
    """


class VirtualMemoryPointer(int):
    """A pointer representing a virtual memory location within the Mach-O
    """


NULL_PTR = StaticFilePointer(0)
FILE_HEAD_PTR = StaticFilePointer(0)


def swap32(i: int) -> int:
    """Reverse the bytes of a little-endian integer representation ie (3) -> 50331648"""
    return struct.unpack("<I", struct.pack(">I", i))[0]


class MachArch(IntEnum):
    MH_MAGIC = 0xfeedface
    MH_CIGAM = 0xcefaedfe
    MH_MAGIC_64 = 0xfeedfacf
    MH_CIGAM_64 = 0xcffaedfe

    FAT_MAGIC = 0xcafebabe
    FAT_CIGAM = 0xbebafeca

    MH_CPU_ARCH_ABI64 = 0x01000000
    MH_CPU_TYPE_ARM = 12
    MH_CPU_TYPE_ARM64 = MH_CPU_TYPE_ARM | MH_CPU_ARCH_ABI64


class CPU_TYPE(IntEnum):
    ARMV7 = 0
    ARM64 = 1
    UNKNOWN = 2


class MachoFileType(IntEnum):
    MH_OBJECT = 1           # relocatable object file
    MH_EXECUTE = 2          # demand paged executable file
    MH_FVMLIB = 3           # fixed VM shared library file
    MH_CORE = 4             # core file
    MH_PRELOAD = 5          # preloaded executable file
    MH_DYLIB = 6            # dynamically bound shared library
    MH_DYLINKER = 7         # dynamic link editor
    MH_BUNDLE = 8           # dynamically bound bundle file
    MH_DYLIB_STUB = 9       # shared library stub for static linking only, no section contents
    MH_DSYM = 10            # shared library stub for static
    MH_KEXT_BUNDLE = 11     # x86_64 kext


class MachoHeader32(Structure):
    _fields_ = [
        ('magic', c_uint32),
        ('cputype', c_uint32),
        ('cpusubtype', c_uint32),
        ('filetype', c_uint32),
        ('ncmds', c_uint32),
        ('sizeofcmds', c_uint32),
        ('flags', c_uint32),
    ]


class MachoHeader64(Structure):
    _fields_ = [
        ('magic', c_uint32),
        ('cputype', c_uint32),
        ('cpusubtype', c_uint32),
        ('filetype', c_uint32),
        ('ncmds', c_uint32),
        ('sizeofcmds', c_uint32),
        ('flags', c_uint32),
        ('reserved', c_uint32),
    ]


class MachoSegmentCommand32(Structure):
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('segname', c_char * 16),
        ('vmaddr', c_uint32),
        ('vmsize', c_uint32),
        ('fileoff', c_uint32),
        ('filesize', c_uint32),
        ('maxprot', c_uint32),
        ('initprot', c_uint32),
        ('nsects', c_uint32),
        ('flags', c_uint32),
    ]


class MachoSegmentCommand64(Structure):
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('segname', c_char * 16),
        ('vmaddr', c_uint64),
        ('vmsize', c_uint64),
        ('fileoff', c_uint64),
        ('filesize', c_uint64),
        ('maxprot', c_uint32),
        ('initprot', c_uint32),
        ('nsects', c_uint32),
        ('flags', c_uint32),
    ]


class MachoLoadCommand(Structure):
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
    ]


class MachoSection32Raw(Structure):
    _fields_ = [
        ('sectname', c_char * 16),
        ('segname', c_char * 16),
        ('addr', c_uint32),
        ('size', c_uint32),
        ('offset', c_uint32),
        ('align', c_uint32),
        ('reloff', c_uint32),
        ('nreloc', c_uint32),
        ('flags', c_uint32),
        ('reserved1', c_uint32),
        ('reserved2', c_uint32),
    ]


class MachoSection64Raw(Structure):
    _fields_ = [
        ('sectname', c_char * 16),
        ('segname', c_char * 16),
        ('addr', c_uint64),
        ('size', c_uint64),
        ('offset', c_uint32),
        ('align', c_uint32),
        ('reloff', c_uint32),
        ('nreloc', c_uint32),
        ('flags', c_uint32),
        ('reserved1', c_uint32),
        ('reserved2', c_uint32),
        ('reserved3', c_uint32),
    ]


class MachoDysymtabCommand(Structure):
    """Python representation of struct dysymtab_command

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('ilocalsym', c_uint32),
        ('nlocalsym', c_uint32),
        ('iextdefsym', c_uint32),
        ('nextdefsym', c_uint32),
        ('iundefsym', c_uint32),
        ('nundefsym', c_uint32),
        ('tocoff', c_uint32),
        ('ntoc', c_uint32),
        ('modtaboff', c_uint32),
        ('nmodtab', c_uint32),
        ('extrefsymoff', c_uint32),
        ('nextrefsyms', c_uint32),
        ('indirectsymoff', c_uint32),
        ('nindirectsyms', c_uint32),
        ('extreloff', c_uint32),
        ('nextrel', c_uint32),
        ('locreloff', c_uint32),
        ('nlocrel', c_uint32)
    ]


class MachoSymtabCommand(Structure):
    """Python representation of struct symtab_command

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('symoff', c_uint32),
        ('nsyms', c_uint32),
        ('stroff', c_uint32),
        ('strsize', c_uint32)
    ]


class MachoDyldInfoCommand(Structure):
    """Python representation of struct dyld_info_command

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('rebase_off', c_uint32),
        ('rebase_size', c_uint32),
        ('bind_off', c_uint32),
        ('bind_size', c_uint32),
        ('weak_bind_off', c_uint32),
        ('weak_bind_size', c_uint32),
        ('lazy_bind_off', c_uint32),
        ('lazy_bind_size', c_uint32),
        ('export_off', c_uint32),
        ('export_size', c_uint32),
        ('weak_bind_size', c_uint32),
        ('weak_bind_size', c_uint32),
    ]


class MachoLinkeditDataCommand(Structure):
    """Python representation of struct linkedit_data_command

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('dataoff', c_uint32),
        ('datasize', c_uint32),
    ]


class MachoNlistUn(Union):
    """Python representation of union n_un

    Definition found in <mach-o/nlist.h>
    """
    __slots__ = ['n_strx']
    _fields_ = [
        ('n_strx', c_uint32),
    ]


class MachoNlist32(Structure):
    """Python representation of struct nlist

    Definition found in <mach-o/nlist.h>
    """
    __slots__ = ['n_un', 'n_type', 'n_sect', 'n_desc', 'n_value']
    _fields_ = [
        ('n_un', MachoNlistUn),
        ('n_type', c_uint8),
        ('n_sect', c_uint8),
        ('n_desc', c_int16),
        ('n_value', c_uint32),
    ]


class MachoNlist64(Structure):
    """Python representation of struct nlist_64

    Definition found in <mach-o/nlist.h>
    """
    __slots__ = ['n_un', 'n_type', 'n_sect', 'n_desc', 'n_value']
    _fields_ = [
        ('n_un', MachoNlistUn),
        ('n_type', c_uint8),
        ('n_sect', c_uint8),
        ('n_desc', c_uint16),
        ('n_value', c_uint64),
    ]


class MachoEncryptionInfo32Command(Structure):
    """Python representation of a struct encryption_info_command

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('cryptoff', c_uint32),
        ('cryptsize', c_uint32),
        ('cryptid', c_uint32),
    ]


class MachoEncryptionInfo64Command(Structure):
    """Python representation of a struct encryption_info_command_64

    Definition found in <mach-o/loader.h>
    """
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('cryptoff', c_uint32),
        ('cryptsize', c_uint32),
        ('cryptid', c_uint32),
        ('pad', c_uint32),
    ]


class MachoFatHeader(Structure):
    """Python representation of a struct fat_header

    Definition found in <mach-o/fat.h>
    """
    _fields_ = [
        ('magic', c_uint32),
        ('nfat_arch', c_uint32),
    ]


class MachoFatArch(Structure):
    """Python representation of a struct fat_arch

    Definition found in <mach-o/fat.h>
    """
    _fields_ = [
        ('cputype', c_uint32),
        ('cpusubtype', c_uint32),
        ('offset', c_uint32),
        ('size', c_uint32),
        ('align', c_uint32),
    ]


class NLIST_NTYPE(IntEnum):
    N_STAB = 0xe0 # symbollic debugging entry
    N_PEXT = 0x10 # private external symbol bit
    N_TYPE = 0x0e # mask for type bits
    N_EXT = 0x01 # external symbol bit


class NTYPE_VALUES(IntEnum):
    N_UNDF = 0x0 # undefined, n_sect == NO_SECT
    N_ABS = 0x2 # absolute, n_sect == NO_SECT
    N_SECT = 0xe # defined in section n_sect
    N_PBUD = 0xc # prebound undefined (defined in a dylib)
    N_INDR = 0xa # indirect


class HEADER_FLAGS(IntEnum):
    NOUNDEFS = 0x1
    INCRLINK = 0x2
    DYLDLINK = 0x4
    BINDATLOAD = 0x8
    PREBOUND = 0x10
    SPLIT_SEGS = 0x20
    LAZY_INIT = 0x40
    TWOLEVEL = 0x80
    FORCE_FLAT = 0x100
    NOMULTIDEFS = 0x200
    NOFIXPREBINDING = 0x400
    PREBINDABLE = 0x800
    ALLMODSBOUND = 0x1000
    SUBSECTIONS_VIA_SYMBOLS = 0x2000
    CANONICAL = 0x4000
    WEAK_DEFINES = 0x8000
    BINDS_TO_WEAK = 0x10000
    ALLOW_STACK_EXECUTION = 0x20000
    ROOT_SAFE = 0x40000
    SETUID_SAFE = 0x80000
    NO_REEXPORTED_DYLIBS = 0x100000
    PIE = 0x200000
    DEAD_STRIPPABLE_DYLIB = 0x400000
    HAS_TLV_DESCRIPTORS = 0x800000
    NO_HEAP_EXECUTION = 0x1000000
    APP_EXTENSION_SAFE = 0x2000000

# Some of these can be found at
# https://opensource.apple.com/source/objc4/objc4-723/runtime/objc-runtime-new.h.auto.html


class ObjcProtocolRaw32(Structure):
    _fields_ = [
        ('isa', c_uint32),
        ('name', c_uint32),
        ('protocols', c_uint32),
        ('required_instance_methods', c_uint32),
        ('required_class_methods', c_uint32),
        ('optional_instance_methods', c_uint32),
        ('optional_class_methods', c_uint32),
        ('instance_properties', c_uint32),
        ('instance_properties', c_uint32),
        ('size', c_uint32),
        ('flags', c_uint32),
    ]


class ObjcProtocolRaw64(Structure):
    _fields_ = [
        ('isa', c_uint64),
        ('name', c_uint64),
        ('protocols', c_uint64),
        ('required_instance_methods', c_uint64),
        ('required_class_methods', c_uint64),
        ('optional_instance_methods', c_uint64),
        ('optional_class_methods', c_uint64),
        ('instance_properties', c_uint64),
        ('instance_properties', c_uint64),
        ('size', c_uint32),
        ('flags', c_uint32),
    ]


class ObjcCategoryRaw32(Structure):
    _fields_ = [
        ('name', c_uint32),
        ('base_class', c_uint32),
        ('instance_methods', c_uint32),
        ('class_methods', c_uint32),
        ('base_protocols', c_uint32),
        ('instance_properties', c_uint32)
    ]


class ObjcCategoryRaw64(Structure):
    _fields_ = [
        ('name', c_uint64),
        ('base_class', c_uint64),
        ('instance_methods', c_uint64),
        ('class_methods', c_uint64),
        ('base_protocols', c_uint64),
        ('instance_properties', c_uint64)
    ]


class ObjcClassRaw32(Structure):
    _fields_ = [
        ('metaclass', c_uint32),
        ('superclass', c_uint32),
        ('cache', c_uint32),
        ('vtable', c_uint32),
        ('data', c_uint32)
    ]


class ObjcClassRaw64(Structure):
    _fields_ = [
        ('metaclass', c_uint64),
        ('superclass', c_uint64),
        ('cache', c_uint64),
        ('vtable', c_uint64),
        ('data', c_uint64)
    ]


class ObjcDataRaw32(Structure):
    _fields_ = [
        ('flags', c_uint32),
        ('instance_start', c_uint32),
        ('instance_size', c_uint32),
        ('ivar_layout', c_uint32),
        ('name', c_uint32),
        ('base_methods', c_uint32),
        ('base_protocols', c_uint32),
        ('ivars', c_uint32),
        ('weak_ivar_layout', c_uint32),
        ('base_properties', c_uint32),
    ]


class ObjcDataRaw64(Structure):
    _fields_ = [
        ('flags', c_uint32),
        ('instance_start', c_uint32),
        ('instance_size', c_uint32),
        ('reserved', c_uint32),
        ('ivar_layout', c_uint64),
        ('name', c_uint64),
        ('base_methods', c_uint64),
        ('base_protocols', c_uint64),
        ('ivars', c_uint64),
        ('weak_ivar_layout', c_uint64),
        ('base_properties', c_uint64),
    ]


class ObjcMethodList(Structure):
    _fields_ = [
        ('flags', c_uint32),
        ('methcount', c_uint32),
    ]


class ObjcProtocolList32(Structure):
    _fields_ = [
        ('count', c_uint32)
    ]


class ObjcProtocolList64(Structure):
    _fields_ = [
        ('count', c_uint64)
    ]


class ObjcMethod32(Structure):
    _fields_ = [
        ('name', c_uint32),
        ('signature', c_uint32),
        ('implementation', c_uint32)
    ]


class ObjcMethod64(Structure):
    _fields_ = [
        ('name', c_uint64),
        ('signature', c_uint64),
        ('implementation', c_uint64)
    ]


class LcStrUnion(Union):
    _fields_ = [
        ('offset', c_uint32),
        ('ptr', c_char_p)
    ]


class DylibStruct(Structure):
    _fields_ = [
        ('name', LcStrUnion),
        ('timestamp', c_uint32),
        ('current_version', c_uint32),
        ('compatibility_version', c_uint32),
    ]


class DylibCommand(Structure):
    _fields_ = [
        ('cmd', c_uint32),
        ('cmdsize', c_uint32),
        ('dylib', DylibStruct),
    ]


class CFString32(Structure):
    _fields_ = [
        ('base', c_uint32),
        ('flags', c_uint32),
        ('literal', c_uint32),
        ('length', c_uint32)
    ]


class CFString64(Structure):
    _fields_ = [
        ('base', c_uint64),
        ('flags', c_uint64),
        ('literal', c_uint64),
        ('length', c_uint64)
    ]
