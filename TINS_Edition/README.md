# echo_finder_TINS_Edition

## Description
`echo_finder_TINS_Edition` is a sophisticated desktop application designed to identify and highlight redundant or excessively repeated phrases ("echoes") within narrative text. It helps users refine their writing by pinpointing repetitive phrasing, focusing on the "longest possible repeating sequences" to provide actionable insights. The application features a live, interactive highlighting system that updates in real-time as the user edits, providing an intuitive and powerful curation experience. It also includes persistent user preferences for UI theme, appearance, and sorting, ensuring a personalized workflow.

## Functionality

### Core Features
-   **Text Input:** Load text from a project file or paste/type directly into a dedicated text area.
-   **Echo Detection:** Process the narrative text to find repeating sequences of words (phrases).
-   **Configurable Word Count:** Analyze phrases with a user-configurable minimum and maximum number of words. The maximum is dynamically limited by the longest available phrase in the text.
-   **"Maximal Match" (Greedy) Logic:** Prioritize and report only the longest possible repeating phrases, automatically filtering out shorter, overlapping repetitions that are fully contained within a reported longer echo.
-   **Live Interactive Highlighting:** Select a phrase from the results list or type into a dedicated toolbar field to see all occurrences instantly highlighted. The highlights and result counts update in real-time as the main text is edited.
-   **Persistent UI Customization:** Choose between Light, Dark, or Auto (system) themes, and select from available UI styles (e.g., Fusion, Windows). Preferences are saved and automatically applied on next launch.
-   **Persistent Sorting Presets:** Offer two predefined sorting methods: "Longest First (by Word Count)" and "Most Repeated (Short to Long)". The application defaults to "Longest First" and remembers the user's last choice across sessions.
-   **Custom Whitelist:** Define a project-specific whitelist of abbreviations (e.g., "Dr.", "Mr.") whose internal punctuation should be preserved during text preprocessing.
-   **Seamless Clipboard Integration:** An "Auto Copy" feature, enabled by default, instantly copies any selected phrase from the results list to the system clipboard for use in external editors.
-   **Project Management:** Create, load, and save projects as `.json` files, preserving the text, configurations, whitelist, and analysis results.
-   **Robust UI Feedback:** Provide clear visual indicators for a "dirty" state (when inputs no longer match the last analysis) and detailed status messages.

### User Interface (PySide6)

The main application window is a PySide6 desktop application that respects persistent user settings for style and theme. It features a central layout divided into four main sections by `QSplitter` widgets, allowing dynamic resizing.

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
    -   `New (Ctrl+N)`: Initializes a new empty project.
    -   `Open (Ctrl+O)`: Opens a `QFileDialog` to select a `.json` project file.
    -   `Save (Ctrl+S)`: Saves current project state.
    -   `Save As (Ctrl+Shift+S)`: Opens `QFileDialog` to save project to a new `.json` file.
    -   `Exit (Ctrl+Q)`: Closes the application.
-   **Edit:**
    -   `Paste from Clipboard (Ctrl+V)`: Pastes system clipboard content into `Narrative Text Area`.
    -   `Auto Copy Phrase to Clipboard`: A checkable action, enabled by default.
    -   `Appearance`: A sub-menu with a checkable, exclusive group of actions for all available system styles (e.g., Fusion, Windows).
    -   `Theme`: A sub-menu with a checkable, exclusive group of actions for `Auto`, `Light`, and `Dark` themes.
-   **Help:**
    -   `About`: Displays a `QMessageBox` with application details, license, and repository link.

#### Narrative Text Area (`QTextEdit`)
-   A large, multi-line `QTextEdit` widget for displaying and editing the narrative text.
-   **Dirty Indicator:** Displays a red border when the current inputs (text, word counts, whitelist) do not match the state of the last successful analysis.
-   **Live Highlighting:** Dynamically highlights all occurrences of a selected phrase, using a theme-aware color (`QPalette.Highlight`).

