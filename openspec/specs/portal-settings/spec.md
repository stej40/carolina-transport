# portal-settings Specification


## Purpose
Holds company-wide portal configuration used by the dispatcher portal and
API, so creation flows are prefilled with agreed defaults such as currency.

## Requirements

### Requirement: Default currency setting
The system SHALL maintain a company-wide portal setting `default_currency`
whose value is CZK or EUR; the API MUST serve it to creation flows as the
prefilled order currency and MUST reject updates with any other value.

#### Scenario: Setting served
- **WHEN** a dispatcher portal requests portal settings
- **THEN** the API returns the current default currency

#### Scenario: Setting updated
- **WHEN** a dispatcher changes the default currency to EUR
- **THEN** subsequent order prefills and currency-less order creations use EUR

#### Scenario: Invalid value rejected
- **WHEN** a settings update carries a currency other than CZK or EUR
- **THEN** the system rejects the update and the stored value is unchanged
