# model.py
import re
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = Signal()
    error = Signal(tuple)
    result = Signal(list)
    progress = Signal(str)
    max_words_available = Signal(int)

class EchoFinderWorker(QRunnable):
    """Worker thread for finding echoes in text."""
    def __init__(self, text, min_words, max_words, whitelist, strip_punctuation):
        super().__init__()
        self.text = text
        self.min_words = min_words
        self.max_words = max_words
        # Create a lowercase set for fast, case-insensitive lookups
        self.whitelist_lower = {w.lower() for w in whitelist}
        self.whitelist_original = whitelist # Keep original for regex
        self.strip_punctuation = strip_punctuation
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            # 1. Tokenization
            self.signals.progress.emit("Step 1/4: Tokenizing text...")
            
            escaped_whitelist = [re.escape(w) for w in self.whitelist_original]
            escaped_whitelist.sort(key=len, reverse=True)
            general_word_pattern = r'\b[a-zA-Z0-9\'’`]+\b'
            
            # This pattern finds any sequence of non-whitespace, which is a good
            # base for both stripping and non-stripping modes.
            token_pattern = r'\S+'
            
            tokens = []
            
            for match in re.finditer(token_pattern, self.text):
                original_word = match.group(0)
                start, end = match.span()
                
                # --- Normalization Logic ---
                normalized_word = original_word.lower()
                is_whitelisted = normalized_word in self.whitelist_lower

                if not is_whitelisted:
                    if self.strip_punctuation:
                        # Aggressively strip leading/trailing punctuation for non-whitelisted words
                        normalized_word = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', normalized_word)
                    # If not stripping, the normalized_word remains as is (e.g., "hello,")
                
                # We only care about tokens that result in a non-empty normalized word
                if normalized_word:
                    tokens.append({'normalized': normalized_word, 'start': start, 'end': end})

            if tokens:
                text_word_count = len(re.findall(r'\b\w+\b', self.text))
                self.signals.max_words_available.emit(text_word_count)

            # 2. N-gram Generation
            self.signals.progress.emit("Step 2/4: Generating phrases...")
            phrase_occurrences = {}
            for n in range(self.min_words, self.max_words + 1):
                if n > len(tokens): break
                for i in range(len(tokens) - n + 1):
                    phrase_tokens = tokens[i : i + n]
                    # The phrase key is ALWAYS built from normalized words
                    phrase_key = " ".join(t['normalized'] for t in phrase_tokens)
                    
                    occurrence = {'start': phrase_tokens[0]['start'], 'end': phrase_tokens[-1]['end']}
                    
                    if phrase_key not in phrase_occurrences:
                        phrase_occurrences[phrase_key] = []
                    phrase_occurrences[phrase_key].append(occurrence)

            # 3. Frequency Filtering
            self.signals.progress.emit("Step 3/4: Filtering frequent phrases...")
            repeated_phrases = {
                phrase: occurrences
                for phrase, occurrences in phrase_occurrences.items()
                if len(occurrences) >= 2
            }

            # 4. Maximal Match Filtering
            self.signals.progress.emit("Step 4/4: Finding maximal echoes...")
            sorted_phrases = sorted(repeated_phrases.keys(), key=lambda p: len(p.split()), reverse=True)
            
            maximal_echoes = {}
            for phrase in sorted_phrases:
                is_subphrase = False
                for existing_max_phrase in maximal_echoes:
                    if phrase in existing_max_phrase:
                        is_subphrase = True
                        break
                if not is_subphrase:
                    maximal_echoes[phrase] = repeated_phrases[phrase]

            # Build final result list with the verbatim representative phrase
            results = []
            for phrase_key, occurrences in maximal_echoes.items():
                first_occurrence = occurrences[0]
                # THIS IS THE CRITICAL FIX: Always slice the original text for display
                representative_original = self.text[first_occurrence['start']:first_occurrence['end']]
                results.append({
                    'phrase': phrase_key, # The normalized key for logic
                    'representative_original': representative_original, # The verbatim for display/search
                    'count': len(occurrences),
                    'words': len(phrase_key.split()),
                    'occurrences': occurrences,
                })

            self.signals.result.emit(results)
        except Exception as e:
            self.signals.error.emit((e, "Error during text processing."))
        finally:
            self.signals.finished.emit()

