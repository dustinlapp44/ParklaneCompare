from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import pandas as pd
from core.csv_processor import CSVProcessor, strip_whitespace, convert_hours_to_float
from core.pdf_parser import PDFParser  # <- if you want to keep it around
from core.csv_exporter import CSVExporter


class PDFCSVApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Data Parser")
        self.root.geometry("1000x700")
        self.original_df = pd.DataFrame()
        self.formatted_df = pd.DataFrame()
        self.last_loaded_file = None
        self._init_styles()
        self._init_widgets()

    def _init_styles(self):
        style = ttk.Style(self.root)
        #style.theme_use('default')
        style.theme_use("clam")

    def _init_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.csv_tab = ttk.Frame(self.notebook)
        self.pdf_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.csv_tab, text="CSV Parser")
        self.notebook.add(self.pdf_tab, text="PDF Parser")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_tab(self.csv_tab, self.import_csv)
        self._build_tab(self.pdf_tab, self.import_pdf)

    def _build_tab(self, parent, import_callback):
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Format options
        options_frame = ttk.LabelFrame(frame, text="Format Options")
        options_frame.pack(fill=tk.X, pady=5)

        # Store checkbox states
        parent.strip_ws_var = tk.BooleanVar(value=True)
        parent.convert_hours_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Strip Whitespace", variable=parent.strip_ws_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Convert HH:MM to Float", variable=parent.convert_hours_var).pack(side=tk.LEFT, padx=5)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Import", command=import_callback).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reload", command=self.reload_file).pack(side=tk.LEFT, padx=5)

        tree = ttk.Treeview(frame, show="headings", selectmode="browse")
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        parent.tree = tree

    def import_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        self.last_loaded_file = file_path
        self._process_csv_file(file_path)

    def _process_csv_file(self, file_path):
        formatters = []
        if self.csv_tab.strip_ws_var.get():
            formatters.append(strip_whitespace)
        if self.csv_tab.convert_hours_var.get():
            formatters.append(convert_hours_to_float)

        try:
            processor = CSVProcessor(file_path, formatters)
            self.formatted_df = processor.load_and_process()
            self.original_df = pd.read_csv(file_path)

            self.dataframe = self.formatted_df.copy()
            self._display_dataframe(self.csv_tab.tree)
            print(f"[INFO] CSV imported with shape: {self.dataframe.shape}")
        except Exception as e:
            print(f"[ERROR] Failed to parse CSV: {e}")
            messagebox.showerror("Error", f"Failed to parse CSV:\n{e}")
    
    def reload_file(self):
        if not self.last_loaded_file:
            messagebox.showwarning("No File", "No file has been imported yet.")
            return

        print("[INFO] Reloading file:", self.last_loaded_file)
        self._process_csv_file(self.last_loaded_file)

    def import_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return
        try:
            parser = PDFParser(file_path)
            self.dataframe = parser.parse_to_dataframe()
            self._display_dataframe(self.pdf_tab.tree)
        except Exception as e:
            print(f"[ERROR] Failed to parse PDF: {e}")
            messagebox.showerror("Error", f"Failed to parse PDF:\n{e}")

    def export_csv(self):
        if self.dataframe.empty:
            print("[WARNING] No data to export.")
            messagebox.showwarning("No Data", "No data to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        try:
            CSVExporter.export(self.dataframe, file_path)
            print(f"[INFO] CSV exported to: {file_path}")
            messagebox.showinfo("Success", f"CSV exported to:\n{file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to export CSV: {e}")
            messagebox.showerror("Error", f"Failed to export CSV:\n{e}")

    def _display_dataframe(self, treeview):
        treeview.delete(*treeview.get_children())

        columns = [
            f"Column_{i}" if not col or pd.isna(col) else str(col)
            for i, col in enumerate(self.dataframe.columns)
        ]
        treeview["columns"] = columns
        treeview["show"] = "headings"

        for col in columns:
            treeview.heading(col, text=col)
            treeview.column(col, width=150, anchor=tk.W)

        for idx, row in self.dataframe.iterrows():
            values = list(row)

            treeview.insert("", "end", values=values)

    def run(self):
        self.root.mainloop()
