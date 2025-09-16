# main.py
import re
import sys
import os # For checking spacy model

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

# Attempt to load SpaCy model globally or on first use
# This must be done on the main thread if not handled by a worker
nlp = None
try:
    import spacy
    # Load the English model if spacy is available. This happens on the main thread.
    # For robust production code, this could be offloaded to a worker or checked at runtime.
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Model not found/downloaded, nlp remains None. Will be handled gracefully in export.
    print("SpaCy 'en_core_web_sm' model not found. Semantic Echo export will be disabled.")
except ImportError:
    # Spacy library itself not installed, nlp remains None. Will be handled gracefully.
    print("SpaCy library not installed. Semantic Echo export will be disabled.")
except Exception as e:
    print(f"Error loading SpaCy model: {e}. Semantic Echo export will be disabled.")

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
            self.skip_overlap_checkbox.isChecked(),
            tuple(sorted(whitelist_items))
        )

    def _check_dirty_state(self):
        """Compares current state to the last clean state and updates the UI."""
        is_dirty = self._get_current_state_snapshot() != self.last_clean_state
        self.narrative_text_edit.setStyleSheet("border: 1px solid red;" if is_dirty else "")
        self.update_export_actions_state(not is_dirty and bool(self.model.data.get("echo_results")))

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
        self.skip_overlap_checkbox = QCheckBox("Skip Overlapping Echoes")
        self.strip_punctuation_checkbox = QCheckBox("Strip Punctuation")
        self.add_whitelist_button = QPushButton("Add")
        self.remove_whitelist_button = QPushButton("Remove")
        whitelist_controls_layout.addWidget(self.skip_overlap_checkbox)
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
        
        file_menu.addActions([action_new, action_open, action_save, action_save_as])
        file_menu.addSeparator()

        self.action_export_echo_list = QAction("Export &Echo List (html)", self)
        self.action_export_echo_list.triggered.connect(self.on_export_echo_list_html)
        file_menu.addAction(self.action_export_echo_list)

        self.action_export_semantic_echo = QAction("Export &Semantic Echo (html)", self)
        # Disable semantic export if spacy model is not loaded
        self.action_export_semantic_echo.setEnabled(nlp is not None) 
        # self.action_export_semantic_echo.triggered.connect(self.on_export_semantic_echo_html) # Connect when implemented
        file_menu.addAction(self.action_export_semantic_echo)
        file_menu.addSeparator()
        
        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

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
        
        self.update_export_actions_state(False) # Initial state disabled

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
        self.skip_overlap_checkbox.stateChanged.connect(self._check_dirty_state)

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
        self.skip_overlap_checkbox.setChecked(data.get("skip_overlapping_echoes", True))

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
        self.update_export_actions_state(bool(data.get("echo_results")))

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
        self.update_export_actions_state(bool(results)) # Enable/disable export actions

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
        pattern = r'\b' + r'\W*'.join(re.escape(word) for word in words) + r'\b'
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
        self.model.update_data("skip_overlapping_echoes", self.skip_overlap_checkbox.isChecked())

    def update_process_button_state(self):
        text = self.narrative_text_edit.toPlainText()
        word_count = len(re.findall(r'\b\w+\b', text))
        self.process_button.setEnabled(word_count >= self.min_words_spinbox.value())

    def update_export_actions_state(self, enable: bool):
        self.action_export_echo_list.setEnabled(enable)
        # Only enable semantic export if SpaCy is loaded AND echoes exist
        self.action_export_semantic_echo.setEnabled(enable and nlp is not None) 

    # Helper function for newline processing
    def _convert_newlines_to_html(self, text_segment: str) -> str:
        """Converts various newline patterns to HTML <br> tags."""
        text_segment = text_segment.replace('\r\n', '\n') # Normalize line endings
        text_segment = re.sub(r'\n{3,}', '<br><br><br>', text_segment) # Triple+ newlines
        text_segment = re.sub(r'\n{2}', '<br><br>', text_segment)      # Double newlines
        text_segment = re.sub(r'\n', '<br>', text_segment)             # Single newlines
        return text_segment

    def on_export_echo_list_html(self):
        if not self.model.data.get("echo_results"):
            QMessageBox.information(self, "Export HTML", "No echo results to export. Please run analysis first.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Export Echo List (HTML)", "", "HTML Files (*.html)")
        if not filepath: return
        
        original_text = self.model.data.get("original_text", "")
        echo_results = self.model.data.get("echo_results", [])

        # Prepare a list of (start, end, color) for all echo occurrences based on REGEX MATCHES
        echo_spans = []
        saturation = 75
        lightness = 15 # Darker for text on dark background
        
        def get_hsl_color(hue, sat=saturation, lit=lightness):
            return f"hsl({hue}, {sat}%, {lit}%)"

        def get_echo_occurrence_hsl_color(occurrence_index: int, total_occurrences: int, phrase_word_count: int, app_min_words_bound: int, app_max_words_bound: int):
            """
            Calculates a dynamic HSL color for an individual echo occurrence.
            Color shifts from purple (low repetition/first instance) to red (high repetition/later instance).
            The rate of shift is influenced by the phrase's word count.

            :param occurrence_index: 0-indexed position of this specific occurrence (0 for 1st, 1 for 2nd, etc.)
            :param total_occurrences: Total count of this phrase in the document.
            :param phrase_word_count: Number of words in the phrase.
            :param app_min_words_bound: The current minimum word count set in the app's spinbox.
            :param app_max_words_bound: The current maximum word count set in the app's spinbox.
            :return: An HSL color string.
            """
            if total_occurrences < 2:
                return get_hsl_color(300) # Default to purple if somehow only 1 occurrence

            # Normalize occurrence progress: 0.0 for first instance, 1.0 for last instance
            occurrence_progress = occurrence_index / (total_occurrences - 1) if total_occurrences > 1 else 0.0

            # Calculate word impact factor (0.0 for min_words_bound, 1.0 for max_words_bound)
            # This determines how "fast" the color shifts towards red.
            word_range = max(1, app_max_words_bound - app_min_words_bound) # Prevent division by zero
            word_impact_factor = (phrase_word_count - app_min_words_bound) / word_range
            word_impact_factor = max(0.0, min(1.0, word_impact_factor)) # Clamp between 0 and 1

            # Define the range of severity based on word count
            # Longer phrases shift color more aggressively (closer to red)
            COLOR_CHANGE_RATE_MIN_WORDS = 0.2  # Max severity for a 2-word phrase at its last instance
            COLOR_CHANGE_RATE_MAX_WORDS = 0.8  # Max severity for an 8-word phrase at its last instance

            base_change_rate = COLOR_CHANGE_RATE_MIN_WORDS + (
                (COLOR_CHANGE_RATE_MAX_WORDS - COLOR_CHANGE_RATE_MIN_WORDS) * word_impact_factor
            )

            final_severity = occurrence_progress * base_change_rate
            final_severity = max(0.0, min(1.0, final_severity)) # Clamp final severity

            # Map severity to hue (300 = Purple, 240 = Blue, 120 = Green, 60 = Yellow, 0 = Red)
            hue = 300 - (final_severity * 300)
            
            return get_hsl_color(hue)
        
        app_min_words_bound = self.min_words_spinbox.value()
        app_max_words_bound = self.max_words_spinbox.value()

        for echo_item in echo_results:
            normalized_phrase = echo_item['phrase']
            total_occurrences = len(echo_item['occurrences'])
            phrase_word_count = echo_item['words']
            
            # Reconstruct the regex to find the actual spans in the original text
            # This ensures punctuation is correctly handled by the regex, not explicitly removed
            words_for_regex = re.split(r'\s+', normalized_phrase)
            pattern = r'\b' + r'\W*'.join(re.escape(word) for word in words_for_regex) + r'\b'
            
            found_matches = []
            for match in re.finditer(pattern, original_text, re.IGNORECASE):
                found_matches.append((match.start(), match.end()))
            
            # Sort matches by start position to ensure correct occurrence_index
            found_matches.sort(key=lambda x: x[0])

            for occurrence_index, (start, end) in enumerate(found_matches):
                color = get_echo_occurrence_hsl_color(
                    occurrence_index=occurrence_index,
                    total_occurrences=total_occurrences,
                    phrase_word_count=phrase_word_count,
                    app_min_words_bound=app_min_words_bound,
                    app_max_words_bound=app_max_words_bound
                )
                echo_spans.append((start, end, color))

        # Sort spans by start position
        echo_spans.sort(key=lambda x: x[0])

        # Generate HTML content by processing the original text and inserting highlights
        html_parts = []
        current_idx = 0

        for echo_start, echo_end, echo_color in echo_spans:
            # Add text before this echo, converting newlines
            if echo_start > current_idx:
                segment = original_text[current_idx:echo_start]
                html_parts.append(self._convert_newlines_to_html(segment))
            
            # Add the highlighted echo itself
            highlighted_text = original_text[echo_start:echo_end]
            html_parts.append(
                f'<span class="echo-highlight" style="background-color: {echo_color};">'
                f'{highlighted_text}'
                f'</span>'
            )
            current_idx = echo_end
        
        # Add any remaining text after the last echo, converting newlines
        if current_idx < len(original_text):
            segment = original_text[current_idx:]
            html_parts.append(self._convert_newlines_to_html(segment))
        
        html_text_with_echo_highlights = ''.join(html_parts)

        # Final HTML structure based on PoC template for Echo List
        # semantic_echo_html_content will be empty for now
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>Repetition Heatmap</title>
<style>
body {{ font-family: sans-serif; background-color: #333; color: white; }}
#toggles {{ position: fixed; top: 10px; left: 25%; transform: translateX(-50%); text-align: center; }}
#toggles button {{ margin-right: 10px; padding: 5px 10px; cursor: pointer; }}
#semantic-echo-view {{ display: none; }} /* Initially hide semantic view */
.no-colors #semantic-echo-view p, .no-colors #echo-list-view span.echo-highlight {{ background-color: transparent !important; }} /* Hide colors */
.echo-highlight {{ padding: 0.1em 0.2em; border-radius: 0.2em; }} /* Consistent styling */
</style>
</head>
<body class="show-colors">

<div id="color-legend" style="margin-bottom: 20px;">
    <h3>Color Legend: Repetition Level</h3>
    <div style="display: flex; align-items: center; flex-wrap: wrap;">
        <span style="background-color: hsl(300, {saturation}%, {lightness}%); width: 30px; height: 30px; display: inline-block; margin-right: 5px; border: 1px solid #555;"></span> Purple: Very Low Repetition   
        <span style="background-color: hsl(240, {saturation}%, {lightness}%); width: 30px; height: 30px; display: inline-block; margin-right: 5px; border: 1px solid #555;"></span> Blue: Low Repetition   
        <span style="background-color: hsl(120, {saturation}%, {lightness}%); width: 30px; height: 30px; display: inline-block; margin-right: 5px; border: 1px solid #555;"></span> Green: Moderate Repetition   
        <span style="background-color: hsl(60 , {saturation}%, {lightness}%); width: 30px; height: 30px; display: inline-block; margin-right: 5px; border: 1px solid #555;"></span> Yellow: High Repetition   
        <span style="background-color: hsl(0  , {saturation}%, {lightness}%); width: 30px; height: 30px; display: inline-block; margin-right: 5px; border: 1px solid #555;"></span> Red: Very High Repetition (Review)
    </div>
</div>

<div id="toggles">
    <button id="toggle-view">Semantic Echo View</button>
    <button id="toggle-colors">Hide Colors</button>
</div>

<h2 id="semantic-echo-header" style="display: none;">Echo List and Semantic Echo Level Repetition</h2>
<div id="semantic-echo-view">
    <!-- Semantic Echo content will be generated here when feature is enabled -->
    <p style="text-align: center; color: gray;">Semantic Echo analysis is not yet implemented.</p>
</div>

<h2 id="echo-list-header">Echo List Level Repetition</h2>
<div id="echo-list-view" style="display: block;">
    {html_text_with_echo_highlights}
</div>

<script>
    const toggleViewButton = document.getElementById('toggle-view');
    const toggleColorsButton = document.getElementById('toggle-colors');
    const semanticEchoView = document.getElementById('semantic-echo-view');
    const echoListView = document.getElementById('echo-list-view');
    const semanticEchoHeader = document.getElementById('semantic-echo-header');
    const echoListHeader = document.getElementById('echo-list-header');
    let isEchoListView = true;
    let areColorsVisible = true;

    // Initial state setup
    semanticEchoView.style.display = 'none';
    semanticEchoHeader.style.display = 'none';
    echoListView.style.display = 'block';
    echoListHeader.style.display = 'block';
    toggleViewButton.textContent = 'Semantic Echo View';


    toggleViewButton.addEventListener('click', function() {{
        isEchoListView = !isEchoListView;
        if (isEchoListView) {{
            semanticEchoView.style.display = 'none';
            semanticEchoHeader.style.display = 'none';
            echoListView.style.display = 'block';
            echoListHeader.style.display = 'block';
            toggleViewButton.textContent = 'Semantic Echo View';
        }} else {{
            semanticEchoView.style.display = 'block';
            semanticEchoHeader.style.display = 'block';
            echoListView.style.display = 'none';
            echoListHeader.style.display = 'none';
            toggleViewButton.textContent = 'Echo List View';
        }}
    }});

    toggleColorsButton.addEventListener('click', function() {{
        areColorsVisible = !areColorsVisible;
        if (areColorsVisible) {{
            document.body.classList.remove('no-colors');
            toggleColorsButton.textContent = 'Hide Colors';
        }} else {{
            document.body.classList.add('no-colors');
            toggleColorsButton.textContent = 'Show Colors';
        }}
    }});
</script>

</body>
</html>"""

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.status_bar.showMessage(f"Echo List exported to {filepath}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save HTML file: {e}")
            self.status_bar.showMessage(f"Error saving HTML: {e}", 5000)

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