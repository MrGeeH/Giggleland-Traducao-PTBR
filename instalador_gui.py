# Janela do instalador da tradução PT-BR do Giggleland (por MrGeH)
import os, re, sys, threading, traceback, queue
import tkinter as tk
from tkinter import filedialog, messagebox
import instalar_traducao as core

BG = '#1E1430'; PANEL = '#2B1D45'; FG = '#F3EAFB'; MUTED = '#A898B8'
ACCENT = '#FFCA66'; PINK = '#E8506E'; OK = '#5CE07A'

def pastas_candidatas():
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    p = exe_dir
    for _ in range(4):
        yield p; p = os.path.dirname(p)
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
        steam = winreg.QueryValueEx(k, 'SteamPath')[0]
        libs = [steam]
        vdf = os.path.join(steam, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            libs += [m.replace('\\\\', '\\') for m in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='ignore').read())]
        for lib in libs:
            yield os.path.join(lib, 'steamapps', 'common', 'Giggleland')
    except Exception:
        pass

def detectar_jogo():
    for p in pastas_candidatas():
        if core.eh_pasta_do_jogo(p): return os.path.normpath(p)
    return ''

class Saida:
    """Redireciona os print() do instalador para a janela."""
    def __init__(self, q): self.q = q
    def write(self, s):
        if s: self.q.put(('log', s))
    def flush(self): pass

