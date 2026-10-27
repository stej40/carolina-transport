# ui-localization

## Purpose
Let every user work in their own language in both frontends, with the choice
stored on the user profile so it follows them across devices.

## ADDED Requirements

### Requirement: Supported languages
The dispatcher portal and the driver PWA SHALL support Czech (`cs`), English
(`en`), and German (`de`) for all user-facing interface text.

#### Scenario: All screens localized
- **WHEN** a user switches their language to any of the supported values
- **THEN** portal/PWA interface text renders in that language with no
  untranslated static labels

### Requirement: Per-user selection
The selected language SHALL be a per-user profile setting (see
identity-auth), applied on login/load, not a device-only choice.

#### Scenario: Same user, new device
- **WHEN** a user logs in on a different device
- **THEN** the interface uses the language stored on their profile

### Requirement: Sensible defaults
When no preference is stored yet, the dispatcher portal SHALL default to
English and the driver PWA SHALL default to Czech.

#### Scenario: First driver login
- **WHEN** a driver signs in for the first time with no language stored
- **THEN** the PWA renders in Czech until they change it
