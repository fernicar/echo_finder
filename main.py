# main.py
import re
import sys

from PySide6.QtCore import (QCoreApplication, QSettings, Qt, QTimer, Slot, QRegularExpression)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QKeySequence, QPalette,
                           QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QSplitter, QStatusBar,
                               QTableWidget, QTableWidgetItem, QTextEdit,
                               QToolBar, QSpinBox, QVBoxLayout, QWidget, QStyleFactory)

from model import ProjectModel


class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("echo_finder_TINS_Edition")
        self.setGeometry(100, 100, 1200, 800)

        self.settings = QSettings()

        self.model = ProjectModel()
        self.last_clean_state = None 

        self._setup_ui()
        self._connect_signals()

        self.on_new_project()

    def _get_current_state_snapshot(self):
        """Captures the current state of all user inputs that affect processing."""
        whitelist_items = [self.whitelist_list.item(i).text() for i in range(self.whitelist_list.count())]
        return (
            self.narrative_text_edit.toPlainText(),
            self.min_words_spinbox.value(),
            self.max_words_spinbox.value(),
            self.strip_punctuation_checkbox.isChecked(),
            tuple(sorted(whitelist_items))
        )

    def _check_dirty_state(self):
        """Compares current state to the last clean state and updates the UI."""
        is_dirty = self._get_current_state_snapshot() != self.last_clean_state
        self.narrative_text_edit.setStyleSheet("border: 1px solid red;" if is_dirty else "")

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(main_splitter)

        self.narrative_text_edit = QTextEdit()
        self.narrative_text_edit.setPlaceholderText("Paste or type your narrative text here...")

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Count", "Words", "Phrase"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        whitelist_widget = QWidget()
        whitelist_layout = QVBoxLayout(whitelist_widget)
        whitelist_layout.setContentsMargins(0, 0, 0, 0)

        whitelist_controls_layout = QHBoxLayout()
        self.strip_punctuation_checkbox = QCheckBox("Strip Punctuation")
        self.add_whitelist_button = QPushButton("Add")
        self.remove_whitelist_button = QPushButton("Remove")
        whitelist_controls_layout.addWidget(self.strip_punctuation_checkbox)
        whitelist_controls_layout.addStretch()
        whitelist_controls_layout.addWidget(QLabel("Whitelist:"))
        whitelist_controls_layout.addWidget(self.add_whitelist_button)
        whitelist_controls_layout.addWidget(self.remove_whitelist_button)

        self.whitelist_list = QListWidget()
        whitelist_layout.addLayout(whitelist_controls_layout)
        whitelist_layout.addWidget(self.whitelist_list)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        main_splitter.addWidget(self.narrative_text_edit)
        main_splitter.addWidget(self.results_table)
        main_splitter.addWidget(whitelist_widget)
        main_splitter.setSizes([400, 300, 100])

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        edit_menu = menu_bar.addMenu("&Edit")
        help_menu = menu_bar.addMenu("&Help")

        action_new = QAction("&New", self)
        action_new.setShortcut(QKeySequence(QKeySequence.StandardKey.New))
        action_new.triggered.connect(self.on_new_project)
        action_open = QAction("&Open...", self)
        action_open.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        action_open.triggered.connect(self.on_open_project)
        action_save = QAction("&Save", self)
        action_save.setShortcut(QKeySequence(QKeySequence.StandardKey.Save))
        action_save.triggered.connect(self.on_save_project)
        action_save_as = QAction("Save &As...", self)
        action_save_as.setShortcut(QKeySequence(QKeySequence.StandardKey.SaveAs))
        action_save_as.triggered.connect(self.on_save_as_project)
        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        action_exit.triggered.connect(self.close)
        file_menu.addActions([action_new, action_open, action_save, action_save_as, action_exit])

        action_paste = QAction("&Paste from Clipboard", self)
        action_paste.setShortcut(QKeySequence(QKeySequence.StandardKey.Paste))
        action_paste.triggered.connect(self.narrative_text_edit.paste)
        self.action_auto_copy = QAction("Auto Copy Phrase to Clipboard", self, checkable=True, checked=True)
        edit_menu.addActions([action_paste, self.action_auto_copy])
        edit_menu.addSeparator()

        self.appearance_menu = edit_menu.addMenu("Appearance")
        self.style_action_group = QActionGroup(self)
        self.style_action_group.setExclusive(True)
        current_style = self.settings.value("gui/style", QApplication.style().objectName())
        for style_name in QStyleFactory.keys():
            action = QAction(style_name, self, checkable=True)
            if style_name == current_style: action.setChecked(True)
            self.appearance_menu.addAction(action)
            self.style_action_group.addAction(action)

        self.theme_menu = edit_menu.addMenu("Theme")
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        current_theme = self.settings.value("gui/theme", Qt.ColorScheme.Unknown, type=int)
        theme_map = { "Auto (System Default)": Qt.ColorScheme.Unknown, "Light": Qt.ColorScheme.Light, "Dark": Qt.ColorScheme.Dark }
        for name, theme_id in theme_map.items():
            action = QAction(name, self, checkable=True)
            action.setData(theme_id)
            if theme_id == current_theme: action.setChecked(True)
            self.theme_menu.addAction(action)
            self.theme_action_group.addAction(action)

        action_about = QAction("&About echo_finder_TINS_Edition", self)
        action_about.triggered.connect(self.on_about)
        help_menu.addAction(action_about)

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("Min Words:"))
        self.min_words_spinbox = QSpinBox(minimum=2, value=2)
        toolbar.addWidget(self.min_words_spinbox)
        toolbar.addWidget(QLabel("  Max Words: "))
        self.max_words_spinbox = QSpinBox(minimum=2, value=8)
        toolbar.addWidget(self.max_words_spinbox)
        self.min_words_spinbox.setMaximum(self.max_words_spinbox.value())
        self.max_words_spinbox.setMinimum(self.min_words_spinbox.value())
        self.process_button = QPushButton("Find Them / Find Again")
        toolbar.addWidget(self.process_button)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Preset: "))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("By Word Count (Desc)", "by_word_count")
        self.preset_combo.addItem("By Repetition Count (Desc)", "by_repetition_count")
        toolbar.addWidget(self.preset_combo)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Highlight:"))
        self.highlight_field = QLineEdit(placeholderText="Select from list or type here...")
        self.highlight_field.setClearButtonEnabled(True)
        toolbar.addWidget(self.highlight_field)

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(250)

    def _connect_signals(self):
        self.model.project_loaded.connect(self.on_project_loaded)
        self.model.status_message.connect(self.status_bar.showMessage)
        self.model.echo_results_updated.connect(self.update_results_table)
        self.model.whitelist_updated.connect(self.update_whitelist_display)
        self.model.max_words_available.connect(self.on_max_words_available)

        self.process_button.clicked.connect(self.on_process_text)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.min_words_spinbox.valueChanged.connect(self._check_dirty_state)
        self.max_words_spinbox.valueChanged.connect(self._check_dirty_state)
        self.strip_punctuation_checkbox.stateChanged.connect(self._check_dirty_state)

        self.add_whitelist_button.clicked.connect(self.on_add_whitelist)
        self.remove_whitelist_button.clicked.connect(self.on_remove_whitelist)
        self.results_table.cellClicked.connect(self.on_result_cell_clicked)

        self.style_action_group.triggered.connect(self.on_style_changed)
        self.theme_action_group.triggered.connect(self.on_theme_changed)

        self.narrative_text_edit.textChanged.connect(self.on_narrative_text_changed)
        self.highlight_field.textChanged.connect(self.on_highlight_text_changed)
        self.debounce_timer.timeout.connect(self._perform_live_highlight)

    @Slot(dict)
    def on_project_loaded(self, data):
        self.narrative_text_edit.setText(data.get("original_text", ""))
        self.min_words_spinbox.blockSignals(True)
        self.max_words_spinbox.blockSignals(True)
        self.min_words_spinbox.setValue(data.get("min_phrase_words", 2))
        self.max_words_spinbox.setValue(data.get("max_phrase_words", 8))
        self.min_words_spinbox.blockSignals(False)
        self.max_words_spinbox.blockSignals(False)

        self.strip_punctuation_checkbox.setChecked(data.get("strip_punctuation", True))

        preset_id = data.get("last_used_sort_preset", self.settings.value("last_used_sort_preset", "by_word_count"))
        index = self.preset_combo.findData(preset_id)
        if index >= 0: self.preset_combo.setCurrentIndex(index)

        self.update_whitelist_display(data.get("custom_whitelist", []))
        self.update_results_table(data.get("echo_results", []))

        self.setWindowTitle(f"echo_finder_TINS_Edition - {data.get('project_name', 'Unnamed Project')}")
        self.highlight_field.clear()

        self.last_clean_state = self._get_current_state_snapshot()
        self._check_dirty_state()
        self.update_process_button_state()

    @Slot(list)
    def update_results_table(self, results):
        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(results))
        for row, item in enumerate(results):
            # Display the CLEAN, NORMALIZED phrase to the user
            phrase_item = QTableWidgetItem(item['phrase'])
            phrase_item.setData(Qt.ItemDataRole.UserRole, item) # Store the whole result object

            count_item = QTableWidgetItem(str(item['count']))
            count_item.setData(Qt.ItemDataRole.UserRole, item['count'])
            
            self.results_table.setItem(row, 0, count_item)
            self.results_table.setItem(row, 1, QTableWidgetItem(str(item['words'])))
            self.results_table.setItem(row, 2, phrase_item)
            
        self.results_table.resizeColumnsToContents()
        self.results_table.horizontalHeader().setStretchLastSection(True)

        self.last_clean_state = self._get_current_state_snapshot()
        self._check_dirty_state()

    @Slot(list)
    def update_whitelist_display(self, whitelist):
        self.whitelist_list.clear()
        self.whitelist_list.addItems(whitelist)
        self._check_dirty_state()

    @Slot(int)
    def on_max_words_available(self, max_words):
        self.min_words_spinbox.blockSignals(True)
        self.max_words_spinbox.blockSignals(True)
        
        current_max = self.max_words_spinbox.value()
        safe_max = max(2, max_words)
        self.max_words_spinbox.setMaximum(safe_max)
        if current_max > safe_max: self.max_words_spinbox.setValue(safe_max)

        self.min_words_spinbox.blockSignals(False)
        self.max_words_spinbox.blockSignals(False)
    
    def on_new_project(self):
        self._clear_highlights()
        saved_preset = self.settings.value("last_used_sort_preset", "by_word_count")
        self.model.new_project(preferred_preset=str(saved_preset))

    def on_open_project(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)")
        if filepath:
            self._clear_highlights()
            self.model.load_project(filepath)

    def on_save_project(self):
        if self.model.current_project_path:
            self._save_current_data_to_model()
            self.model.save_project(str(self.model.current_project_path))
        else: self.on_save_as_project()

    def on_save_as_project(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "JSON Files (*.json)")
        if filepath:
            self._save_current_data_to_model()
            self.model.save_project(filepath)
            self.setWindowTitle(f"echo_finder_TINS_Edition - {self.model.data['project_name']}")

    def on_process_text(self):
        self.highlight_field.clear()
        self._save_current_data_to_model()
        self.model.process_text()

    def on_narrative_text_changed(self):
        self._check_dirty_state()
        self.update_process_button_state()
        if not self.highlight_field.text(): return
        self.debounce_timer.start()

    def on_highlight_text_changed(self):
        self.debounce_timer.start()

    def on_preset_changed(self, index):
        preset_id = self.preset_combo.itemData(index)
        self.model.update_data("last_used_sort_preset", preset_id)
        self.model.sort_results()
        self.settings.setValue("last_used_sort_preset", preset_id)

    @Slot(QAction)
    def on_style_changed(self, action):
        style_name = action.text()
        QApplication.setStyle(style_name)
        self.settings.setValue("gui/style", style_name)

    @Slot(QAction)
    def on_theme_changed(self, action):
        theme_id = action.data()
        QApplication.styleHints().setColorScheme(Qt.ColorScheme(theme_id))
        self.settings.setValue("gui/theme", theme_id)

    @Slot(int, int)
    def on_result_cell_clicked(self, row, column):
        phrase_item = self.results_table.item(row, 2)
        if phrase_item:
            # Use the CLEAN phrase for highlighting logic and copying
            phrase_text = phrase_item.text()
            
            self.highlight_field.setText(phrase_text)
            if self.action_auto_copy.isChecked():
                QApplication.clipboard().setText(phrase_text)
                self.status_bar.showMessage(f"Copied to clipboard: '{phrase_text}'", 4000)

    def _clear_highlights(self):
        cursor = QTextCursor(self.narrative_text_edit.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())

    @Slot()
    def _perform_live_highlight(self):
        self._clear_highlights()
        search_text = self.highlight_field.text().strip()

        # Restore original counts before performing a new search
        for row in range(self.results_table.rowCount()):
            count_item = self.results_table.item(row, 0)
            if count_item is not None:
                original_count = count_item.data(Qt.ItemDataRole.UserRole)
                count_item.setText(str(original_count))
                count_item.setForeground(QApplication.palette().text().color())
        
        if not search_text: return
        
        # Build a regex that finds the words separated by non-word characters
        words = re.split(r'\s+', search_text)
        pattern = r'\b' + r'\W+'.join(re.escape(word) for word in words) + r'\b'
        q_regex = QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption)
        
        palette = self.palette()
        highlight_color = palette.color(QPalette.ColorRole.Highlight)
        highlighted_text_color = palette.color(QPalette.ColorRole.HighlightedText)
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(highlight_color)
        highlight_format.setForeground(highlighted_text_color)
        
        doc = self.narrative_text_edit.document()
        cursor = QTextCursor(doc)
        found_count = 0
        while True:
            cursor = doc.find(q_regex, cursor)
            if cursor.isNull(): break
            found_count += 1
            cursor.mergeCharFormat(highlight_format)
            
        # Update the count for the *exact* phrase being highlighted
        for row in range(self.results_table.rowCount()):
            phrase_item = self.results_table.item(row, 2)
            if phrase_item and phrase_item.text() == search_text:
                count_item = self.results_table.item(row, 0)
                if count_item:
                    count_item.setText(str(found_count))
                    if found_count < 2:
                        count_item.setForeground(Qt.GlobalColor.gray)
                    else:
                        count_item.setForeground(QApplication.palette().text().color())

    def on_add_whitelist(self):
        text, ok = QInputDialog.getText(self, "Add Whitelist Entry", "Enter abbreviation:")
        if ok and text.strip():
            self.model.add_whitelist_entry(text.strip())
            self._check_dirty_state()

    def on_remove_whitelist(self):
        selected_items = self.whitelist_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an entry to remove.")
            return
        for item in selected_items: self.model.remove_whitelist_entry(item.text())
        self._check_dirty_state()

    def on_about(self):
        QMessageBox.about(self, "About echo_finder_TINS_Edition", "<b>echo_finder_TINS_Edition</b><p>A tool to analyze repeated phrases in text.</p><p>License: MIT</p><p>Copyright: fernicar</p><p>Repository: <a href='https://github.com/fernicar/echo_finder_TINS_Edition'>github.com/fernicar/echo_finder_TINS_Edition</a></p>")

    def _save_current_data_to_model(self):
        self.model.update_data("original_text", self.narrative_text_edit.toPlainText())
        self.model.update_data("min_phrase_words", self.min_words_spinbox.value())
        self.model.update_data("max_phrase_words", self.max_words_spinbox.value())
        self.model.update_data("strip_punctuation", self.strip_punctuation_checkbox.isChecked())

    def update_process_button_state(self):
        text = self.narrative_text_edit.toPlainText()
        word_count = len(re.findall(r'\b\w+\b', text))
        self.process_button.setEnabled(word_count >= self.min_words_spinbox.value())

def apply_app_settings(settings):
    available_styles = QStyleFactory.keys()
    saved_style = settings.value("gui/style", "Fusion")
    if saved_style in available_styles: QApplication.setStyle(saved_style)
    
    try: # QSettings can return strings for enums, robustly handle it
        theme_id_str = settings.value("gui/theme", str(Qt.ColorScheme.Unknown.value))
        theme_id = int(theme_id_str)
        QApplication.styleHints().setColorScheme(Qt.ColorScheme(theme_id))
    except (ValueError, TypeError):
        QApplication.styleHints().setColorScheme(Qt.ColorScheme.Unknown)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("fernicar")
    QCoreApplication.setApplicationName("echo_finder_TINS_Edition")
    settings = QSettings()
    apply_app_settings(settings)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())