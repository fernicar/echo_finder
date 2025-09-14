# model.py
import json
import re
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(list)
    status = Signal(str)
    max_words_available = Signal(int)


class EchoFinderWorker(QRunnable):
    """
    Worker thread for finding echoes. Inherits from QRunnable to handle
    worker thread setup, signals, and wrap the heavy processing.
    """
    def __init__(self, text, min_words, max_words, whitelist):
        super().__init__()
        self.signals = WorkerSignals()
        self.text = text
        self.min_words = min_words
        self.max_words = max_words
        self.whitelist = set(item.lower() for item in whitelist)

    @Slot()
    def run(self):
        try:
            self.signals.status.emit("Processing: Normalizing text...")
            
            processed_tokens = self._preprocess_text()

            if not processed_tokens:
                self.signals.result.emit([])
                self.signals.status.emit("No processable words found in text.")
                return

            max_available_words = len(processed_tokens)
            self.signals.max_words_available.emit(max_available_words)
            
            if len(processed_tokens) < self.min_words:
                self.signals.result.emit([])
                self.signals.status.emit("Not enough words to find echoes.")
                return

            self.signals.status.emit(f"Processing: Finding phrases ({self.min_words}-{self.max_words} words)...")
            
            phrase_occurrences = defaultdict(list)
            for n in range(self.min_words, min(self.max_words, max_available_words) + 1):
                for i in range(len(processed_tokens) - n + 1):
                    phrase_tokens = processed_tokens[i : i + n]
                    phrase_str = " ".join(token['word'] for token in phrase_tokens)
                    
                    start_char = phrase_tokens[0]['start']
                    end_char = phrase_tokens[-1]['end']
                    
                    phrase_occurrences[phrase_str].append({'start': start_char, 'end': end_char})

            echoes = {
                phrase: occurrences
                for phrase, occurrences in phrase_occurrences.items()
                if len(occurrences) >= 2
            }

            self.signals.status.emit("Processing: Filtering for maximal matches...")
            
            # Sort echoes by word count (desc) to prioritize longer matches
            # CORRECTED: Was sorting by character length, now correctly sorts by word count.
            sorted_echo_phrases = sorted(echoes.keys(), key=lambda p: len(p.split()), reverse=True)
            
            maximal_echoes = {}
            for phrase in sorted_echo_phrases:
                is_substring = False
                for longer_phrase in maximal_echoes:
                    if phrase in longer_phrase:
                        is_substring = True
                        break
                
                if not is_substring:
                    maximal_echoes[phrase] = echoes[phrase]
            
            results = []
            for phrase, occurrences in maximal_echoes.items():
                results.append({
                    "phrase": phrase,
                    "count": len(occurrences),
                    "words": len(phrase.split()),
                    "occurrences": occurrences,
                })

            self.signals.result.emit(results)
            self.signals.status.emit(f"Processing complete. Found {len(results)} maximal echoes.")

        except Exception as e:
            self.signals.error.emit((type(e), e, str(e)))
        finally:
            self.signals.finished.emit()

    def _preprocess_text(self):
        tokens = []
        whitelist_pattern = "|".join(re.escape(item) for item in self.whitelist)
        word_pattern = r'\b(?:' + whitelist_pattern + r'|[a-zA-Z0-9\'-]+)\b' if self.whitelist else r'\b[a-zA-Z0-9\'-]+\b'

        for match in re.finditer(word_pattern, self.text, re.IGNORECASE):
            word = match.group(0).lower()
            if match.group(0) in self.whitelist:
                 word = match.group(0)

            tokens.append({
                'word': word,
                'start': match.start(),
                'end': match.end()
            })
        return tokens


class ProjectModel(QObject):
    """Manages the application's data and business logic."""
    project_loaded = Signal(dict)
    status_message = Signal(str)
    echo_results_updated = Signal(list)
    whitelist_updated = Signal(list)
    max_words_available = Signal(int)

    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        self.current_project_path = None
        self.data = {}
        self.new_project()

    def new_project(self):
        self.current_project_path = None
        self.data = {
            "project_name": "Unnamed Project",
            "original_text": "",
            "min_phrase_words": 2,
            "max_phrase_words": 8,
            "custom_whitelist": ["Dr.", "Mr.", "Mrs.", "St.", "e.g.", "i.e."],
            "last_used_sort_preset": "most_repeated_short_to_long",
            "echo_results": []
        }
        self.project_loaded.emit(self.data)
        self.status_message.emit("New project created. Paste text to begin.")

    @Slot(str)
    def load_project(self, filepath: str):
        try:
            path = Path(filepath)
            with path.open('r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.current_project_path = path
            self.project_loaded.emit(self.data)
            self.status_message.emit(f"Project loaded: {path.name}")
        except Exception as e:
            self.status_message.emit(f"Error loading project: {e}")

    @Slot(str)
    def save_project(self, filepath: str):
        try:
            path = Path(filepath)
            with path.open('w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            self.current_project_path = path
            self.data['project_name'] = path.stem
            self.status_message.emit(f"Project saved: {path.name}")
        except Exception as e:
            self.status_message.emit(f"Error saving project: {e}")
            
    def update_data(self, key, value):
        self.data[key] = value

    @Slot()
    def process_text(self):
        text = self.data.get("original_text", "")
        min_words = self.data.get("min_phrase_words", 2)
        max_words = self.data.get("max_phrase_words", 8)
        whitelist = self.data.get("custom_whitelist", [])
        
        worker = EchoFinderWorker(text, min_words, max_words, whitelist)
        worker.signals.result.connect(self._on_processing_result)
        worker.signals.status.connect(self.status_message)
        worker.signals.max_words_available.connect(self.max_words_available)
        worker.signals.error.connect(lambda e: self.status_message.emit(f"Processing Error: {e[2]}"))
        
        self.threadpool.start(worker)

    @Slot(list)
    def _on_processing_result(self, results):
        self.data["echo_results"] = results
        self.sort_results()

    @Slot()
    def sort_results(self):
        preset = self.data.get("last_used_sort_preset", "most_repeated_short_to_long")
        results = self.data.get("echo_results", [])
        
        if preset == "most_repeated_short_to_long":
            results.sort(key=lambda x: (-x['count'], x['words'], x['phrase']))
        elif preset == "longest_first_by_word_count":
            results.sort(key=lambda x: (-x['words'], x['count'], x['phrase']))
            
        self.echo_results_updated.emit(results)
    
    @Slot(str)
    def add_whitelist_entry(self, entry):
        if entry and entry not in self.data["custom_whitelist"]:
            self.data["custom_whitelist"].append(entry)
            self.data["custom_whitelist"].sort()
            self.whitelist_updated.emit(self.data["custom_whitelist"])

    @Slot(str)
    def remove_whitelist_entry(self, entry):
        if entry in self.data["custom_whitelist"]:
            self.data["custom_whitelist"].remove(entry)
            self.whitelist_updated.emit(self.data["custom_whitelist"])