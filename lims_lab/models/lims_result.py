# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LimsResult(models.Model):
    _name = 'lims.result'
    _description = 'Measurement Result'
    _order = 'sequence, date_measurement'

    analysis_id = fields.Many2one('lims.analysis', string='Analysis', required=True, ondelete='cascade')
    sample_id = fields.Many2one(
        'lims.sample', string='Sample',
        related='analysis_id.sample_id', store=True, readonly=True
    )
    parameter_id = fields.Many2one(
        'lims.parameter', string='Parameter',
        related='analysis_id.parameter_id', store=True, readonly=True
    )

    sequence = fields.Integer(string='Measurement No.', default=1)
    date_measurement = fields.Datetime(string='Measurement Date/Time', default=fields.Datetime.now)
    analyst_id = fields.Many2one('res.users', string='Analyst', default=lambda self: self.env.user)

    # Value
    value = fields.Float(string='Measured Value', digits=(16, 6))
    value_char = fields.Char(string='Value (text)')
    unit_id = fields.Many2one(
        'lims.unit', string='Unit',
        related='analysis_id.unit_id', readonly=True
    )

    # Measurement type
    measurement_type = fields.Selection([
        ('sample', 'Real Sample'),
        ('blank', 'Blank'),
        ('duplicate', 'Duplicate'),
        ('spike', 'Spike'),
        ('standard', 'Standard'),
        ('crs', 'Certified Reference Material'),
        ('repeat', 'Replicate'),
    ], string='Type', default='sample', required=True)

    # Instrument
    equipment_id = fields.Many2one('lims.equipment', string='Instrument')
    instrument_reading = fields.Float(string='Raw Instrument Reading')
    calibration_ref = fields.Char(string='Calibration Curve Reference')

    # Dilution
    dilution_factor = fields.Float(string='Dilution Factor', default=1.0)
    value_corrected = fields.Float(
        string='Corrected Value',
        compute='_compute_corrected', store=True
    )

    # Measurement quality
    is_outlier = fields.Boolean(string='Outlier', default=False)
    outlier_reason = fields.Char(string='Exclusion Reason')
    is_used_for_result = fields.Boolean(string='Used for Final Result', default=True)

    note = fields.Text(string='Observations')

    @api.depends('value', 'dilution_factor')
    def _compute_corrected(self):
        for rec in self:
            factor = rec.dilution_factor or 1.0
            rec.value_corrected = rec.value * factor

    @api.onchange('is_outlier')
    def _onchange_outlier(self):
        if self.is_outlier:
            self.is_used_for_result = False
        else:
            self.is_used_for_result = True
