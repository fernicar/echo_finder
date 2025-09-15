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
        self.whitelist = whitelist
        self.strip_punctuation = strip_punctuation
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            # 1. Tokenization
            self.signals.progress.emit("Step 1/4: Tokenizing text...")
            
            # Build a regex that prioritizes whitelisted words
            # This ensures "Dr." is matched before a general word match might just find "Dr"
            escaped_whitelist = [re.escape(w) for w in self.whitelist]
            # Sort by length descending to match longer entries first (e.g., "i.e." before "i.")
            escaped_whitelist.sort(key=len, reverse=True)
            
            # The general pattern for words
            general_word_pattern = r'\b[a-zA-Z0-9\'’`]+\b'
            
            # Combine them, prioritizing the whitelist
            # The whitelist part captures case-sensitively
            # The general part captures case-insensitively via re.IGNORECASE flag
            patterns = escaped_whitelist + [general_word_pattern]
            combined_pattern = re.compile("|".join(patterns))

            tokens = []
            max_words_in_sentence = 0
            current_sentence_word_count = 0

            if self.strip_punctuation:
                for match in combined_pattern.finditer(self.text):
                    word = match.group(0)
                    start, end = match.span()
                    
                    # Only lowercase if it's NOT in the whitelist
                    token_word = word if word in self.whitelist else word.lower()
                    tokens.append({'word': token_word, 'start': start, 'end': end})
            else: # Literal tokenization
                for match in re.finditer(r'\S+', self.text):
                    word = match.group(0)
                    start, end = match.span()
                    tokens.append({'word': word, 'start': start, 'end': end})

            # Calculate max words for the UI spinbox
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
                    phrase_text = " ".join(t['word'] for t in phrase_tokens)
                    
                    # The occurrence tracks the start of the first word and end of the last word
                    occurrence = {'start': phrase_tokens[0]['start'], 'end': phrase_tokens[-1]['end']}
                    
                    if phrase_text not in phrase_occurrences:
                        phrase_occurrences[phrase_text] = []
                    phrase_occurrences[phrase_text].append(occurrence)

            # 3. Frequency Filtering
            self.signals.progress.emit("Step 3/4: Filtering frequent phrases...")
            repeated_phrases = {
                phrase: occurrences
                for phrase, occurrences in phrase_occurrences.items()
                if len(occurrences) >= 2
            }

            # 4. Maximal Match Filtering
            self.signals.progress.emit("Step 4/4: Finding maximal echoes...")
            # Sort by word count descending, so we process longer phrases first
            sorted_phrases = sorted(repeated_phrases.keys(), key=lambda p: len(p.split()), reverse=True)
            
            maximal_echoes = {}
            for phrase in sorted_phrases:
                # Check if this phrase is a substring of an already-accepted longer phrase
                is_subphrase = False
                for existing_max_phrase in maximal_echoes:
                    if phrase in existing_max_phrase:
                        is_subphrase = True
                        break
                if not is_subphrase:
                    maximal_echoes[phrase] = repeated_phrases[phrase]

            # Build final result list
            results = []
            for phrase, occurrences in maximal_echoes.items():
                first_occurrence = occurrences[0]
                representative_original = self.text[first_occurrence['start']:first_occurrence['end']]
                results.append({
                    'phrase': phrase,
                    'representative_original': representative_original,
                    'count': len(occurrences),
                    'words': len(phrase.split()),
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

    def new_project(self, preferred_preset="longest_first_by_word_count"):
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
        preset = self.data.get("last_used_sort_preset", "longest_first_by_word_count")
        if preset == "longest_first_by_word_count":
            self.data["echo_results"].sort(key=lambda x: (-x['words'], -x['count'], x['phrase']))
        elif preset == "most_repeated_short_to_long":
            self.data["echo_results"].sort(key=lambda x: (-x['count'], x['words'], x['phrase']))
        
        self.echo_results_updated.emit(self.data["echo_results"])

    def update_data(self, key, value):
        self.data[key] = value

    def add_whitelist_entry(self, entry):
        if "custom_whitelist" not in self.data:
            self.data["custom_whitelist"] = []
        if entry not in self.data["custom_whitelist"]:
            self.data["custom_whitelist"].append(entry)
            self.whitelist_updated.emit(self.data["custom_whitelist"])
    
    def remove_whitelist_entry(self, entry):
        if "custom_whitelist" in self.data and entry in self.data["custom_whitelist"]:
            self.data["custom_whitelist"].remove(entry)
            self.whitelist_updated.emit(self.data["custom_whitelist"])