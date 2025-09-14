## Description
`echo_finder_TINS_Edition` is a minimalist desktop application designed to identify and highlight redundant or excessively repeated phrases ("echoes") within narrative text. It helps users refine their writing by pinpointing repetitive phrasing, focusing on the "longest possible repeating sequences" to provide actionable insights for intervention. The application prioritizes clear identification over real-time editing, allowing users to analyze text and then make informed decisions to improve narrative flow.

## Functionality

### Core Features
-   **Text Input:** Load text from a project file or paste/type directly into a dedicated text area.
-   **Echo Detection:** Process the narrative text to find repeating sequences of words (phrases).
-   **Dynamic Phrase Lengths:** Analyze phrases with a minimum length of 2 words, up to a dynamically determined maximum length based on the input text.
-   **"Maximal Match" (Greedy) Logic:** Prioritize and report only the longest possible repeating phrases, automatically filtering out shorter, overlapping repetitions that are fully contained within a reported longer echo.
-   **Custom Whitelist:** Allow users to define a project-specific whitelist of abbreviations (e.g., "Dr.", "Mr.") whose internal punctuation should be preserved during text preprocessing.
-   **Echo Results Display:** Present detected echoes in a sortable list, showing the phrase, its count, and its word length.
-   **Sorting Presets:** Offer two predefined sorting methods for the echo results: "Most Repeated (Short to Long)" and "Longest First (by Word Count)".
-   **Project Management:** Create new projects, load existing `.json` project files, and save the current text, configurations, whitelist, and echo results to `.json` files.
-   **UI Feedback:** Provide clear visual indicators for dirty text (needs re-processing) and status messages.

### User Interface (PySide6 - Fusion Style, Auto Color Scheme)

The main application window will be a PySide6 desktop application using the 'Fusion' style and 'Auto' color scheme. It will feature a central layout divided into four main sections by `QSplitter` widgets, allowing dynamic resizing.

```mermaid
graph TD
    A[Main Window (echo_finder_TINS_Edition)] --> B[Menu Bar]
    A --> C["Splitter 1 (Vertical)"]
    C --> D["Narrative Text Area (QTextEdit)"]
    C --> E["Splitter 2 (Vertical)"]
    E --> F["Echo Results List (QTableWidget)"]
    E --> G["Splitter 3 (Vertical)"]
    G --> H["Whitelist Area (QListWidget)"]
    G --> I["Status Bar (QStatusBar)"]
    A --> J["Toolbar (QToolBar)"]
```

#### Menu Bar
-   **File:**
    -   `New (Ctrl+N)`: Clears UI, resets configuration to defaults, initializes a new empty project.
    -   `Open (Ctrl+O)`: Opens a `QFileDialog` to select a `.json` project file.
    -   `Save (Ctrl+S)`: Saves current project state. If `unnamed`, prompts for "Save As".
    -   `Save As (Ctrl+Shift+S)`: Opens `QFileDialog` to save project to a new `.json` file.
    -   `Exit (Ctrl+Q)`: Closes the application.
-   **Edit:**
    -   `Paste from Clipboard (Ctrl+V)`: Pastes system clipboard content into `Narrative Text Area`.
-   **Help:**
    -   `About`: Displays a `QMessageBox` with "echo_finder_TINS_Edition", "License: MIT", "Copyright: fernicar", "Repository: [link to fernicar/echo_finder_TINS_Edition]".

#### Narrative Text Area (`QTextEdit`)
-   A large, multi-line `QTextEdit` widget for displaying and editing the narrative text.
-   It will be read-write, allowing direct input.
-   **Dirty Indicator:** Displays a visual cue (e.g., a red border or text label) when the text content (or `min/max_length`, or whitelist) changes, indicating the need for re-processing. This indicator clears after `Find Them` is successfully executed.
-   *Highlighting feature is planned for a future iteration.*

#### Echo Results List (`QTableWidget`)
-   Displays processed echo phrases.
-   Columns: `Phrase` (string), `Count` (integer), `Length` (integer - number of words).
-   Populated and updated after text processing or sorting.

