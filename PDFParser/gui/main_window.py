from tkinter import filedialog, messagebox, ttk
from tksheet import Sheet
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

        # Sheet
        sheet = Sheet(frame)
        sheet.pack(fill=tk.BOTH, expand=True)
        parent.sheet = sheet

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
            self._display_dataframe(self.csv_tab.sheet, highlight_changes=True)
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
            self._display_dataframe(self.csv_tab.sheet, highlight_changes=True)
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

    def _display_dataframe(self, sheet_widget, highlight_changes=False):
        df = self.dataframe
        sheet_widget.set_sheet_data(df.values.tolist(), reset_col_positions=True, reset_row_positions=True)
        sheet_widget.headers(df.columns.tolist())
        sheet_widget.enable_bindings((
            "single_select", "row_select", "column_width_resize", "arrowkeys",
            "rc_select", "copy", "paste", "delete", "undo", "edit_cell"))

        if highlight_changes and not self.original_df.empty:
            changed_cells = []

            for row in range(min(len(self.original_df), len(self.dataframe))):
                for col in range(len(df.columns)):
                    val_new = str(df.iat[row, col]).strip()
                    val_old = str(self.original_df.iat[row, col]).strip()
                    if val_new != val_old:
                        changed_cells.append((row, col))

            for (r, c) in changed_cells:
                sheet_widget.highlight_cells(row=r, column=c, bg="#fffcc0")

    def run(self):
        self.root.mainloop()
