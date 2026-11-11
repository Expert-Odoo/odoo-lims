# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LimsMethod(models.Model):
    _name = 'lims.method'
    _description = 'Analytical Method'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Method Name', required=True, tracking=True)
    code = fields.Char(string='Method Reference', required=True)
    description = fields.Text(string='Description')
    method_type = fields.Selection([
        ('internal', 'Internal Method'),
        ('standard', 'Norm / Standard'),
        ('accredited', 'Accredited Method'),
    ], string='Method Type', default='internal', required=True)

    # Normative reference
    standard_ref = fields.Char(string='Normative Reference', help='E.g. ISO 7027, EN 1484...')
    version = fields.Char(string='Version / Revision')
    revision_date = fields.Date(string='Revision Date')
    next_review_date = fields.Date(string='Next Review')

    # Accreditation
    is_accredited = fields.Boolean(string='ISO 17025 Accredited Method')
    accreditation_number = fields.Char(string='Accreditation No.')
    accreditation_body = fields.Char(string='Accreditation Body', help='E.g. A2LA, UKAS, ILAC member')
    accreditation_expiry = fields.Date(string='Accreditation Expiry')

    # Scope
    matrix_ids = fields.Many2many(
        'lims.matrix', 'lims_method_matrix_rel',
        'method_id', 'matrix_id',
        string='Applicable Matrices'
    )
    parameter_ids = fields.Many2many(
        'lims.parameter', 'lims_parameter_method_rel',
        'method_id', 'parameter_id',
        string='Covered Parameters'
    )

    # Required equipment
    equipment_ids = fields.Many2many(
        'lims.equipment', 'lims_method_equipment_rel',
        'method_id', 'equipment_id',
        string='Required Equipment'
    )

    # Documents
    document_ids = fields.Many2many('ir.attachment', string='Method Documents')
    sop_ref = fields.Char(string='SOP Reference')

    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('obsolete', 'Obsolete'),
    ], default='draft', string='Status', tracking=True)

    def action_validate(self):
        self.state = 'validated'

    def action_obsolete(self):
        self.state = 'obsolete'

    _code_unique = models.Constraint(
        'unique(code, version)',
        'The method code/version pair must be unique.',
    )


class LimsMatrix(models.Model):
    _name = 'lims.matrix'
    _description = 'Analysis Matrix'
    _order = 'name'

    name = fields.Char(string='Matrix', required=True, help='E.g. Water, Soil, Food, Air...')
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