#### Whitelist Area (`QListWidget` with Controls)
-   `QListWidget` displaying current project's custom abbreviations.
-   Accompanying buttons for `Add`, `Edit`, `Remove` whitelist entries.
    -   `Add`: Uses a `QInputDialog` to get new abbreviation.
    -   `Edit`: Allows inline editing or uses `QInputDialog` to modify selected entry.
    -   `Remove`: Deletes selected entry.

#### Status Bar (`QStatusBar`)
-   Displays real-time messages: "Ready", "Processing...", "Project saved: [filename]", "No echoes found for current parameters", "Error: [message]".
-   Provides feedback on file operations and processing status.

#### Toolbar (`QToolBar`)
-   **Controls:**
    -   `Min Length:` (`QLabel` displaying "2" - read-only).
    -   `Max Length:` (`QSpinBox`, default 8). Its `maximum` property is dynamically set by `model.py` based on the longest possible phrase in the current text (after preprocessing). If the current value exceeds the new maximum, it clamps to the new maximum.
    -   `Find Them / Find Again` (`QPushButton`): Triggers text processing in `model.py`.
    -   `Separator`
    -   `Preset:` (`QComboBox`):
        -   Option 1: "Most Repeated (Short to Long)"
        -   Option 2: "Longest First (by Word Count)"

### Behavior Specifications (UI to Model Interaction)

-   **Processing Trigger:** The `Find Them / Find Again` button explicitly calls `model.py`'s `process_text()` method.
-   **Dirty State:** Any change in `Narrative Text Area` text, `max_phrase_length` `QSpinBox` value, or `Whitelist Area` content will set the UI's dirty indicator.
-   **Model-to-UI Updates:** `model.py` uses PySide6 signals (e.g., `echo_results_updated`, `status_message`, `project_loaded`, `whitelist_updated`) to inform `main.py` of processing completion, status changes, and data updates. `main.py` connects its slots to these signals to refresh the UI.
-   **Project Loading:** `model.py` emits a `project_loaded` signal, which `main.py` uses to populate all UI elements (text area, spin boxes, whitelist, results table, preset dropdown) with the loaded data.
-   **Sorting Interaction:** Selecting a `Preset` from the `QComboBox` calls `model.py`'s `sort_results()` method. `model.py` then emits `echo_results_updated` with the newly sorted list, which `main.py` uses to refresh the `QTableWidget`. This does not trigger a full text re-processing.

## Technical Implementation

### Architecture
The application will adhere to a clear separation of concerns:
-   **`model.py`**: Encapsulates all application logic, data handling, text processing, echo detection, project management, and sorting. It will be a `QObject` to emit signals.
-   **`main.py`**: Manages the graphical user interface, user interactions, and acts as the view/controller. It listens to `model.py`'s signals and calls its methods in response to UI events.
-   **Threading**: Long-running operations within `model.py` (specifically `process_text()`) must be executed in a separate `QThread` to prevent the `main.py` GUI from freezing, ensuring responsiveness and allowing status updates.

### Data Model

#### Project Structure (JSON file, e.g., `my_project.json`)
```json
{
  "project_name": "My Narrative Analysis",
  "original_text": "The turtle started running and then it crouch... The turtle started running and then it smiled...",
  "min_phrase_length": 2,
  "max_phrase_length": 8,
  "custom_whitelist": ["Dr.", "Mr.", "Mrs.", "St.", "e.g.", "i.e."],
  "last_used_sort_preset": "most_repeated_short_to_long",
  "echo_results": []
}
```

#### Echo Phrase Object Structure (within `echo_results` list)
```json
{
  "phrase": "the turtle started running and then it smiled", // The normalized echo phrase (lowercase, punctuation stripped)
  "count": 2,                                               // Number of occurrences
  "length": 8,                                              // Number of words in the phrase
  "occurrences": [                                          // List of original occurrences for highlighting (character indices)
    {"start": 0, "end": 45},
    {"start": 50, "end": 95}
  ]
}
```

### Algorithms (in `model.py`)

