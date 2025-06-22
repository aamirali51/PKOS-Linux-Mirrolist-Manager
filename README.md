# PKOS Linux Mirrorlist Manager

This is a desktop application for PKOS Linux (Arch-based) built using PyQt6. It provides a graphical interface to manage the `/etc/pacman.d/mirrorlist` file.

**Developer:** Aamir Abdullah  
**Email:** aamirabdullah33@gmail.com  
**License:** Open Source  
**Version:** 2.0

## Features

- Fetch the latest Arch mirror list with filters for country, protocol, and active-only.
- Display mirrors in a GUI table with sorting and selection.
- Rank mirrors by download speed or ping.
- Apply changes to the mirrorlist with root permissions.
- Optional features include GeoIP auto-detection and systemd timer support.

## Project Structure

- `main.py`: Entry point of the application.
- `requirements.txt`: List of Python dependencies.
- `config/`: Directory for configuration files.
  - `config.json`: User configuration file.
- `src/`: Source code directory.
  - `ui/`: Directory for UI components.
    - `main_window.py`: Main window of the application.
    - `dialogs.py`: Dialogs for sudo prompts and error handling.
  - `core/`: Core functionalities.
    - `mirror_manager.py`: Logic for fetching, parsing, and managing mirrors.
    - `speed_test.py`: Functions for testing mirror speed.
    - `file_operations.py`: Functions for file operations with root permissions.
  - `utils/`: Utility functions.
    - `network.py`: Network-related utilities.
    - `geoip.py`: Optional GeoIP detection.

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## About PKOS Linux

PKOS Linux is a modern Arch-based Linux distribution focused on providing a user-friendly experience while maintaining the power and flexibility of Arch Linux.

## License

This project is open source and free to use, modify, and distribute.

## Contact

For questions, suggestions, or contributions, please contact:
- **Developer:** Aamir Abdullah
- **Email:** aamirabdullah33@gmail.com

## Contributing

This is an open source project. Contributions, bug reports, and feature requests are welcome!