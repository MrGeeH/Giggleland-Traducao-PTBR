import struct
class R:
    def __init__(s,b,p=0): s.b=b; s.p=p
    def i32(s): v=struct.unpack_from('<i',s.b,s.p)[0]; s.p+=4; return v
    def i64(s): v=struct.unpack_from('<q',s.b,s.p)[0]; s.p+=8; return v
    def f32(s): v=struct.unpack_from('<f',s.b,s.p)[0]; s.p+=4; return v
    def u8a(s): v=s.b[s.p]; s.p+=1; s.align(); return v
    def align(s): s.p=(s.p+3)&~3
    def str(s): n=s.i32(); v=s.b[s.p:s.p+n].decode('utf-8'); s.p+=n; s.align(); return v
class W:
    def __init__(s): s.o=bytearray()
    def align(s): s.o+=b'\0'*((-len(s.o))%4)
    def i32(s,v): s.o+=struct.pack('<i',v)
    def i64(s,v): s.o+=struct.pack('<q',v)
    def f32(s,v): s.o+=struct.pack('<f',v)
    def u8a(s,v): s.o.append(v); s.align()
    def str(s,v): e=v.encode('utf-8'); s.i32(len(e)); s.o+=e; s.align()
def parse(raw):
    r=R(raw); r.p=12; r.u8a(); r.p+=12; r.str()   # GameObject, enabled, script, name
    start=r.p
    langs=[]
    for _ in range(r.i32()):
        L={'code':r.str(),'displayName':r.str(),'isRightToLeft':r.u8a(),'font':(r.i32(),r.i64()),'fontMode':r.i32()}
        L['systemLanguages']=[r.i32() for _ in range(r.i32())]; L['readingCharsPerSecond']=r.f32(); langs.append(L)
    ents=[]
    for _ in range(r.i32()):
        e={'key':r.str(),'category':r.str(),'context':r.str(),'isSubtitle':r.u8a(),'sentForTranslation':r.str()}
        e['values']=[{'lang':r.str(),'text':r.str()} for _ in range(r.i32())]; ents.append(e)
    return raw[:start],langs,ents,raw[r.p:]
def build(head,langs,ents,tail):
    w=W(); w.o+=head; w.i32(len(langs))
    for L in langs:
        w.str(L['code']); w.str(L['displayName']); w.u8a(L['isRightToLeft']); w.i32(L['font'][0]); w.i64(L['font'][1]); w.i32(L['fontMode'])
        w.i32(len(L['systemLanguages'])); [w.i32(x) for x in L['systemLanguages']]; w.f32(L['readingCharsPerSecond'])
    w.i32(len(ents))
    for e in ents:
        w.str(e['key']); w.str(e['category']); w.str(e['context']); w.u8a(e['isSubtitle']); w.str(e['sentForTranslation'])
        w.i32(len(e['values']))
        for v in e['values']: w.str(v['lang']); w.str(v['text'])
    w.o+=tail; return bytes(w.o)
