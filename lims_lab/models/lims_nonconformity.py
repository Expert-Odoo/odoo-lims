# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LimsNonConformity(models.Model):
    _name = 'lims.nonconformity'
    _description = 'Non-Conformity / CAPA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_detected desc'

    name = fields.Char(
        string='NC No.', required=True,
        copy=False, default=lambda self: _('New')
    )
    title = fields.Char(string='Title / Summary', required=True)

    # ─── Classification ───────────────────────────────────────────
    nc_type = fields.Selection([
        ('result', 'Non-Conform Result'),
        ('method', 'Method Deviation'),
        ('equipment', 'Equipment Failure'),
        ('process', 'Procedure Deviation'),
        ('customer', 'Customer Complaint'),
        ('internal_audit', 'Internal Audit'),
        ('external_audit', 'External Audit / Accreditation'),
        ('other', 'Other'),
    ], string='NC Type', required=True)

    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='minor', tracking=True)

    # ─── Links ────────────────────────────────────────────────────
    sample_id = fields.Many2one('lims.sample', string='Related Sample')
    analysis_id = fields.Many2one('lims.analysis', string='Related Analysis')
    equipment_id = fields.Many2one('lims.equipment', string='Related Equipment')
    method_id = fields.Many2one('lims.method', string='Related Method')
    partner_id = fields.Many2one('res.partner', string='Related Customer')

    # ─── Detection ────────────────────────────────────────────────
    date_detected = fields.Date(string='Detection Date', required=True, default=fields.Date.today)
    detected_by = fields.Many2one('res.users', string='Detected By', default=lambda self: self.env.user)
    description = fields.Html(string='Non-Conformity Description', required=True)
    root_cause = fields.Html(string='Identified Root Cause')

    # ─── Immediate actions ────────────────────────────────────────
    immediate_action = fields.Html(string='Immediate Action (containment)')
    immediate_action_date = fields.Date(string='Immediate Action Date')
    immediate_action_by = fields.Many2one('res.users', string='Performed By')

    # ─── CAPA ─────────────────────────────────────────────────────
    corrective_action = fields.Html(string='Corrective Action')
    preventive_action = fields.Html(string='Preventive Action')
    action_due_date = fields.Date(string='CAPA Due Date')
    action_responsible = fields.Many2one('res.users', string='CAPA Responsible')

    # ─── Effectiveness check ──────────────────────────────────────
    effectiveness_check = fields.Html(string='Effectiveness Check')
    effectiveness_date = fields.Date(string='Verification Date')
    effectiveness_by = fields.Many2one('res.users', string='Verified By')
    is_effective = fields.Boolean(string='Effective CAPA')

    # ─── Closure ──────────────────────────────────────────────────
    date_closed = fields.Date(string='Closure Date')
    closed_by = fields.Many2one('res.users', string='Closed By', readonly=True)
    closure_note = fields.Text(string='Closure Comment')

    # ─── Status ───────────────────────────────────────────────────
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('capa_defined', 'CAPA Defined'),
        ('capa_implemented', 'CAPA Implemented'),
        ('verification', 'Under Verification'),
        ('closed', 'Closed'),
    ], default='open', string='Status', tracking=True)

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    note = fields.Text(string='Additional Notes')

    # ─── ORM ──────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.nonconformity') or _('New')
        return super().create(vals_list)

    # ─── Workflow ─────────────────────────────────────────────────
    def action_start_treatment(self):
        self.state = 'in_progress'

    def action_define_capa(self):
        for rec in self:
            if not rec.corrective_action and not rec.preventive_action:
                raise UserError(_('Please define at least one corrective or preventive action.'))
        self.state = 'capa_defined'

    def action_implement_capa(self):
        self.state = 'capa_implemented'

    def action_verify(self):
        self.state = 'verification'

    def action_close(self):
        for rec in self:
            if not rec.is_effective:
                raise UserError(_('Please confirm the effectiveness of the CAPA before closing.'))
        self.write({
            'state': 'closed',
            'date_closed': fields.Date.today(),
            'closed_by': self.env.user.id,
        })

    def action_reopen(self):
        self.write({'state': 'open', 'date_closed': False})
