# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LimsSample(models.Model):
    _name = 'lims.sample'
    _description = 'Sample'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reception desc, name desc'

    # ─── Identification ───────────────────────────────────────────
    name = fields.Char(
        string='Sample Reference', required=True,
        copy=False, readonly=True, default=lambda self: _('New')
    )
    barcode = fields.Char(string='Barcode', copy=False)
    external_ref = fields.Char(string='Customer / External Reference')
    sample_type_id = fields.Many2one('lims.sample.type', string='Sample Type', required=True)
    matrix_id = fields.Many2one('lims.matrix', string='Matrix', required=True)

    # ─── Customer & request ───────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    request_id = fields.Many2one('lims.request', string='Analysis Request')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    # ─── Sampling ─────────────────────────────────────────────────
    sampling_date = fields.Datetime(string='Sampling Date')
    sampling_location = fields.Char(string='Sampling Location')
    sampling_by = fields.Char(string='Sampled By')
    sampler_id = fields.Many2one('res.users', string='Sampling Agent')

    # ─── Reception ────────────────────────────────────────────────
    date_reception = fields.Datetime(
        string='Reception Date', default=fields.Datetime.now, tracking=True
    )
    received_by = fields.Many2one('res.users', string='Received By',
                                   default=lambda self: self.env.user)
    condition_reception = fields.Selection([
        ('good', 'Good'),
        ('degraded', 'Degraded'),
        ('rejected', 'Rejected'),
    ], string='Condition on Receipt', default='good', tracking=True)
    condition_note = fields.Text(string='Reception Remarks')

    # ─── Deadlines ────────────────────────────────────────────────
    date_due = fields.Date(string='Analysis Due Date')
    date_results = fields.Datetime(string='Results Delivered Date')
    is_urgent = fields.Boolean(string='Urgent', default=False)
    is_overdue = fields.Boolean(
        string='Overdue', compute='_compute_is_overdue', store=True
    )

    # ─── Analyses ─────────────────────────────────────────────────
    analysis_ids = fields.One2many('lims.analysis', 'sample_id', string='Analyses')
    analysis_count = fields.Integer(compute='_compute_analysis_count', string='Analyses Count')

    # ─── Global status ────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('received', 'Received'),
        ('in_progress', 'In Analysis'),
        ('results_ready', 'Results Available'),
        ('validated', 'Validated'),
        ('reported', 'Report Issued'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    conformity_state = fields.Selection([
        ('pending', 'Pending'),
        ('conform', 'Conform'),
        ('non_conform', 'Non Conform'),
        ('inconclusive', 'Inconclusive'),
    ], string='Conformity', compute='_compute_conformity', store=True)

    # ─── Chain of custody (ISO 17025) ─────────────────────────────
    custody_log_ids = fields.One2many('lims.custody.log', 'sample_id', string='Custody Log')

    # ─── Storage ──────────────────────────────────────────────────
    storage_location = fields.Char(string='Storage Location')
    storage_temp = fields.Char(string='Storage Temperature')
    disposal_date = fields.Date(string='Planned Disposal Date')

    # ─── Invoicing ────────────────────────────────────────────────
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    is_invoiced = fields.Boolean(
        string='Invoiced', compute='_compute_is_invoiced', store=True
    )

    # ─── Notes ────────────────────────────────────────────────────
    note = fields.Html(string='Internal Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # ─── Computed ─────────────────────────────────────────────────
    @api.depends('analysis_ids')
    def _compute_analysis_count(self):
        for rec in self:
            rec.analysis_count = len(rec.analysis_ids)

    @api.depends('date_due', 'state')
    def _compute_is_overdue(self):
        from datetime import date
        today = date.today()
        for rec in self:
            rec.is_overdue = (
                rec.date_due and rec.date_due < today
                and rec.state not in ('validated', 'reported', 'cancelled')
            )

    @api.depends('analysis_ids.conformity_state')
    def _compute_conformity(self):
        for rec in self:
            states = rec.analysis_ids.mapped('conformity_state')
            if not states:
                rec.conformity_state = 'pending'
            elif 'non_conform' in states:
                rec.conformity_state = 'non_conform'
            elif all(s == 'conform' for s in states):
                rec.conformity_state = 'conform'
            elif all(s in ('conform', 'inconclusive') for s in states):
                rec.conformity_state = 'inconclusive'
            else:
                rec.conformity_state = 'pending'

    @api.depends('invoice_id', 'invoice_id.payment_state')
    def _compute_is_invoiced(self):
        for rec in self:
            rec.is_invoiced = bool(rec.invoice_id)

    # ─── ORM ──────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.sample') or _('New')
        return super().create(vals_list)

    # ─── Workflow actions ─────────────────────────────────────────
    def action_receive(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft samples can be received.'))
            rec.state = 'received'
            rec._add_custody_log('Received at the laboratory')

    def action_start_analysis(self):
        for rec in self:
            if not rec.analysis_ids:
                raise UserError(_('Please create at least one analysis first.'))
            rec.state = 'in_progress'
            rec._add_custody_log('Analyses started')

    def action_validate(self):
        for rec in self:
            incomplete = rec.analysis_ids.filtered(
                lambda a: a.state not in ('validated', 'cancelled')
            )
            if incomplete:
                raise UserError(_(
                    'All analyses must be validated before validating the sample.\n'
                    'Pending analyses: %s'
                ) % ', '.join(incomplete.mapped('name')))
            rec.state = 'validated'
            rec.date_results = fields.Datetime.now()
            rec._add_custody_log('Results validated')

    def action_report(self):
        for rec in self:
            rec.state = 'reported'
            rec._add_custody_log('Report issued to customer')

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ─── Custody ──────────────────────────────────────────────────
    def _add_custody_log(self, action, notes=''):
        self.env['lims.custody.log'].create({
            'sample_id': self.id,
            'action': action,
            'user_id': self.env.user.id,
            'date': fields.Datetime.now(),
            'notes': notes,
        })

    # ─── Action buttons ───────────────────────────────────────────
    def action_view_analyses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample Analyses'),
            'res_model': 'lims.analysis',
            'view_mode': 'list,form',
            'domain': [('sample_id', '=', self.id)],
            'context': {'default_sample_id': self.id},
        }

    def action_print_certificate(self):
        return self.env.ref('lims_lab.action_lims_certificate_report').report_action(self)

    def action_create_invoice(self):
        """Create an invoice from the sample's analyses."""
        self.ensure_one()
        if self.is_invoiced:
            raise UserError(_('This sample is already invoiced.'))
        if self.state not in ('validated', 'reported'):
            raise UserError(_('The sample must be validated before creating an invoice.'))

        invoice_lines = []
        for analysis in self.analysis_ids.filtered(lambda a: a.state == 'validated'):
            product = analysis.parameter_id.product_id
            if product:
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f'[{analysis.name}] {analysis.parameter_id.name}',
                    'quantity': 1,
                    'price_unit': analysis.parameter_id.price,
                }))

        if not invoice_lines:
            raise UserError(_('No parameter with a billing product defined.'))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': invoice_lines,
            'narration': f'Sample: {self.name}',
        })
        self.invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }


class LimsSampleType(models.Model):
    _name = 'lims.sample.type'
    _description = 'Sample Type'
    _order = 'name'

    name = fields.Char(string='Type', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    default_matrix_id = fields.Many2one('lims.matrix', string='Default Matrix')
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)


class LimsCustodyLog(models.Model):
    _name = 'lims.custody.log'
    _description = 'Chain of Custody Log'
    _order = 'date desc'
    _rec_name = 'action'

    sample_id = fields.Many2one('lims.sample', string='Sample', required=True, ondelete='cascade')
    date = fields.Datetime(string='Date/Time', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    action = fields.Char(string='Action', required=True)
    location_from = fields.Char(string='From')
    location_to = fields.Char(string='To')
    notes = fields.Text(string='Notes')
    signature = fields.Binary(string='Signature')
