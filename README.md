<div align="center">

<img src="https://github.com/user-attachments/assets/1bc2dcb0-eb96-41b8-82cf-74e50cc2f1e8" alt="GitHub Token Validator Logo" width="350"/>

</div>

<div align="center">

![Python](https://img.shields.io/badge/python-3.6%2B-3776AB.svg?style=flat-square&logo=python)
![Click](https://img.shields.io/badge/cli-click-blue?style=flat-square)
![Rich](https://img.shields.io/badge/output-rich-green?style=flat-square)
![Last Commit](https://img.shields.io/github/last-commit/zebbern/Github-Token-Validator/main?style=flat-square)

</div>

> **Github-Token-Validator** is a fast, concurrent CLI tool (gitcheck.py) to validate GitHub Personal Access Tokens (PATs), audit their scopes, and export results in various formats.

---

## Features

- **Concurrent Validation**: Validate hundreds of tokens in parallel with adjustable worker count.
- **Retry & Rate-Limit Handling**: Automatic retries for transient errors and waits when GitHub rate limits are encountered.
- **Flexible Output**: Rich console table, JSON, or CSV; dump valid tokens to a file.
- **Customizable**: Specify API endpoint (for GitHub Enterprise), required scopes, delay between requests, and more.
- **Verbose Logging**: Detailed logs to stderr or a file for auditing.

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/zebbern/Github-Token-Validator.git
cd Github-Token-Validator

# Install dependencies
pip install -r requirements.txt

# (Optional) Install as a package
pip install .
```

---

## Usage

```bash
# Check with all default taking tokens from tokens.txt by default
python gitcheck.py

# Basic check with defaults
python gitcheck.py --tokens-file tokens.txt

# Show full tokens, use 4 workers, require 'repo' scope, and output JSON
python gitcheck.py -w 4   --full-token   --min-scopes repo   --output-format json   --output-file results.json

# Export only valid tokens
python gitcheck.py --tokens-file tokens.txt   --valid-output-file valid_tokens.txt

# Custom GitHub Enterprise URL
python gitcheck.py --api-url https://github.company.com/api/v3/user   --tokens-file tokens.txt
```

---

## 📋 Options

| Flag                           | Description                                                 |
| ------------------------------ | ----------------------------------------------------------- |
| `--tokens-file`                | Path to file with one token per line (required)            |
| `-w`, `--workers`              | Number of concurrent workers (default: 2)                   |
| `--delay`                      | Seconds delay between requests per worker (default: 1.0)    |
| `--retries`                    | Number of retries for HTTP errors (default: 2)             |
| `--min-scopes`                 | Comma-separated required scopes to validate                |
| `--mask` / `--full-token`      | Mask tokens output (default: full-token)                    |
| `--output-format`              | Output format: text, json, csv (default: text)             |
| `--output-file`                | File to write JSON/CSV output                              |
| `--valid-output-file`          | File to write valid tokens (one per line)                  |
| `--log-file`                   | Path to detailed log file                                  |
| `-v`, `--verbose`              | Verbose logging to stderr                                  |
| `-h`, `--help`                 | Show help message                                          |

---

## 📷 Showcase

<div align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Github-Token-Validator+in+action" alt="Github-Token-Validator Screenshot" width="80%"/>
</div>

---

