# -*- coding: utf-8 -*-
{
    'name': 'LIMS - Laboratory Information Management System',
    'version': '19.0.1.2.0',
    'category': 'Laboratory',
    'summary': 'Complete laboratory management: samples, analyses, results, reports, invoicing and ISO 17025 compliance',
    'description': """
        Generic LIMS module for Odoo.
        =====================================
        Features:
        - Sample management (reception, tracking, barcode, chain of custody)
        - Configurable parameters, methods and units
        - Results and multi-level validation
        - Certificates of analysis and PDF reports
        - Invoicing linked to analyses
        - ISO 17025 compliance / accreditation
        - Non-conformity and CAPA management
        - Customer portal
    """,
    'author': 'Expodo',
    'website': 'https://expodo.fr/en/',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'sale',
    ],
    'data': [
        # Security — IMPORTANT : lims_category.xml doit être chargé EN PREMIER
        # pour que la ref "lims_lab.module_lims_category" soit disponible
        # dans lims_security.xml (les deux fichiers sont committés séparément).
        'security/lims_category.xml',
        'security/lims_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/lims_sequence_data.xml',
        'data/lims_parameter_data.xml',

        # Reports (loaded before views: views reference the report actions)
        'report/lims_certificate_report.xml',
        'report/lims_certificate_template.xml',
        'report/lims_analysis_report.xml',

        # Views
        'views/lims_sample_views.xml',
        'views/lims_analysis_views.xml',
        'views/lims_result_views.xml',
        'views/lims_method_views.xml',
        'views/lims_parameter_views.xml',
        'views/lims_equipment_views.xml',
        'views/lims_nonconformity_views.xml',
        'views/lims_request_views.xml',
        'views/lims_menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