1.  **Text Preprocessing:**
    *   Convert input `original_text` to lowercase.
    *   Tokenize the text into a list of words.
    *   **Punctuation Stripping with Whitelist:** Iterate through words. For each word, remove common punctuation (`,`, `.`, `?`, `!`, `;`, `:`, `(`, `)`, etc.) unless the word (or a significant part of it) matches an entry in the `custom_whitelist` (e.g., "Dr." should remain "Dr."). During this, meticulously track the original `start` and `end` character indices for each processed word token relative to the `original_text`.
    *   **Maximal Phrase Length Calculation:** After preprocessing, determine the maximum number of words in any contiguous sequence that can form a phrase, to set the dynamic `max_phrase_length` for the UI's `QSpinBox`.

2.  **N-gram Generation & Frequency Counting:**
    *   Using the preprocessed word tokens and their original index mappings, generate all possible contiguous phrases (n-grams) from `min_phrase_length` (fixed at 2) up to the user-selected `max_phrase_length`.
    *   For each generated n-gram:
        *   Store it in a hash map (Python dictionary) where the key is the phrase string and the value is an object containing `count`, `length`, and a list of `occurrences` (e.g., `{"start": ..., "end": ...}` character index tuples from the *original* text).
        *   Increment `count` if the phrase already exists. Add new phrase if not.

3.  **"Maximal Match" (Greedy) Filtering:**
    *   After generating all n-grams and their counts, iterate through the detected echoes (`count >= 2`).
    *   Implement logic to ensure that if a longer phrase `P_long` is an echo, and a shorter phrase `P_short` is also an echo, where `P_short` is a direct substring of `P_long` AND `P_short`'s occurrences are entirely contained within (or identical to the start/end bounds of) `P_long`'s occurrences, then only `P_long` should be included in the final `echo_results`. This ensures that only the most extensive, non-redundant repeating sequences are reported.

4.  **Sorting Algorithms:**
    *   **Preset 1: "Most Repeated (Short to Long)"**: Sort `echo_results` primarily by `count` (descending), then by `length` (ascending), then alphabetically by `phrase`.
    *   **Preset 2: "Longest First (by Word Count)"**: Sort `echo_results` primarily by `length` (descending), then by `count` (ascending), then alphabetically by `phrase`.

### Dependencies
-   **PySide6** (version >= 6.9.1)
-   Standard Python libraries (e.g., `json`, `re` for regex in preprocessing if needed).
-   No other third-party libraries or external APIs are required for the application's runtime.

## Input/Output

### Input Specifications
-   **Text Input:** Raw text (string) via `QTextEdit` or loaded from a `.json` file.
-   **`max_phrase_length`:** Integer (2 to dynamic max, default 8).
-   **`custom_whitelist` entries:** List of strings.
-   **Sorting Preset Selection:** String ("most_repeated_short_to_long", "longest_first_by_word_count").
-   **Project File Path:** String (path to `.json` file).

### Output Specifications
-   **`echo_results` Display:** `QTableWidget` rows: `Phrase` (string), `Count` (integer), `Length` (integer).
-   **Status Messages:** `QStatusBar` (string messages).
-   **Project Files:** `.json` files containing the specified project data structure.
-   **Whitelist Display:** `QListWidget` displaying current `custom_whitelist` entries.

## Error Handling and Validation

-   **File Errors:** `model.py` will catch file I/O errors (e.g., `FileNotFoundError`, `PermissionError`, `json.JSONDecodeError`) during load/save operations and emit `status_message` signals. `main.py` will display these in the `QStatusBar` and potentially as `QMessageBox.warning` for critical failures.
-   **Empty Narrative Text:** The `Find Them / Find Again` button will be disabled if the `Narrative Text Area` is empty or if the preprocessed text contains fewer than 2 words.
-   **Empty Whitelist Entry:** Adding an empty or whitespace-only string to the `custom_whitelist` will be prevented, with a `QMessageBox.warning` shown to the user.
-   **No Echoes Found:** If `process_text` returns an empty `echo_results` list, the `QStatusBar` will display "No echoes found for current parameters."
-   **`max_phrase_length` Validation:** The `QSpinBox` will dynamically adjust its maximum value and clamp its current value if it exceeds the new maximum, preventing invalid ranges.
-   **UI Feedback:** All user actions and model responses will trigger appropriate status bar messages or visual indicators (like the "red line").

## Technical Constraints & Notes

