# LIMS - Laboratory Information Management System for Odoo

A complete laboratory workflow inside Odoo, from sample reception to certificate of analysis. Built around ISO/IEC 17025 practices and ready to run on Odoo Community.

The technical module is `lims_lab`.

## Features

- Sample management: reception with barcode, sample types and matrices, deadlines, storage and a full chain-of-custody log
- Analyses and measurements: parameters, analytical methods and equipment; replicate measurements with the final value averaged automatically and still editable
- Conformity engine: min/max limits, LOD and LOQ per parameter; each result flagged Conform, Non Conform or Below LOD
- ISO 17025: measurement uncertainty and confidence level, equipment calibration and verification tracking, accredited methods and parameters
- Certificate of analysis and analysis sheet (PDF)
- Non-conformities and CAPA with root cause, corrective and preventive actions, and effectiveness check
- Analysis requests and quotations, invoicing of analyses through Odoo Sales and Accounting
- Four access levels: Technician, Analyst, Quality Manager, LIMS Manager

## Supported versions

| Odoo version | Branch |
|---|---|
| 17.0 | `17.0` |
| 18.0 | `18.0` |
| 19.0 | `19.0` |
| 20.0 | `20.0` |

## Installation

Copy the `lims_lab` folder into your Odoo addons path, update the apps list, then install **LIMS** from the Apps menu.

## A generic base, made to be tailored

Every laboratory works differently: its own parameters, limits, methods, report layout and regulatory context. This module gives you a solid generic foundation, designed from the start to be customized to your lab.

Need your parameters pre-loaded, a certificate in your branding, a specific accreditation workflow or an integration with your instruments? That is what we do.

## License

LGPL-3

## About

Developed and maintained by Expodo. Odoo migrations and custom development.
Website: https://expodo.fr
Contact: info@expodo.fr
