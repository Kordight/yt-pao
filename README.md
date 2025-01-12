# YT-PAO
Efficient YouTube playlist analyzer & organizer.

## What is YT-PAO

YT-PAO is a tool designed to extract data from YouTube playlists. This tool can be used to archive playlists, track removed videos, or simply export playlist data for other purposes.

## Requirements

YT-PAO uses a few external libraries. You can install them with `pip install -r requirements.txt`

## Install

To install YT-PAO, simply clone this repository or manually download it from GitHub.

## Usage

Example usage:

`python3 main.py --playlistLink --resultFormat --listMode`

Flags:

- `--playlistLink` - str input with the YouTube playlist link
- `--resultFormat` - str input separated by spaces that generates the report in. Expected values: `cmd`, `txt`, `json`, `mySQL`, `csv`
- `--listMode` - str input specifying the work mode, expected values: `all`, `unavailable`, `available`