class App:
    def __init__(self, root):
        self.root = root; self.q = queue.Queue(); self.ocupado = False
        root.title('Tradução PT-BR - Giggleland')
        root.configure(bg=BG); root.resizable(False, False)
        try: root.iconbitmap(core.res('icone.ico'))
        except Exception: pass

        tk.Label(root, text='GiggleLand', bg=BG, fg=ACCENT, font=('Segoe UI Black', 28)).pack(pady=(18, 0))
        tk.Label(root, text='Tradução para Português do Brasil', bg=BG, fg=FG, font=('Segoe UI', 13)).pack()
        tk.Label(root, text='Tradução por MrGeH', bg=BG, fg=PINK, font=('Segoe UI Semibold', 11)).pack(pady=(2, 14))

        box = tk.Frame(root, bg=PANEL, padx=16, pady=14); box.pack(fill='x', padx=20)
        tk.Label(box, text='Pasta do jogo', bg=PANEL, fg=MUTED, font=('Segoe UI', 9)).grid(row=0, column=0, sticky='w')
        self.pasta = tk.StringVar(value=detectar_jogo())
        e = tk.Entry(box, textvariable=self.pasta, width=52, bg='#140D22', fg=FG, insertbackground=FG,
                     relief='flat', font=('Segoe UI', 10))
        e.grid(row=1, column=0, ipady=5, sticky='we')
        self.b_proc = self.botao(box, 'Procurar...', self.procurar, '#4A3570', FG, w=10)
        self.b_proc.grid(row=1, column=1, padx=(8, 0))
        self.status_pasta = tk.Label(box, bg=PANEL, font=('Segoe UI', 9), anchor='w')
        self.status_pasta.grid(row=2, column=0, columnspan=2, sticky='w', pady=(6, 0))
        self.pasta.trace_add('write', lambda *a: self.checar_pasta()); self.checar_pasta()

        bt = tk.Frame(root, bg=BG); bt.pack(pady=14)
        self.b_inst = self.botao(bt, 'INSTALAR TRADUÇÃO', self.instalar, ACCENT, '#2B1D45', w=22)
        self.b_inst.pack(side='left', padx=6)
        self.b_des = self.botao(bt, 'Desinstalar', self.desinstalar, '#4A3570', FG, w=12)
        self.b_des.pack(side='left', padx=6)

        self.log = tk.Text(root, height=12, width=70, bg='#140D22', fg=FG, relief='flat', font=('Consolas', 9),
                           padx=10, pady=8, state='disabled', wrap='word')
        self.log.pack(padx=20, pady=(0, 6))
        self.log.tag_configure('ok', foreground=OK); self.log.tag_configure('erro', foreground=PINK)
        self.rodape = tk.Label(root, text='Feche o jogo antes de instalar. Os arquivos originais ganham backup (.original.bak).',
                               bg=BG, fg=MUTED, font=('Segoe UI', 8))
        self.rodape.pack(pady=(0, 14))
        self.escrever('Pronto para instalar.\n')
        root.after(100, self.bombear)

    def botao(self, pai, txt, cmd, bg, fg, w):
        return tk.Button(pai, text=txt, command=cmd, bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                         relief='flat', bd=0, width=w, pady=8, cursor='hand2', font=('Segoe UI Semibold', 10))

    def checar_pasta(self):
        if core.eh_pasta_do_jogo(self.pasta.get()):
            self.status_pasta.config(text='✔ Jogo encontrado', fg=OK)
        else:
            self.status_pasta.config(text='✖ Escolha a pasta onde fica o Giggleland.exe', fg=PINK)

    def procurar(self):
        p = filedialog.askdirectory(title='Escolha a pasta do Giggleland (onde fica Giggleland.exe)')
        if p: self.pasta.set(os.path.normpath(p))

    def escrever(self, s, tag=None):
        self.log.config(state='normal'); self.log.insert('end', s, tag); self.log.see('end'); self.log.config(state='disabled')

    def bombear(self):
        try:
            while True:
                tipo, s = self.q.get_nowait()
                if tipo == 'log':
                    tag = 'erro' if 'ERRO' in s else ('ok' if 'PRONTO' in s or 'removida' in s else None)
                    self.escrever(s, tag)
                elif tipo == 'fim':
                    self.travar(False)
                    ok, msg = s
                    (messagebox.showinfo if ok else messagebox.showwarning)('Tradução PT-BR', msg)
        except queue.Empty:
            pass
        self.root.after(100, self.bombear)

    def travar(self, sim):
        self.ocupado = sim
        for b in (self.b_inst, self.b_des, self.b_proc):
            b.config(state='disabled' if sim else 'normal')
        self.root.config(cursor='watch' if sim else '')

    def rodar(self, func):
        jogo = self.pasta.get()
        if not core.eh_pasta_do_jogo(jogo):
            messagebox.showerror('Tradução PT-BR', 'Pasta do jogo inválida.\nEscolha a pasta onde fica o Giggleland.exe.')
            return
        self.travar(True)
        self.log.config(state='normal'); self.log.delete('1.0', 'end'); self.log.config(state='disabled')
        def trabalho():
            antigo = sys.stdout; sys.stdout = Saida(self.q)
            try:
                res = func(jogo)
            except PermissionError:
                print('\nERRO: sem permissão para alterar os arquivos. Feche o jogo e tente de novo.')
                res = (False, 'Não foi possível alterar os arquivos.\nFeche o jogo e tente de novo.')
            except Exception:
                print('\nERRO inesperado:\n' + traceback.format_exc())
                res = (False, 'Ocorreu um erro inesperado. Veja os detalhes na janela.')
            finally:
                sys.stdout = antigo
            self.q.put(('fim', res))
        threading.Thread(target=trabalho, daemon=True).start()

    def instalar(self):
        def f(jogo):
            print('Instalando em: ' + jogo + '\n')
            ok1 = core.instalar_tabela(jogo)
            ok2 = core.instalar_dll(jogo) if ok1 else False
            core.instalar_csv(jogo)
            if ok1 and ok2:
                core.definir_idioma()
                print('\nPRONTO! Abra o jogo e divirta-se.\n')
                return True, 'Tradução instalada com sucesso!\nAbra o jogo e divirta-se.'
            print('\nERRO: a instalação não foi completa. Veja as mensagens acima.\n')
            return False, 'A instalação não foi completa.\nVeja as mensagens na janela.'
        self.rodar(f)

    def desinstalar(self):
        if not messagebox.askyesno('Tradução PT-BR', 'Remover a tradução e voltar os arquivos originais?'):
            return
        def f(jogo):
            core.desinstalar(jogo)
            return True, 'Pronto. O jogo voltou aos arquivos originais.'
        self.rodar(f)

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
