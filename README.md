# SCALE System - Professional Weighbridge Management

SCALE System is a comprehensive, professional-grade weighbridge management application built with Python and PyQt6. It provides a robust solution for managing weighing transactions, with features designed for industrial and commercial environments.

## Key Features

-   **Real-time Weighing:** Live data from serial-connected weighbridges.
-   **Multiple Weighing Modes:** Supports two-pass (first and second weight) and fixed-tare weighing.
-   **User and Role Management:** Secure PIN-based authentication with three user roles (Admin, Supervisor, Operator).
-   **Transaction Management:** Create, track, and manage weighing transactions.
-   **Data Export:** Export transaction data to CSV and JSON formats.
-   **Hardware Integration:** Automated RS232 serial port detection and configuration.
-   **Comprehensive Reporting:** Generate detailed reports for analysis.
-   **Headless and Demo Modes:** Includes modes for automated testing and demonstration without a GUI.

## Project Structure

The project is organized into the following directories:

-   `auth/`: User authentication and session management.
-   `config/`: Application configuration files.
-   `core/`: Core application logic and configuration management.
-   `data/`: SQLite database and exported data files.
-   `database/`: Database schema and data access layer.
-   `docs/`: Project documentation.
-   `hardware/`: Serial communication and hardware management.
-   `logs/`: Application log files.
-   `tests/`: Automated tests.
-   `ui/`: PyQt6 user interface components.
-   `utils/`: Helper functions and utilities.
-   `weighing/`: Business logic for weighing operations.

## Installation

1.  **Prerequisites:**
    -   Python 3.8 or higher.

2.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    The `requirements.txt` file lists all dependencies. To run the full GUI application, you will need to install the optional dependencies as well.

    -   **For the core application (headless/CLI):**
        ```bash
        pip install pyserial qrcode
        ```

    -   **For the full GUI application:**
        ```bash
        pip install pyserial qrcode PyQt6
        ```

    You can also install all dependencies (including development tools) from the provided `requirements.txt` file, but be aware that it lists some standard libraries that do not need to be installed via pip.

    ```bash
    pip install -r requirements.txt
    ```

## Usage

The application can be launched from the `main.py` script with various command-line arguments.

-   **To run the GUI application:**
    ```bash
    python main.py
    ```

-   **To run in test mode (with simulated data):**
    ```bash
    python main.py --test-mode
    ```

-   **To run headless tests (no GUI):**
    ```bash
    python main.py --headless
    ```

-   **To run automated demo scenarios:**
    ```bash
    python main.py --demo
    ```

## Default Credentials

The system comes with default user accounts for testing:

-   **Admin:** `pin=1234`
-   **Supervisor:** `pin=2345`
-   **Operator:** `pin=3456`

## Testing

To run the suite of headless tests, use the `--headless` flag:

```bash
python main.py --headless
```

This will execute tests for authentication, weight simulation, mock serial communication, and the complete workflow without launching the GUI.

## Dependencies

The `requirements.txt` file includes core dependencies, optional packages for the GUI and other features, and standard Python libraries (which do not need to be installed via `pip`). For a minimal setup, you only need `pyserial` and `qrcode`. For the full experience, `PyQt6` is also required.
