# XFileTransferApp

## Overview
XFileTransferApp implements a file transfer system using Python's socket programming. It allows users to send and receive files over a network using a client-server architecture.

## Features
- **Client-Server Architecture**: Simple and efficient file transfer between a client and a server.
- **Multi-threading**: Supports concurrent file transfers using threads.
- **Configurable Settings**: Users can configure settings such as file paths, host IPs, and ports through a configuration file.
- **Progress Tracking**: Displays progress bars during file transfer using `tqdm`.

## Requirements
- Python 3.x
- Required libraries:
  - `socket`
  - `asyncio`
  - `zlib`
  - `threading`
  - `pickle`
  - `hashlib`
  - `tqdm`
  - `configparser`
  - `localization` (custom module)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/lavrentijav/XFileTransferApp.git
   ```
2. Navigate to the project directory:
   ```bash
   cd XFileTransferApp
   ```

3. Install any required libraries (if necessary):
   ```bash
   pip install tqdm
   ```

## Configuration
Before running the application, you need to configure the settings in the `config.ini` file. The application will create this file automatically if it does not exist. The configuration file contains the following sections:

```ini
[Settings server]
FILE = test.txt
MAX_PORTS = 4
HOST_IP = 127.0.0.1
HOST_PORT = 55500
MAX_PACKET_SIZE = 4096

[Settings client]
SAVE_PATH = .
HOST_IP = 127.0.0.1
HOST_PORT = 55500

[Languages]
LANGUAGE = en
```
## Usage
### Running the Server
Open a terminal and run the server: 
```
python xtfa.py
2
```
### Running the Client
Open another terminal and run the client: 
```
python xtfa.py
1
```
Sending Files
The client will prompt you to enter the file path you want to send, and the server will receive the file.
License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
Thanks to the contributors and the open-source community for their support and resources.
Contact
For any questions or feedback, please reach out to https://github.com/lavrentijav/XFileTransferApp/issues