#### Echo Results List (`QTableWidget`)
-   Displays processed echo phrases.
-   Columns: `Count` (integer), `Words` (integer), `Phrase` (string).
-   The `Count` column updates live as the user edits the main text while a phrase is highlighted.

#### Whitelist Area (`QListWidget` with Controls)
-   `QListWidget` displaying the current project's custom abbreviations.
-   Accompanying buttons for `Add` and `Remove` whitelist entries.

#### Status Bar (`QStatusBar`)
-   Displays real-time messages: "Ready", "Processing...", "Project saved", "Copied to clipboard", etc.

#### Toolbar (`QToolBar`)
-   **Controls:**
    -   `Min Words:` (`QSpinBox`, configurable).
    -   `Max Words:` (`QSpinBox`, configurable, with its maximum value dynamically set).
    -   `Find Them / Find Again` (`QPushButton`).
    -   `Preset:` (`QComboBox` with "Longest First" and "Most Repeated" options).
    -   `Highlight:` (`QLineEdit`): An editable field that receives the selected phrase or accepts manual input for ad-hoc live searching.

### Behavior Specifications

-   **Processing Trigger:** The `Find Them / Find Again` button explicitly calls `model.py`'s `process_text()` method.
-   **Dirty State Logic (State Snapshotting):** After a successful analysis, a snapshot of the inputs (text, word counts, whitelist) is taken. The state is considered "dirty" if the current inputs no longer match this snapshot. This comparison is checked whenever a relevant input changes.
-   **Live Highlighting Behavior:** User interaction (clicking the results table or typing in the highlight field) triggers a 250ms debounce `QTimer`. When the timer finishes, a live search is performed on the main text, applying theme-aware highlights and updating the result counts. Editing the main text also re-triggers this process.
-   **Persistent Settings (`QSettings`):** The application uses `QSettings` to store and load the user's preferred GUI style, theme, and default sort preset. These are applied at startup. The sort preset is saved the moment it's changed.
-   **Project Loading:** Loading a project restores its specific state. A new project inherits the user's persistent global preferences.
-   **Model-to-UI Updates:** `model.py` uses PySide6 signals (e.g., `echo_results_updated`, `project_loaded`) to communicate with `main.py`, which updates the UI via connected slots.

## Technical Implementation

### Architecture
-   **`model.py`**: A `QObject` encapsulating all application logic: data handling, text processing, echo detection, project management, and sorting.
-   **`main.py`**: The `QMainWindow` that manages the GUI, user interactions, and persistent settings via `QSettings`. It acts as the view/controller.
-   **Threading**: Long-running operations in `model.py` (specifically `process_text()`) must run in a separate `QThread` to keep the GUI responsive.

### Data Model

#### Project Structure (JSON file, e.g., `my_project.json`)
```json
{
  "project_name": "My Narrative Analysis",
  "original_text": "The turtle started running and then it smiled...",
  "min_phrase_words": 2,
  "max_phrase_words": 8,
  "custom_whitelist": ["Dr.", "Mr.", "Mrs.", "St.", "e.g.", "i.e."],
  "last_used_sort_preset": "longest_first_by_word_count",
  "echo_results": []
}
```

#### Echo Phrase Object Structure (within `echo_results` list)
```json
{
  "phrase": "the turtle started running and then it smiled",
  "count": 2,
  "words": 8,
  "occurrences": [
    {"start": 0, "end": 45},
    {"start": 50, "end": 95}
  ]
}
```

### Algorithms

1.  **Text Preprocessing:**
    *   Convert `original_text` to lowercase.
    *   Tokenize into a list of words, meticulously tracking original character indices for each token.
    *   Strip common punctuation unless a word matches an entry in the `custom_whitelist`.
    *   Calculate the maximum possible phrase length to update the UI's `Max Words` spin box limit.

2.  **N-gram Generation & Frequency Counting:**
    *   Generate all contiguous phrases (n-grams) within the user-selected `min_phrase_words` and `max_phrase_words` range.
    *   Store each unique phrase in a hash map, aggregating its `count`, `words`, and a list of all `occurrences` (character index tuples).

