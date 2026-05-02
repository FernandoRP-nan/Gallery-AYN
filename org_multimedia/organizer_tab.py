"""Pestaña de organización automática con barra de progreso y opciones."""

from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core.media_organizer import MediaOrganizer


class OrganizerApp:
    """Interfaz grafica simple para seleccionar ruta y ejecutar organizacion."""

    def __init__(self, parent: ttk.Frame) -> None:
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.root.title("Galería AYN")
        self.root.geometry("900x620")
        self.root.minsize(800, 560)
        self.root.resizable(True, True)

        self.selected_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Estado: esperando ruta.")
        self.progress_text = tk.StringVar(value="Progreso: 0/0")
        self.elapsed_text = tk.StringVar(value="Tiempo transcurrido: 00:00")
        self.progress_value = tk.DoubleVar(value=0.0)
        self.include_organized_var = tk.BooleanVar(value=False)
        self.include_comics_var = tk.BooleanVar(value=False)
        self.include_pending_var = tk.BooleanVar(value=False)
        self.remove_duplicates_var = tk.BooleanVar(value=False)
        self.group_similar_images_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.worker_thread: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.ui_queue: queue.Queue = queue.Queue()
        self.run_btn: ttk.Button | None = None
        self.cancel_btn: ttk.Button | None = None
        self.run_started_at: float | None = None
        self.indeterminate_active = False
        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.parent, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            container,
            text="Organiza imagenes y videos por anio/mes",
            font=("Sans", 13, "bold"),
        )
        title.pack(anchor="w", pady=(0, 8))

        description = ttk.Label(
            container,
            text=(
                "Selecciona una carpeta. El programa movera archivos multimedia a "
                "'Organizado/Anio/Mes', los .cbz a 'ComicsCBZ/Serie' y todo lo demas "
                "a 'PendientesRevision/Tipo'."
            ),
            wraplength=640,
        )
        description.pack(anchor="w", pady=(0, 12))

        path_frame = ttk.Frame(container)
        path_frame.pack(fill=tk.X, pady=(0, 12))

        path_entry = ttk.Entry(path_frame, textvariable=self.selected_path, width=78)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        path_entry.bind("<Return>", lambda _event: self._run_organizer())

        choose_btn = ttk.Button(path_frame, text="Seleccionar carpeta", command=self._choose_folder)
        choose_btn.pack(side=tk.LEFT, padx=(8, 0))

        warning = ttk.Label(
            container,
            text=(
                "Importante: se moveran archivos y se intentaran borrar carpetas vacias "
                "anteriores para dejar estructura limpia."
            ),
            foreground="#e0af68",
            wraplength=640,
        )
        warning.pack(anchor="w", pady=(0, 16))

        tips = ttk.Label(
            container,
            text=(
                "Tip: tambien puedes pegar la ruta manualmente y pulsar Enter. "
                "Ejemplo: /home/usuario/Documentos o ~/Videos"
            ),
            wraplength=720,
        )
        tips.pack(anchor="w", pady=(0, 12))

        self.progress_bar = ttk.Progressbar(
            container,
            orient="horizontal",
            length=720,
            mode="determinate",
            variable=self.progress_value,
            maximum=100,
        )
        self.progress_bar.pack(anchor="w", fill=tk.X, pady=(0, 6))

        progress_label = ttk.Label(container, textvariable=self.progress_text)
        progress_label.pack(anchor="w", pady=(0, 4))

        elapsed_label = ttk.Label(container, textvariable=self.elapsed_text, foreground="#565f89")
        elapsed_label.pack(anchor="w", pady=(0, 12))

        include_organized = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'Organizado' en esta ejecucion",
            variable=self.include_organized_var,
        )
        include_organized.pack(anchor="w", pady=(0, 10))

        include_comics = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'ComicsCBZ' en esta ejecucion",
            variable=self.include_comics_var,
        )
        include_comics.pack(anchor="w", pady=(0, 6))

        include_pending = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'PendientesRevision' en esta ejecucion",
            variable=self.include_pending_var,
        )
        include_pending.pack(anchor="w", pady=(0, 10))

        remove_duplicates = ttk.Checkbutton(
            container,
            text="Eliminar imagenes duplicadas (comparacion real por hash)",
            variable=self.remove_duplicates_var,
        )
        remove_duplicates.pack(anchor="w", pady=(0, 6))

        group_similar = ttk.Checkbutton(
            container,
            text="Agrupar imagenes por similitud de nombre (Screenshots/Facebook/etc.)",
            variable=self.group_similar_images_var,
        )
        group_similar.pack(anchor="w", pady=(0, 12))

        status = ttk.Label(container, textvariable=self.status_text, foreground="#7aa2f7")
        status.pack(anchor="w", pady=(0, 10))

        buttons_frame = ttk.Frame(container)
        buttons_frame.pack(anchor="e")
        self.cancel_btn = ttk.Button(buttons_frame, text="Cancelar", command=self._cancel_organizer, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self.run_btn = ttk.Button(buttons_frame, text="Organizar ahora", command=self._run_organizer)
        self.run_btn.pack(side=tk.RIGHT)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona la carpeta raiz a organizar")
        if folder:
            self.selected_path.set(folder)
            self.status_text.set(f"Estado: ruta seleccionada -> {folder}")
        else:
            self.status_text.set("Estado: no se selecciono carpeta.")

    @staticmethod
    def _normalize_input_path(raw_path: str) -> Path:
        # Permite usar "~" y variables de entorno en rutas escritas manualmente.
        expanded = os.path.expandvars(os.path.expanduser(raw_path.strip()))
        return Path(expanded).resolve()

    def _run_organizer(self) -> None:
        if self.is_running:
            return

        raw_folder = self.selected_path.get().strip()
        if not raw_folder:
            messagebox.showwarning("Falta ruta", "Selecciona una carpeta antes de ejecutar.")
            self.status_text.set("Estado: falta ruta para iniciar.")
            return

        folder_path = self._normalize_input_path(raw_folder)
        folder = str(folder_path)
        self.selected_path.set(folder)

        if not folder_path.exists() or not folder_path.is_dir():
            messagebox.showerror("Ruta invalida", f"La ruta no existe o no es carpeta:\n{folder}")
            self.status_text.set("Estado: ruta invalida, revisa el texto ingresado.")
            return

        confirm = messagebox.askyesno(
            "Confirmar reorganizacion",
            (
                "Se reorganizaran los archivos de esta ruta y sus subcarpetas.\n\n"
                f"Ruta: {folder}\n\n"
                "Deseas continuar?"
            ),
        )
        if not confirm:
            self.status_text.set("Estado: operacion cancelada por el usuario.")
            return

        try:
            self.is_running = True
            self.cancel_event.clear()
            self.run_started_at = time.time()
            self.progress_value.set(0)
            self.progress_text.set("Progreso: escaneando archivos...")
            self.elapsed_text.set("Tiempo transcurrido: 00:00")
            self.status_text.set("Estado: trabajando...")
            self._start_indeterminate_progress()
            if self.run_btn:
                self.run_btn.config(state=tk.DISABLED)
            if self.cancel_btn:
                self.cancel_btn.config(state=tk.NORMAL)

            def worker() -> None:
                try:
                    organizer = MediaOrganizer(
                        folder_path,
                        include_organized_scan=self.include_organized_var.get(),
                        include_comics_scan=self.include_comics_var.get(),
                        include_pending_scan=self.include_pending_var.get(),
                        remove_duplicate_images=self.remove_duplicates_var.get(),
                        group_similar_images=self.group_similar_images_var.get(),
                    )

                    def on_progress(current: int, total: int, detail: str) -> None:
                        self.ui_queue.put(("progress", current, total, detail))

                    stats = organizer.organize(progress_callback=on_progress, cancel_event=self.cancel_event)
                    self.ui_queue.put(("done", stats, organizer.cancel_requested))
                except Exception as exc:
                    self.ui_queue.put(("error", str(exc)))

            self.worker_thread = threading.Thread(target=worker, daemon=True)
            self.worker_thread.start()
            self._poll_ui_queue()
        except Exception as exc:
            self._finish_run()
            messagebox.showerror("Error", f"No se pudo completar el proceso:\n{exc}")
            self.status_text.set(f"Estado: error -> {exc}")

    def _poll_ui_queue(self) -> None:
        while not self.ui_queue.empty():
            item = self.ui_queue.get_nowait()
            item_type = item[0]
            if item_type == "progress":
                _, current, total, detail = item
                if self.indeterminate_active and total > 0:
                    self._stop_indeterminate_progress()
                percent = (current / total * 100.0) if total > 0 else 100.0
                self.progress_value.set(percent)
                self.progress_text.set(f"Progreso: {current}/{total}")
                self.status_text.set(f"Estado: {detail}")
            elif item_type == "done":
                _, stats, was_cancelled = item
                self._finish_run()
                if was_cancelled:
                    messagebox.showinfo(
                        "Proceso cancelado",
                        (
                            "La organizacion fue cancelada por el usuario.\n\n"
                            f"Multimedia movida: {stats.moved_media}\n"
                            f"CBZ agrupados: {stats.moved_cbz}\n"
                            f"Otros archivos movidos: {stats.moved_other}\n"
                            f"Imagenes duplicadas eliminadas: {stats.deleted_duplicate_images}\n"
                            f"Imagenes agrupadas por nombre: {stats.grouped_similar_images}\n"
                            f"Carpetas vacias eliminadas: {stats.deleted_dirs}\n"
                            f"Errores: {stats.errors}"
                        ),
                    )
                    self.status_text.set("Estado: proceso cancelado.")
                else:
                    messagebox.showinfo(
                        "Proceso completado",
                        (
                            "Organizacion finalizada.\n\n"
                            f"Multimedia movida: {stats.moved_media}\n"
                            f"CBZ agrupados: {stats.moved_cbz}\n"
                            f"Otros archivos movidos: {stats.moved_other}\n"
                            f"Imagenes duplicadas eliminadas: {stats.deleted_duplicate_images}\n"
                            f"Imagenes agrupadas por nombre: {stats.grouped_similar_images}\n"
                            f"Carpetas vacias eliminadas: {stats.deleted_dirs}\n"
                            f"Errores: {stats.errors}"
                        ),
                    )
                    self.status_text.set(
                        "Estado: completado. "
                        f"Multimedia={stats.moved_media}, CBZ={stats.moved_cbz}, "
                        f"Otros={stats.moved_other}, Duplicadas={stats.deleted_duplicate_images}, "
                        f"Agrupadas={stats.grouped_similar_images}, Errores={stats.errors}"
                    )
                    self.progress_value.set(100.0)
            elif item_type == "error":
                _, error_message = item
                self._finish_run()
                messagebox.showerror("Error", f"No se pudo completar el proceso:\n{error_message}")
                self.status_text.set(f"Estado: error -> {error_message}")

        if self.is_running:
            self._update_elapsed_time()
            self.root.after(120, self._poll_ui_queue)

    def _cancel_organizer(self) -> None:
        if not self.is_running:
            return
        self.cancel_event.set()
        self.status_text.set("Estado: cancelando proceso, espera...")
        if self.cancel_btn:
            self.cancel_btn.config(state=tk.DISABLED)

    def _finish_run(self) -> None:
        self.is_running = False
        self._stop_indeterminate_progress()
        self.run_started_at = None
        if self.run_btn:
            self.run_btn.config(state=tk.NORMAL)
        if self.cancel_btn:
            self.cancel_btn.config(state=tk.DISABLED)

    def _update_elapsed_time(self) -> None:
        if self.run_started_at is None:
            return
        elapsed_seconds = int(time.time() - self.run_started_at)
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        self.elapsed_text.set(f"Tiempo transcurrido: {minutes:02d}:{seconds:02d}")

    def _start_indeterminate_progress(self) -> None:
        if not self.indeterminate_active:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(12)
            self.indeterminate_active = True

    def _stop_indeterminate_progress(self) -> None:
        if self.indeterminate_active:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.indeterminate_active = False


