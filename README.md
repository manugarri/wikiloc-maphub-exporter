# Wikiloc MapHub Exporter

Wikiloc Exporter is a tool designed to export Trail GPS tracks from Wikiloc to MapHub

## Installation

To install the Wikiloc Exporter, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/wikiloc_exporter.git
    ```
2. Navigate to the project directory:
    ```sh
    cd wikiloc_exporter
    ```
3. Install the required dependencies:
    ```sh
    uv venv
    uv sync
    ```

*Note that I am using uv as the dependency manager here, but you can use pip/poetry whatever else you use*

## Usage

To use the Wikiloc Exporter, first make sure you have your maphub api token set up as an environment variable (see `.envrc.example` for the required variable name), then run the following command:
```sh
python wikiloc_export.py WIKILOC_URL
```

Where `WIKILOC_URL` is the url of the wikiloc trail you want to export.
