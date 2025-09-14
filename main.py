# main.py
import re
import sys

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QMenu,
                               QMessageBox, QPushButton, QSplitter,
                               QStatusBar, QTableWidget, QTableWidgetItem,
                               QTextEdit, QToolBar, QSpinBox, QVBoxLayout,
                               QWidget)

from model import ProjectModel


class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("echo_finder")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize the model
        self.model = ProjectModel()
        self.is_dirty = False

        self._setup_ui()
        self._connect_signals()

        # Load an initial new project
        self.model.new_project()

    def _setup_ui(self):
        # --- Central Widget & Layouts ---
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(main_splitter)

        # --- Widgets ---
        self.narrative_text_edit = QTextEdit()
        self.narrative_text_edit.setPlaceholderText("Paste or type your narrative text here...")
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Phrase", "Count", "Length"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Whitelist Section
        whitelist_widget = QWidget()
        whitelist_layout = QVBoxLayout(whitelist_widget)
        whitelist_layout.setContentsMargins(0,0,0,0)
        
        whitelist_controls_layout = QHBoxLayout()
        self.add_whitelist_button = QPushButton("Add")
        self.remove_whitelist_button = QPushButton("Remove")
        whitelist_controls_layout.addWidget(self.add_whitelist_button)
        whitelist_controls_layout.addWidget(self.remove_whitelist_button)
        whitelist_controls_layout.addStretch()

        self.whitelist_list = QListWidget()
        whitelist_layout.addLayout(whitelist_controls_layout)
        whitelist_layout.addWidget(self.whitelist_list)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # --- Add widgets to splitter ---
        main_splitter.addWidget(self.narrative_text_edit)
        main_splitter.addWidget(self.results_table)
        main_splitter.addWidget(whitelist_widget)
        main_splitter.setSizes([400, 300, 100]) # Initial sizing

        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        edit_menu = menu_bar.addMenu("&Edit")
        help_menu = menu_bar.addMenu("&Help")

        # File Actions
        action_new = QAction("&New", self)
        action_new.setShortcut(QKeySequence.StandardKey.New)
        action_new.triggered.connect(self.on_new_project)

        action_open = QAction("&Open...", self)
        action_open.setShortcut(QKeySequence.StandardKey.Open)
        action_open.triggered.connect(self.on_open_project)

        action_save = QAction("&Save", self)
        action_save.setShortcut(QKeySequence.StandardKey.Save)
        action_save.triggered.connect(self.on_save_project)

        action_save_as = QAction("Save &As...", self)
        action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        action_save_as.triggered.connect(self.on_save_as_project)

        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addActions([action_new, action_open, action_save, action_save_as])
        file_menu.addSeparator()
        file_menu.addAction(action_exit)

        # Edit Actions
        action_paste = QAction("&Paste from Clipboard", self)
        action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        action_paste.triggered.connect(self.narrative_text_edit.paste)
        edit_menu.addAction(action_paste)

        # Help Actions
        action_about = QAction("&About echo_finder", self)
        action_about.triggered.connect(self.on_about)
        help_menu.addAction(action_about)

        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel("Min Length: 2"))
        
        toolbar.addWidget(QLabel("  Max Length: "))
        self.max_len_spinbox = QSpinBox()
        self.max_len_spinbox.setMinimum(2)
        self.max_len_spinbox.setValue(8)
        toolbar.addWidget(self.max_len_spinbox)

        self.process_button = QPushButton("Find Them / Find Again")
        self.process_button.setToolTip("Process the text to find echoes")
        toolbar.addWidget(self.process_button)

        toolbar.addSeparator()
        
        toolbar.addWidget(QLabel("Preset: "))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Most Repeated (Short to Long)", "most_repeated_short_to_long")
        self.preset_combo.addItem("Longest First (by Word Count)", "longest_first_by_word_count")
        toolbar.addWidget(self.preset_combo)

    def _connect_signals(self):
        # Model -> UI
        self.model.project_loaded.connect(self.on_project_loaded)
        self.model.status_message.connect(self.status_bar.showMessage)
        self.model.echo_results_updated.connect(self.update_results_table)
        self.model.whitelist_updated.connect(self.update_whitelist_display)
        self.model.max_len_available.connect(self.on_max_len_available)
        
        # UI -> Model / UI Logic
        self.process_button.clicked.connect(self.on_process_text)
        self.narrative_text_edit.textChanged.connect(self.on_text_changed)
        self.max_len_spinbox.valueChanged.connect(lambda: self.set_dirty(True))
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        
        # Whitelist buttons
        self.add_whitelist_button.clicked.connect(self.on_add_whitelist)
        self.remove_whitelist_button.clicked.connect(self.on_remove_whitelist)

    # --- Slots for Model Signals ---

    @Slot(dict)
    def on_project_loaded(self, data):
        self.narrative_text_edit.setText(data.get("original_text", ""))
        self.max_len_spinbox.setValue(data.get("max_phrase_length", 8))
        
        preset_id = data.get("last_used_sort_preset", "most_repeated_short_to_long")
        index = self.preset_combo.findData(preset_id)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

        self.update_whitelist_display(data.get("custom_whitelist", []))
        self.update_results_table(data.get("echo_results", []))
        
        self.setWindowTitle(f"echo_finder - {data.get('project_name', 'Unnamed Project')}")
        self.set_dirty(False)
        self.update_process_button_state()

    @Slot(list)
    def update_results_table(self, results):
        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(item['phrase']))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(item['count'])))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(item['length'])))
        self.results_table.resizeColumnsToContents()

    @Slot(list)
    def update_whitelist_display(self, whitelist):
        self.whitelist_list.clear()
        for item in whitelist:
            self.whitelist_list.addItem(QListWidgetItem(item))

    @Slot(int)
    def on_max_len_available(self, max_len):
        self.max_len_spinbox.setMaximum(max(2, max_len))
        # Clamp value if it's now out of bounds
        if self.max_len_spinbox.value() > max_len:
            self.max_len_spinbox.setValue(max_len)

    # --- Slots for UI Events ---

    def on_new_project(self):
        self.model.new_project()

    def on_open_project(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            self.model.load_project(filepath)

    def on_save_project(self):
        if self.model.current_project_path:
            self._save_current_data_to_model()
            self.model.save_project(str(self.model.current_project_path))
        else:
            self.on_save_as_project()

    def on_save_as_project(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            self._save_current_data_to_model()
            self.model.save_project(filepath)
            self.setWindowTitle(f"echo_finder - {self.model.data['project_name']}")

    def on_process_text(self):
        self.set_dirty(False)
        self._save_current_data_to_model()
        self.model.process_text()

    def on_text_changed(self):
        self.set_dirty(True)
        self.update_process_button_state()
    
    def on_preset_changed(self, index):
        preset_id = self.preset_combo.itemData(index)
        self.model.update_data("last_used_sort_preset", preset_id)
        self.model.sort_results()

    def on_add_whitelist(self):
        text, ok = QInputDialog.getText(self, "Add Whitelist Entry", "Enter abbreviation:")
        if ok and text.strip():
            self.model.add_whitelist_entry(text.strip())
            self.set_dirty(True)

    def on_remove_whitelist(self):
        selected_items = self.whitelist_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select a whitelist entry to remove.")
            return
        
        for item in selected_items:
            self.model.remove_whitelist_entry(item.text())
        self.set_dirty(True)

    def on_about(self):
        QMessageBox.about(
            self,
            "About echo_finder",
            """
            <b>echo_finder</b>
            <p>A tool to identify and analyze repeated phrases in text.</p>
            <p>License: MIT</p>
            <p>Copyright: fernicar</p>
            <p>Repository: <a href='https://github.com/fernicar/echo_finder'>github.com/fernicar/echo_finder</a></p>
            """
        )
    
    # --- Helper Methods ---

    def set_dirty(self, is_dirty):
        self.is_dirty = is_dirty
        style = "border: 1px solid red;" if is_dirty else ""
        self.narrative_text_edit.setStyleSheet(style)
        
    def _save_current_data_to_model(self):
        self.model.update_data("original_text", self.narrative_text_edit.toPlainText())
        self.model.update_data("max_phrase_length", self.max_len_spinbox.value())
    
    def update_process_button_state(self):
        # Disable button if text has fewer than 2 words
        text = self.narrative_text_edit.toPlainText()
        word_count = len(re.findall(r'\b\w+\b', text))
        self.process_button.setEnabled(word_count >= 2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Consistent modern look
    window = MainWindow()
    window.show()
    sys.exit(app.exec())