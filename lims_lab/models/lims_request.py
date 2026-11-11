# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LimsRequest(models.Model):
    _name = 'lims.request'
    _description = 'Analysis Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc'

    name = fields.Char(
        string='Request No.', required=True,
        copy=False, default=lambda self: _('New')
    )

    # ─── Customer ─────────────────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    contact_id = fields.Many2one(
        'res.partner', string='Contact',
        domain="[('parent_id', '=', partner_id)]"
    )

    # ─── Request ──────────────────────────────────────────────────
    date_request = fields.Datetime(string='Request Date', default=fields.Datetime.now)
    date_due = fields.Date(string='Requested Deadline')
    is_urgent = fields.Boolean(string='Urgent')
    request_type = fields.Selection([
        ('routine', 'Routine Analysis'),
        ('urgent', 'Urgent'),
        ('accredited', 'ISO 17025 Accredited'),
        ('expert', 'Expertise / Consulting'),
    ], string='Service Type', default='routine')

    # ─── Description ──────────────────────────────────────────────
    description = fields.Text(string='Request Description')
    special_instructions = fields.Text(string='Special Instructions')

    # ─── Requested parameters ─────────────────────────────────────
    request_line_ids = fields.One2many(
        'lims.request.line', 'request_id', string='Requested Parameters'
    )

    # ─── Associated samples ───────────────────────────────────────
    sample_ids = fields.One2many('lims.sample', 'request_id', string='Samples')
    sample_count = fields.Integer(compute='_compute_counts', string='Samples Count')

    # ─── Quotation / Invoicing ────────────────────────────────────
    sale_order_id = fields.Many2one('sale.order', string='Quotation / Order', readonly=True)
    amount_total = fields.Float(
        string='Estimated Amount', compute='_compute_amount_total', store=True
    )

    # ─── Status ───────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)

    note = fields.Html(string='Internal Notes')

    # ─── Computed ─────────────────────────────────────────────────
    @api.depends('sample_ids')
    def _compute_counts(self):
        for rec in self:
            rec.sample_count = len(rec.sample_ids)

    @api.depends('request_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.request_line_ids.mapped('price_subtotal'))

    # ─── ORM ──────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.request') or _('New')
        return super().create(vals_list)

    # ─── Workflow ─────────────────────────────────────────────────
    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_view_samples(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Samples'),
            'res_model': 'lims.sample',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_create_samples(self):
        """Create samples from the request lines."""
        self.ensure_one()
        if not self.request_line_ids:
            raise UserError(_('Please define at least one parameter.'))
        # Redirect to sample creation wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Samples'),
            'res_model': 'lims.sample',
            'view_mode': 'form',
            'context': {
                'default_request_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_date_due': self.date_due,
                'default_is_urgent': self.is_urgent,
            },
        }

    def action_create_quotation(self):
        """Create an Odoo Sale quotation from the request."""
        self.ensure_one()
        lines = []
        for line in self.request_line_ids:
            if line.parameter_id.product_id:
                lines.append((0, 0, {
                    'product_id': line.parameter_id.product_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                }))
        sale = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': lines,
            'note': f'Analysis request: {self.name}',
        })
        self.sale_order_id = sale.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': sale.id,
            'view_mode': 'form',
        }


class LimsRequestLine(models.Model):
    _name = 'lims.request.line'
    _description = 'Analysis Request Line'
    _order = 'sequence'

    request_id = fields.Many2one('lims.request', string='Request', ondelete='cascade')
    sequence = fields.Integer(default=10)
    parameter_id = fields.Many2one('lims.parameter', string='Parameter', required=True)
    method_id = fields.Many2one('lims.method', string='Method')
    quantity = fields.Integer(string='Number of Samples', default=1)
    price_unit = fields.Float(
        string='Unit Price', related='parameter_id.price', readonly=False
    )
    price_subtotal = fields.Float(
        string='Subtotal', compute='_compute_subtotal', store=True
    )
    note = fields.Char(string='Note')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit

    @api.onchange('parameter_id')
    def _onchange_parameter_id(self):
        if self.parameter_id and self.parameter_id.method_ids:
            self.method_id = self.parameter_id.method_ids[0]
