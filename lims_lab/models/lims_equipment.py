# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class LimsEquipment(models.Model):
    _name = 'lims.equipment'
    _description = 'Laboratory Equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Equipment Name', required=True, tracking=True)
    reference = fields.Char(string='Internal Reference', copy=False)
    serial_number = fields.Char(string='Serial Number')
    equipment_type = fields.Selection([
        ('instrument', 'Analytical Instrument'),
        ('auxiliary', 'Auxiliary Equipment'),
        ('reference', 'Reference Material'),
        ('consumable', 'Critical Consumable'),
    ], string='Type', required=True, default='instrument')

    # Identification
    brand = fields.Char(string='Brand / Manufacturer')
    model = fields.Char(string='Model')
    location = fields.Char(string='Location')

    # Calibration and metrology (ISO 17025)
    last_calibration_date = fields.Date(string='Last Calibration')
    calibration_interval = fields.Integer(string='Calibration Interval (days)', default=365)
    next_calibration_date = fields.Date(
        string='Next Calibration',
        compute='_compute_next_calibration',
        store=True
    )
    calibration_body = fields.Char(string='Calibration Body')
    calibration_certificate = fields.Char(string='Calibration Certificate No.')

    # Periodic verification
    last_verification_date = fields.Date(string='Last Verification')
    verification_interval = fields.Integer(string='Verification Interval (days)', default=90)
    next_verification_date = fields.Date(
        string='Next Verification',
        compute='_compute_next_verification',
        store=True
    )

    # Metrological status
    metrological_state = fields.Selection([
        ('ok', 'Conform'),
        ('to_calibrate', 'To Calibrate'),
        ('to_verify', 'To Verify'),
        ('out_of_service', 'Out of Service'),
        ('repair', 'Under Repair'),
    ], string='Metrological Status', compute='_compute_metrological_state', store=True)

    state = fields.Selection([
        ('active', 'In Service'),
        ('maintenance', 'Under Maintenance'),
        ('out_of_service', 'Out of Service'),
    ], default='active', string='Status', tracking=True)

    # Documents
    document_ids = fields.Many2many('ir.attachment', string='Documents')
    note = fields.Text(string='Notes')

    responsible_id = fields.Many2one('res.users', string='Responsible')

    @api.depends('last_calibration_date', 'calibration_interval')
    def _compute_next_calibration(self):
        for rec in self:
            if rec.last_calibration_date and rec.calibration_interval:
                from datetime import timedelta
                rec.next_calibration_date = rec.last_calibration_date + timedelta(days=rec.calibration_interval)
            else:
                rec.next_calibration_date = False

    @api.depends('last_verification_date', 'verification_interval')
    def _compute_next_verification(self):
        for rec in self:
            if rec.last_verification_date and rec.verification_interval:
                from datetime import timedelta
                rec.next_verification_date = rec.last_verification_date + timedelta(days=rec.verification_interval)
            else:
                rec.next_verification_date = False

    @api.depends('next_calibration_date', 'next_verification_date', 'state')
    def _compute_metrological_state(self):
        today = date.today()
        for rec in self:
            if rec.state == 'out_of_service':
                rec.metrological_state = 'out_of_service'
            elif rec.state == 'maintenance':
                rec.metrological_state = 'repair'
            elif rec.next_calibration_date and rec.next_calibration_date < today:
                rec.metrological_state = 'to_calibrate'
            elif rec.next_verification_date and rec.next_verification_date < today:
                rec.metrological_state = 'to_verify'
            else:
                rec.metrological_state = 'ok'
