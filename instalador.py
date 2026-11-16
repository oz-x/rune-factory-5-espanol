"""Instalador con ventana (se empaqueta como RF5-Espanol-Instalador.exe).

Sin ventana:  RF5-Espanol-Instalador.exe --instalar|--desinstalar ["ruta al juego"]
(código de salida 0 si todo fue bien).
"""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from instalar import InstallError, find_game, install, is_game, uninstall

AVISO = ('Traducción no oficial hecha con inteligencia artificial, por y para fans de la saga.\n'
         'Puede contener errores. Cierra el juego antes de instalar.\n'
         'En el lanzador del juego, el idioma del sistema debe ser "English".')


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Rune Factory 5 — Traducción al español')
        self.resizable(False, False)
        frm = ttk.Frame(self, padding=16)
        frm.grid()
        ttk.Label(frm, text='Rune Factory 5 en español', font=('Segoe UI', 14, 'bold')).grid(
            column=0, row=0, columnspan=3, sticky='w')
        ttk.Label(frm, text=AVISO, wraplength=520, justify='left').grid(
            column=0, row=1, columnspan=3, sticky='w', pady=(6, 12))
        ttk.Label(frm, text='Carpeta del juego:').grid(column=0, row=2, sticky='w')
        self.path = tk.StringVar(value=find_game() or '')
        ttk.Entry(frm, textvariable=self.path, width=60).grid(column=0, row=3, columnspan=2, sticky='we')
        ttk.Button(frm, text='Buscar…', command=self.browse).grid(column=2, row=3, padx=(6, 0))
        self.install_btn = ttk.Button(frm, text='Instalar traducción', command=lambda: self.run(install))
        self.install_btn.grid(column=0, row=4, sticky='w', pady=(14, 0))
        self.uninstall_btn = ttk.Button(frm, text='Desinstalar (volver al inglés)',
                                        command=lambda: self.run(uninstall))
        self.uninstall_btn.grid(column=1, row=4, sticky='w', pady=(14, 0))
        self.status = ttk.Label(frm, text='' if self.path.get() else
                                'No he encontrado el juego en Steam: elige su carpeta.')
        self.status.grid(column=0, row=5, columnspan=3, sticky='w', pady=(10, 0))

    def browse(self):
        d = filedialog.askdirectory(title='Carpeta de Rune Factory 5')
        if d:
            self.path.set(d)

    def run(self, action):
        game = self.path.get().strip()
        if not is_game(game):
            messagebox.showerror('Error', 'Esa carpeta no es la de Rune Factory 5.')
            return
        for b in (self.install_btn, self.uninstall_btn):
            b.state(['disabled'])
        self.status.config(text='Trabajando… (puede tardar unos segundos)')

        def work():
            try:
                msg, ok = action(game), True
            except (InstallError, OSError) as e:
                msg, ok = str(e), False
            except Exception as e:  # noqa: BLE001 - shown to the user instead of a silent crash
                msg, ok = f'Error inesperado: {e}', False
            self.after(0, self.done, msg, ok)
        threading.Thread(target=work, daemon=True).start()

    def done(self, msg, ok):
        for b in (self.install_btn, self.uninstall_btn):
            b.state(['!disabled'])
        self.status.config(text=msg.splitlines()[0])
        (messagebox.showinfo if ok else messagebox.showerror)('Listo' if ok else 'Error', msg)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('--instalar', '--desinstalar'):
        game = sys.argv[2] if len(sys.argv) > 2 else find_game()
        try:
            (install if sys.argv[1] == '--instalar' else uninstall)(game or '')
        except Exception:  # noqa: BLE001
            sys.exit(1)
        sys.exit(0)
    App().mainloop()
