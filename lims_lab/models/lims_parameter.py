# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LimsParameter(models.Model):
    _name = 'lims.parameter'
    _description = 'Analysis Parameter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Parameter Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False)
    description = fields.Text(string='Description')
    category_id = fields.Many2one('lims.parameter.category', string='Category')
    unit_id = fields.Many2one('lims.unit', string='Unit of Measure')
    method_ids = fields.Many2many(
        'lims.method', 'lims_parameter_method_rel',
        'parameter_id', 'method_id',
        string='Applicable Methods'
    )

    # Conformity limits
    limit_min = fields.Float(string='Minimum Limit')
    limit_max = fields.Float(string='Maximum Limit')
    limit_unit_id = fields.Many2one('lims.unit', string='Limits Unit')
    loq = fields.Float(string='Limit of Quantification (LOQ)')
    lod = fields.Float(string='Limit of Detection (LOD)')

    # ISO 17025 accreditation
    is_accredited = fields.Boolean(string='Accredited Parameter', default=False)
    accreditation_scope = fields.Char(string='Accreditation Scope')

    # Invoicing
    product_id = fields.Many2one(
        'product.product', string='Billing Product',
        domain=[('type', '=', 'service')]
    )
    price = fields.Float(string='Unit Price', related='product_id.lst_price', readonly=True)

    active = fields.Boolean(default=True)
    note = fields.Html(string='Technical Notes')

    _code_unique = models.Constraint(
        'unique(code)',
        'The parameter code must be unique.',
    )


class LimsParameterCategory(models.Model):
    _name = 'lims.parameter.category'
    _description = 'Parameter Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True)
    color = fields.Integer(string='Color')
    parameter_ids = fields.One2many('lims.parameter', 'category_id', string='Parameters')
    parameter_count = fields.Integer(compute='_compute_parameter_count', string='Parameters Count')

    @api.depends('parameter_ids')
    def _compute_parameter_count(self):
        for rec in self:
            rec.parameter_count = len(rec.parameter_ids)


class LimsUnit(models.Model):
    _name = 'lims.unit'
    _description = 'LIMS Unit of Measure'
    _order = 'name'

    name = fields.Char(string='Unit', required=True)
    symbol = fields.Char(string='Symbol')
    description = fields.Char(string='Description')