class ProjectModel(QObject):
    """Manages the application's data and business logic."""
    project_loaded = Signal(dict)
    status_message = Signal(str, int)
    echo_results_updated = Signal(list)
    whitelist_updated = Signal(list)
    max_words_available = Signal(int)

    def __init__(self):
        super().__init__()
        self.data = {}
        self.current_project_path = None
        self.threadpool = QThreadPool()
        self.status_message.emit("Ready. Create a new project or open an existing one.", 0)

    def new_project(self, preferred_preset="by_word_count"):
        self.current_project_path = None
        self.data = {
            "project_name": "Unnamed Project",
            "original_text": "",
            "min_phrase_words": 2,
            "max_phrase_words": 8,
            "strip_punctuation": True,
            "custom_whitelist": ["Dr.", "Mr.", "Mrs.", "St.", "e.g.", "i.e."],
            "last_used_sort_preset": preferred_preset,
            "echo_results": []
        }
        self.project_loaded.emit(self.data)
        self.status_message.emit("New project created. Paste text to begin.", 4000)
    
    def load_project(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import json
                self.data = json.load(f)
                self.current_project_path = filepath
                self.project_loaded.emit(self.data)
                self.status_message.emit(f"Project '{self.data.get('project_name', 'Unnamed')}' loaded.", 4000)
        except Exception as e:
            self.status_message.emit(f"Error loading project: {e}", 5000)

    def save_project(self, filepath):
        try:
            self.data['project_name'] = self._extract_project_name(filepath)
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(self.data, f, indent=2)
                self.current_project_path = filepath
                self.status_message.emit(f"Project saved to {filepath}", 4000)
        except Exception as e:
            self.status_message.emit(f"Error saving project: {e}", 5000)

    def _extract_project_name(self, filepath):
        from pathlib import Path
        return Path(filepath).stem

    def process_text(self):
        worker = EchoFinderWorker(
            text=self.data.get("original_text", ""),
            min_words=self.data.get("min_phrase_words", 2),
            max_words=self.data.get("max_phrase_words", 8),
            whitelist=self.data.get("custom_whitelist", []),
            strip_punctuation=self.data.get("strip_punctuation", True)
        )
        worker.signals.result.connect(self._on_processing_result)
        worker.signals.progress.connect(lambda msg: self.status_message.emit(msg, 0))
        worker.signals.finished.connect(lambda: self.status_message.emit("Processing complete.", 4000))
        worker.signals.error.connect(lambda err: self.status_message.emit(f"Error: {err[1]}", 5000))
        worker.signals.max_words_available.connect(self.max_words_available)
        self.threadpool.start(worker)

    def _on_processing_result(self, results):
        self.data["echo_results"] = results
        self.sort_results() # Apply current sort order to new results

    def sort_results(self):
        preset = self.data.get("last_used_sort_preset", "by_word_count")
        if preset == "by_word_count":
            # Sort by words (desc), then count (desc), then phrase (asc)
            self.data["echo_results"].sort(key=lambda x: (-x['words'], -x['count'], x['phrase']))
        elif preset == "by_repetition_count":
            # Sort by count (desc), then words (desc), then phrase (asc)
            self.data["echo_results"].sort(key=lambda x: (-x['count'], -x['words'], x['phrase']))
        
        self.echo_results_updated.emit(self.data["echo_results"])

    def update_data(self, key, value):
        self.data[key] = value

    def add_whitelist_entry(self, entry):
        if "custom_whitelist" not in self.data:
            self.data["custom_whitelist"] = []
        # Case-insensitive check before adding
        if not any(entry.lower() == item.lower() for item in self.data["custom_whitelist"]):
            self.data["custom_whitelist"].append(entry)
            self.whitelist_updated.emit(self.data["custom_whitelist"])
    
    def remove_whitelist_entry(self, entry):
        # Case-insensitive removal
        entry_lower = entry.lower()
        if "custom_whitelist" in self.data:
            self.data["custom_whitelist"] = [item for item in self.data["custom_whitelist"] if item.lower() != entry_lower]
            self.whitelist_updated.emit(self.data["custom_whitelist"])