-   **Text Volume:** The application should handle text up to the approximate length of 6 typical book chapters efficiently.
-   **Responsiveness:** While processing can take time for large texts, the UI must remain responsive. Heavy computational tasks in `model.py` (especially `process_text`) must run in a separate thread.
-   **Memory:** Standard Python data structures are acceptable; no extreme memory optimizations are necessary given typical text sizes (up to 6 chapters) and a system with 16GB RAM.
-   **Platform:** The primary target platform is Windows 10.
-   **Python-only:** No external APIs or AI/LLM models should be used *within the generated application's runtime*. The LLM will use its capabilities *to generate* the code.

## Acceptance Criteria

The generated `echo_finder_TINS_Edition` application will be verified against the following test cases:

1.  **Core Echo Detection & Maximal Match (Greedy) Logic:**
    *   **Test Case 1 (User Provided - Maximal Match):**
        *   **Input Text:** "The turtle started running and then it smiled and then the turtle started running and then it smiled, while at the same the turtle started running and then it crouched down."
        *   **Expected `echo_results` (after `process_text`, default `min_len=2`, dynamic `max_len`, default whitelist `["Dr.", "Mr.", "Mrs.", "St.", "e.g.", "i.e."]`):**
            ```json
            [
              {
                "phrase": "the turtle started running and then it smiled",
                "count": 2,
                "length": 8,
                "occurrences": [
                  {"start": 0, "end": 45}, // LLM to calculate precise indices
                  {"start": 50, "end": 95}
                ]
              }
            ]
            ```
        *   **Verification:** The `Echo Results List` in the GUI must display exactly one entry: "the turtle started running and then it smiled", with a count of 2 and length 8. No shorter, overlapping echoes (e.g., "the turtle started running and then it") should be reported.
    *   **Test Case 2 (No Echoes):**
        *   **Input Text:** "This is a unique sentence. It has no repetitions at all."
        *   **Expected `echo_results`:** An empty list.
        *   **Verification:** The `Echo Results List` is empty, and the `QStatusBar` displays "No echoes found for current parameters."
    *   **Test Case 3 (Punctuation and Whitelist):**
        *   **Input Text:** "Dr. Smith said, 'Hello Mr. Jones.' Then Dr. Smith asked, 'Is Mr. Jones here?'"
        *   **Custom Whitelist:** Add `["Dr.", "Mr."]` via the UI.
        *   **Verification:** After processing, confirm that `Dr.` and `Mr.` are preserved and `Dr. Smith` and `Mr. Jones` (or similar normalized forms depending on trailing punctuation) are correctly identified as repeating phrases if their counts are >= 2. For instance, "dr. smith" should be treated as a single token for phrase formation and matching.

2.  **Configuration Handling:**
    *   **Dynamic `max_phrase_length`:** When new text is loaded/pasted, the `max_phrase_length` `QSpinBox`'s `maximum` value updates correctly to the longest possible word sequence in the text.
    *   **Processing with New Config:** Changing the `max_phrase_length` and clicking `Find Them / Find Again` correctly re-processes the text and updates results.
    *   **Whitelist Management:** Adding/removing whitelist entries updates the `QListWidget`, changes the "dirty" state, and affects subsequent processing correctly.

3.  **Project Persistence:**
    *   Saving a project to a `.json` file and then re-loading it restores all UI states (`Narrative Text Area` content, `max_phrase_length`, `custom_whitelist`, `echo_results`, `last_used_sort_preset`) precisely.

4.  **User Interface Responsiveness & Feedback:**
    *   The `Find Them / Find Again` button is disabled when the `Narrative Text Area` is empty or has insufficient words for processing.
    *   The "red line" dirty indicator appears/disappears as specified.
    *   `QStatusBar` messages accurately reflect application status (e.g., "Processing...", "Project saved", "No echoes found.").

5.  **Sorting Presets:**
    *   With `echo_results` present, switching between "Most Repeated (Short to Long)" and "Longest First (by Word Count)" in the `Preset` dropdown re-sorts the `QTableWidget` display immediately without re-processing.

6.  **Threading:**
    *   During `process_text` execution, the UI remains responsive, and the `QStatusBar` can update with "Processing...".