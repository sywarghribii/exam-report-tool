"""
gui.py
======

Optional tkinter front-end — a thin wrapper over the toolkit.  All the real
work lives in the library modules; this file only wires the widgets to
:func:`exam_toolkit.export_files_to_excel`.

Run:
    python -m exam_toolkit.gui
"""

from __future__ import annotations

import pathlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from .comments import CommentStore
from .excel_export import export_reports_to_excel
from .extractor import parse_reports


class ExamReportApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("EXAM Report Toolkit → Excel")
        master.geometry("560x340")
        master.resizable(False, False)

        frm = ttk.Frame(master, padding=15)
        frm.pack(fill="both", expand=True)

        # ---- XML files ----
        ttk.Label(frm, text="XML report file(s):").grid(row=0, column=0, sticky="w")
        self.file_entry = ttk.Entry(frm, width=60, state="readonly")
        self.file_entry.grid(row=1, column=0, pady=5, sticky="w")
        ttk.Button(frm, text="Browse …", command=self.select_files).grid(row=1, column=1, padx=5)

        # ---- optional comment store ----
        ttk.Label(frm, text="Comment store (optional JSON):").grid(row=2, column=0, sticky="w")
        self.comment_entry = ttk.Entry(frm, width=60, state="readonly")
        self.comment_entry.grid(row=3, column=0, pady=5, sticky="w")
        ttk.Button(frm, text="Browse …", command=self.select_comments).grid(row=3, column=1, padx=5)

        # ---- destination ----
        ttk.Label(frm, text="Save workbook as:").grid(row=4, column=0, sticky="w")
        self.save_entry = ttk.Entry(frm, width=60, state="readonly")
        self.save_entry.grid(row=5, column=0, pady=5, sticky="w")
        ttk.Button(frm, text="Browse …", command=self.select_save_path).grid(row=5, column=1, padx=5)

        # ---- options ----
        self.analysis_var = tk.BooleanVar(value=True)
        self.summary_var = tk.BooleanVar(value=True)
        opt = ttk.Frame(frm)
        opt.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(opt, text="Include Fail-Analysis sheet", variable=self.analysis_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(opt, text="Include Summary sheet", variable=self.summary_var).grid(row=0, column=1, padx=15, sticky="w")

        # ---- actions ----
        btn = ttk.Frame(frm)
        btn.grid(row=7, column=0, columnspan=2, pady=15)
        ttk.Button(btn, text="Start conversion", command=self.start).grid(row=0, column=0, padx=5)
        ttk.Button(btn, text="Quit", command=master.quit).grid(row=0, column=1, padx=5)

        self.xml_paths: List[pathlib.Path] = []
        self.comment_path: Optional[pathlib.Path] = None
        self.save_path: Optional[pathlib.Path] = None

    # --------------------------------------------------------------
    def _set_entry(self, entry: ttk.Entry, text: str) -> None:
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, text)
        entry.config(state="readonly")

    def select_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select EXAM XML report file(s)",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if files:
            self.xml_paths = [pathlib.Path(f) for f in files]
            self._set_entry(self.file_entry, "; ".join(str(p) for p in self.xml_paths))

    def select_comments(self) -> None:
        file = filedialog.askopenfilename(
            title="Select comment store JSON (optional)",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if file:
            self.comment_path = pathlib.Path(file)
            self._set_entry(self.comment_entry, str(self.comment_path))

    def select_save_path(self) -> None:
        file = filedialog.asksaveasfilename(
            title="Save Excel workbook",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if file:
            self.save_path = pathlib.Path(file)
            self._set_entry(self.save_entry, str(self.save_path))

    # --------------------------------------------------------------
    def start(self) -> None:
        if not self.xml_paths:
            messagebox.showwarning("Missing files", "Please select at least one XML file.")
            return
        if not self.save_path:
            messagebox.showwarning("Missing destination", "Please choose where to save the Excel file.")
            return
        try:
            reports = parse_reports(self.xml_paths)
            store = CommentStore.load(self.comment_path) if self.comment_path else None
            export_reports_to_excel(
                reports,
                self.save_path,
                comment_store=store,
                include_analysis=self.analysis_var.get(),
                include_summary=self.summary_var.get(),
            )
            messagebox.showinfo("Success", f"Excel file written to:\n{self.save_path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"Something went wrong:\n{exc}")


def main() -> None:
    root = tk.Tk()
    ExamReportApp(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()


if __name__ == "__main__":
    main()
