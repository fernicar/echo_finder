# echo_finder

A smart tool for writers to find and eliminate repetitive phrases (echoes) in their text.


*The echo_finder application analyzing text and displaying results.*

## About The Project

`echo_finder` is a desktop application designed specifically for writers, editors, and content creators who want to improve the quality and flow of their narrative. It goes beyond simple word counting to intelligently identify and highlight redundant phrases, helping you create fresher, more engaging text.

The core of `echo_finder` is its "Maximal Match" logic. Instead of overwhelming you with every minor repetition, it focuses on the **longest possible repeating sequences**, giving you the most significant and actionable insights to refine your work.

### Key Features

-   **Maximal Match Logic**: Intelligently finds the longest repeating phrases ("greedy" matching) and hides shorter, overlapping echoes to reduce noise.
-   **Configurable Word Count**: Set a minimum and maximum number of words for a phrase to be considered an echo, giving you full control over the analysis.
-   **Custom Whitelist**: Preserve the integrity of abbreviations and proper nouns (e.g., "Dr.", "Mr. Jones") by adding them to a project-specific whitelist.
-   **Sorting Presets**: Organize the results to focus on what matters most to you—either the most frequently repeated phrases or the longest ones.
-   **Project Management**: Save your text, configurations, and results into a simple `.json` file to resume your work at any time.
-   **Clipboard Integration**: Instantly copy any found phrase to your clipboard with a single click for easy searching and editing in your primary writing tool.

### Built With

`echo_finder` is built with modern, robust technologies to ensure performance and a clean user experience.

*   [**PySide6**](https://www.qt.io/qt-for-python): The official Python bindings for the Qt framework, used for building the entire graphical user interface.
*   **Regular Expression Tokenizer**: The core text processing engine is built using Python's native `re` module. This powerful approach allows for precise and flexible tokenization, ignoring punctuation while respecting a custom whitelist, which is crucial for accurate echo detection across sentence boundaries.

## Getting Started

Follow these steps to get `echo_finder` running on your local machine.

### Prerequisites

-   Python 3.8+

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/fernicar/echo_finder.git
    ```
2.  **Navigate to the project directory:**
    ```sh
    cd echo_finder
    ```
3.  **Create and activate a virtual environment (recommended):**
    -   On Windows:
        ```sh
        python -m venv .venv
        .\venv\Scripts\activate
        ```
    -   On macOS/Linux:
        ```sh
        python3 -m venv .venv
        source .venv/bin/activate
        ```
4.  **Install the required dependencies:**
    ```sh
    pip install -r requirements.txt
    ```
5.  **Run the application:**
    ```sh
    python main.py
    ```

## Usage

1.  **Input Text**: Paste your text directly into the top panel, or open a previously saved `.json` project file via `File > Open`.
2.  **Configure Parameters**: Use the toolbar to set the `Min Words` and `Max Words` for the phrase search.
3.  **Find Echoes**: Click the `Find Them / Find Again` button to start the analysis. The UI will remain responsive while the processing happens in the background.
4.  **Review Results**: The results will appear in the middle panel, sorted by your chosen preset. By default, clicking on a phrase in the results list will automatically copy it to your clipboard.
5.  **Manage Whitelist**: Add or remove terms from the whitelist in the bottom panel to improve the accuracy of the analysis for your specific text.
6.  **Save Your Work**: Use `File > Save` or `Save As` to store your session in a `.json` file.

## License
[MIT License](LICENSE)

---

## Acknowledgments
*   Special thanks to ScuffedEpoch for the TINS methodology and the initial example.
*   Thanks to the free tier AI assistant for its initial contribution to the project.
*   Research LLM Gemini2.5flash (free tier beta testing) from Google AI Studio.

This project builds upon the foundations of the following projects:
- [TINS Edition](https://ThereIsNoSource.com) - Zero Source Specification platform that enables:
  - Complete application reconstruction from specification
  - Self-documenting architecture through detailed markdown
  - Future-proof design adaptable to advancing LLM capabilities
  - Progressive enhancement support as LLM technology evolves
  - Platform-agnostic implementation guidelines
  - Flexible technology stack selection within specified constraints
  - Comprehensive behavioral specifications for consistent rebuilds
  - Automatic adaptation to newer LLM models and capabilities
- [JeredBlu's PRD Creator](https://github.com/JeredBlu/custom-instructions/blob/main/prd-creator-3-25.md) - A comprehensive Product Requirements Document (PRD) creator.