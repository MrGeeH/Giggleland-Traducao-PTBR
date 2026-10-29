# Instalador da tradução PT-BR do Giggleland (por MrGeH)
import sys, os, re, io, csv, json, shutil, struct, hashlib, traceback

def res(nome):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome)

sys.path.insert(0, res('.'))
from locdata import parse, build

CODE = 'pt-BR'
LANG = {'code': CODE, 'displayName': 'Português (Brasil)', 'isRightToLeft': 0, 'font': (0, 0),
        'fontMode': 0, 'systemLanguages': [28], 'readingCharsPerSecond': 0.0}
BAK = '.original.bak'

def titulo():
    print('=' * 60)
    print('  Tradução PT-BR do Giggleland  -  por MrGeH')
    print('=' * 60)

def pausar():
    try: input('\nAperte ENTER para fechar...')
    except EOFError: pass

# ---------- localizar o jogo ----------
def eh_pasta_do_jogo(p):
    return p and os.path.isfile(os.path.join(p, 'GameAssembly.dll')) and \
        os.path.isfile(os.path.join(p, 'Giggleland_Data', 'resources.assets'))

def achar_jogo():
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    p = exe_dir
    for _ in range(4):
        if eh_pasta_do_jogo(p): return p
        p = os.path.dirname(p)
    print('Não achei o jogo na pasta do instalador. Escolha a pasta do Giggleland...')
    try:
        import tkinter as tk
        from tkinter import filedialog
        r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)
        p = filedialog.askdirectory(title='Escolha a pasta do Giggleland (onde fica Giggleland.exe)')
        r.destroy()
    except Exception:
        p = input('Digite o caminho da pasta do jogo: ').strip().strip('"')
    if eh_pasta_do_jogo(p): return p
    return None

def backup(path):
    b = path + BAK
    if not os.path.exists(b):
        shutil.copy2(path, b)
        print('   backup criado:', os.path.basename(b))

# ---------- tabela de idiomas (resources.assets) ----------
def achar_tabela(f):
    for o in f.objects.values():
        if o.type.name != 'MonoBehaviour': continue
        if o.byte_size < 50000: continue
        raw = o.get_raw_data()
        if b'\x02\x00\x00\x00en\x00\x00' not in raw[:4096]: continue
        try:
            h, L, E, t = parse(raw)
            if build(h, L, E, t) == raw and len(E) > 100 and any(l['code'] == 'en' for l in L):
                return o, (h, L, E, t)
        except Exception:
            pass
    return None, None

def instalar_tabela(jogo):
    import UnityPy
    path = os.path.join(jogo, 'Giggleland_Data', 'resources.assets')
    print('\n[1/3] Textos do jogo (resources.assets)')
    print('   carregando... (pode demorar um pouco)')
    with open(path, 'rb') as fh:
        env = UnityPy.load(fh.read())
    f = list(env.files.values())[0]
    o, parsed = achar_tabela(f)
    if not o:
        print('   ERRO: não encontrei a tabela de idiomas nesta versão do jogo.')
        return False
    h, L, E, t = parsed
    tr = json.load(open(res('traducao.json'), encoding='utf-8'))
    L = [l for l in L if l['code'] != CODE] + [dict(LANG)]
    feitos = 0
    for e in E:
        e['values'] = [v for v in e['values'] if v['lang'] != CODE]
        en = next((v['text'] for v in e['values'] if v['lang'] == 'en'), None)
        if en is None: continue
        pt = tr.get(e['key'] + '\x1f' + en)
        if pt is not None: feitos += 1
        e['values'].append({'lang': CODE, 'text': pt if pt is not None else en})
    new = build(h, L, E, t)
    h2, L2, E2, t2 = parse(new)
    assert build(h2, L2, E2, t2) == new and len(E2) == len(E)
    o.set_raw_data(new)
    data = f.save()
    backup(path)
    tmp = path + '.tmp'
    open(tmp, 'wb').write(data)
    os.replace(tmp, path)
    print(f'   {feitos} de {len(E)} textos traduzidos.')
    if feitos < len(E) * 0.8:
        print('   (esta versão do jogo tem textos novos; os que faltam ficam em inglês)')
    return True

# ---------- patch de idioma (GameAssembly.dll) ----------
# Awake: code = "en";  -> pulado
PAT_A = re.compile(rb'\x48\x8B\x05(.{4})\x48\x8D\x4B\x28\x48\x89\x43\x28\x48\x8B\x15(.{4})\xE8.{4}\x48\x8B\x0D.{4}\x48\x8B\x7B\x20', re.S)
DONE_A = re.compile(rb'\xEB\x19\x05.{4}\x48\x8D\x4B\x28\x48\x89\x43\x28\x48\x8B\x15.{4}\xE8.{4}\x48\x8B\x0D.{4}\x48\x8B\x7B\x20', re.S)
# SetLanguage: code = "en";  -> removido
PAT_B = re.compile(rb'\x48\x8B\x0D.{4}\x48\x8B\x3D(.{4})\x48\x8B\x73\x20\x83\xB9\xE0\x00\x00\x00\x00', re.S)
DONE_B = re.compile(rb'\x48\x8B\x0D.{4}\x0F\x1F\x80\x00\x00\x00\x00\x48\x8B\x73\x20\x83\xB9\xE0\x00\x00\x00\x00', re.S)

