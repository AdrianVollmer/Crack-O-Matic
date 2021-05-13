# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed

- Fix bug with empty config setting "additional cracker arguments" after
  upgrading from v0.1

## [0.2] - 2021-05-10

### Added

- Ability to pass custom command line arguments to cracker

### Fixed

- Fix the dependencies `packaging` and `argon2` in docs and `setup.py`
- Fix typos in helper strings of audit form
- Fix status display if hashcat is still initializing
- Avoid 'Internal Server Error' when retrieving the status fails