3.  **"Maximal Match" (Greedy) Filtering:**
    *   After counting, filter the results to ensure that if a longer echo `P_long` is reported, no shorter echo that is a substring of `P_long` and whose occurrences are fully contained within `P_long`'s occurrences is also reported.

4.  **Live Highlighting Logic:**
    *   This logic resides in `main.py`. It clears all existing text formats. It then uses `QTextDocument.find()` in a loop to find all occurrences of the search string (case-insensitively). For each match, it applies a `QTextCharFormat` with a background color from `QApplication.palette().color(QPalette.ColorRole.Highlight)`.

5.  **State Snapshotting Logic:**
    *   A tuple containing the full narrative text, min/max word values, and a sorted tuple of whitelist items is created and stored after a successful analysis. The dirty check involves creating a new snapshot of the current inputs and comparing it to the stored one.

### Dependencies
-   **PySide6** (version >= 6.9.1)
-   Standard Python libraries.

## Input/Output

### Input Specifications
-   **Text Input:** Raw text (string).
-   **`min_phrase_words` / `max_phrase_words`:** Integers.
-   **`custom_whitelist` entries:** List of strings.
-   **Sorting Preset Selection:** String ("longest_first_by_word_count", "most_repeated_short_to_long").
-   **Highlight Search:** String from the `Highlight` toolbar field.
-   **GUI Preferences:** Style name (string) and Theme ID (integer).

### Output Specifications
-   **`echo_results` Display:** `QTableWidget` rows: `Count`, `Words`, `Phrase`.
-   **Status Messages:** `QStatusBar` messages.
-   **Project Files:** `.json` files.

## Error Handling and Validation

-   **File Errors:** `model.py` will catch file I/O and JSON parsing errors and report them via status messages.
-   **Empty/Insufficient Text:** The `Find Them / Find Again` button is disabled if the text is empty or has fewer words than the selected `Min Words` setting.
-   **Empty Whitelist Entry:** User is prevented from adding an empty string to the whitelist.
-   **No Echoes Found:** An informative message is displayed in the status bar.
-   **Robust Dirty State:** The state snapshotting method ensures the red border indicator is accurate and not prone to race conditions from programmatic UI updates.

## Technical Constraints & Notes

-   **Text Volume:** Should handle text equivalent to ~6 book chapters.
-   **Responsiveness:** Long-running text processing must be offloaded to a `QThread` to keep the UI responsive. Live highlighting must be performant.
-   **Platform:** Primary target platform is Windows 10, but should be cross-platform compatible.
-   **Python-only:** No external APIs or runtime AI/LLM models are used.

## Acceptance Criteria

1.  **Core Echo Detection & Maximal Match Logic:**
    *   Given the test text `"The turtle started running and then it smiled and then the turtle started running and then it smiled..."`, the application correctly identifies ` "the turtle started running and then it smiled"` as the sole maximal match with a count of 2 and hides all shorter, contained echoes.

2.  **Live Highlighting and Count Update:**
    *   Clicking a result row highlights all occurrences of its phrase in the main text.
    *   Typing in the highlight field also triggers highlighting.
    *   Editing the main text causes highlights to update their positions correctly in real-time.
    *   Deleting a highlighted phrase in the text updates the `Count` in the results table for that phrase.
    *   Clearing the highlight field removes all highlights.

3.  **Persistent Settings:**
    *   Changing the theme to `Dark`, closing, and re-opening the application launches it in `Dark` theme.
    *   Changing the sort preset to `Most Repeated`, closing, and re-opening the application starts a new project with that preset selected.

4.  **Robust Dirty State:**
    *   Clicking `Find Them / Find Again` removes the red border. The border does not reappear until the user makes a meaningful change to the text, word count settings, or whitelist.

5.  **UI Customization:**
    *   Selecting a new `Appearance` style or `Theme` from the `Edit` menu instantly updates the application's look and feel.