def instalar_dll(jogo):
    path = os.path.join(jogo, 'GameAssembly.dll')
    print('\n[2/3] Liberar a troca de idioma (GameAssembly.dll)')
    b = bytearray(open(path, 'rb').read())
    a_done = len(DONE_A.findall(b)) == 1
    b_done = len(DONE_B.findall(b)) == 1
    if a_done and b_done:
        print('   já estava aplicado.'); return True
    ma = list(PAT_A.finditer(b)) if not a_done else []
    mb = list(PAT_B.finditer(b)) if not b_done else []
    if (not a_done and len(ma) != 1) or (not b_done and len(mb) != 1):
        print('   ERRO: esta versão do jogo é diferente; não alterei nada no GameAssembly.dll.')
        return False
    slot = None
    if ma:
        m = ma[0]; s = m.start()
        t1 = s + 7 + struct.unpack('<i', m.group(1))[0]
        t2 = s + 22 + struct.unpack('<i', m.group(2))[0]
        if t1 != t2:
            print('   ERRO: padrão inesperado; não alterei nada.'); return False
        slot = t1
    if mb and slot is not None:
        s = mb[0].start() + 7
        if s + 7 + struct.unpack('<i', mb[0].group(1))[0] != slot:
            print('   ERRO: padrão inesperado; não alterei nada.'); return False
    if ma:
        b[ma[0].start():ma[0].start() + 2] = b'\xEB\x19'
    if mb:
        s = mb[0].start() + 7
        b[s:s + 7] = b'\x0F\x1F\x80\x00\x00\x00\x00'
    backup(path)
    tmp = path + '.tmp'
    open(tmp, 'wb').write(b)
    os.replace(tmp, path)
    print('   ok.')
    return True

# ---------- en.csv (textos antigos de interface) ----------
def instalar_csv(jogo):
    path = os.path.join(jogo, 'Giggleland_Data', 'StreamingAssets', 'en.csv')
    print('\n[3/3] Textos extras (en.csv)')
    if not os.path.isfile(path):
        print('   não existe nesta versão, pulando.'); return True
    tr = json.load(open(res('csv_pt.json'), encoding='utf-8'))
    raw = open(path, 'rb').read()
    txt = raw.decode('utf-8')
    # percorre as células guardando a posição, para trocar só o texto e manter o resto do arquivo igual
    out, i, n, N = [], 0, 0, len(txt)
    while i <= N:
        if i < N and txt[i] == '"':
            j = i + 1; val = []
            while j < N:
                if txt[j] == '"':
                    if j + 1 < N and txt[j + 1] == '"': val.append('"'); j += 2; continue
                    break
                val.append(txt[j]); j += 1
            end = j + 1; val = ''.join(val)
        else:
            j = i
            while j < N and txt[j] not in ',\r\n': j += 1
            end = j; val = txt[i:j]
        cell = txt[i:end]
        key = val.lstrip('﻿')
        if key in tr:
            novo = tr[key]
            if any(c in novo for c in ',"\r\n'): novo = '"' + novo.replace('"', '""') + '"'
            cell = ('﻿' if val.startswith('﻿') else '') + novo; n += 1
        out.append(cell)
        if end >= N: break
        k = end
        while k < N and txt[k] != ',' and txt[k] not in '\r\n': k += 1
        if k < N and txt[k] == '\r' and k + 1 < N and txt[k + 1] == '\n': sep_end = k + 2
        else: sep_end = k + 1
        out.append(txt[end:sep_end]); i = sep_end
        if i >= N: break
    if n == 0:
        print('   nada para traduzir (já traduzido?).'); return True
    backup(path)
    open(path, 'wb').write(''.join(out).encode('utf-8'))
    print(f'   {n} textos traduzidos.')
    return True

# ---------- configuração ----------
def definir_idioma():
    p = os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'LocalLow', 'Hooked', 'Giggleland', 'Saves', 'settings.json')
    try:
        if os.path.isfile(p):
            d = json.load(open(p, encoding='utf-8'))
            d['language'] = CODE
            json.dump(d, open(p, 'w', encoding='utf-8'), separators=(',', ':'))
            print('\nIdioma do jogo definido como Português (Brasil).')
    except Exception:
        pass

def desinstalar(jogo):
    arqs = [os.path.join(jogo, 'GameAssembly.dll'),
            os.path.join(jogo, 'Giggleland_Data', 'resources.assets'),
            os.path.join(jogo, 'Giggleland_Data', 'StreamingAssets', 'en.csv')]
    achou = False
    for a in arqs:
        if os.path.isfile(a + BAK):
            os.replace(a + BAK, a); achou = True
            print('   restaurado:', os.path.relpath(a, jogo))
    print('Tradução removida.' if achou else 'Nenhum backup encontrado; nada para desfazer.')
    print('Obs.: se o jogo foi atualizado depois da instalação, prefira "Verificar arquivos" na Steam.')

def main():
    titulo()
    jogo = achar_jogo()
    if not jogo:
        print('Pasta do jogo inválida (precisa ter GameAssembly.dll e Giggleland_Data).'); return
    print('Jogo encontrado em:', jogo)
    print('\n  1 - Instalar / atualizar a tradução')
    print('  2 - Desinstalar (voltar ao original)')
    op = input('\nEscolha (1 ou 2): ').strip()
    if op == '2':
        desinstalar(jogo); return
    if op != '1':
        print('Opção inválida.'); return
    print('\nFeche o jogo antes de continuar.')
    ok1 = instalar_tabela(jogo)
    ok2 = instalar_dll(jogo) if ok1 else False
    instalar_csv(jogo)
    if ok1 and ok2:
        definir_idioma()
        print('\nPRONTO! Abra o jogo e divirta-se.')
    else:
        print('\nA instalação não foi completa. Veja as mensagens acima.')

if __name__ == '__main__':
    try:
        main()
    except PermissionError:
        print('\nERRO: sem permissão para alterar os arquivos. Feche o jogo e tente de novo'
              '\n(ou execute o instalador como administrador).')
    except Exception:
        traceback.print_exc()
        print('\nERRO inesperado. Nada que já tenha sido salvo em backup foi perdido.')
    pausar()
