# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LimsAnalysis(models.Model):
    _name = 'lims.analysis'
    _description = 'Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_planned, name'

    name = fields.Char(
        string='Analysis Reference', required=True,
        copy=False, default=lambda self: _('New')
    )

    # ─── Links ────────────────────────────────────────────────────
    sample_id = fields.Many2one('lims.sample', string='Sample', required=True, ondelete='cascade')
    parameter_id = fields.Many2one('lims.parameter', string='Parameter', required=True)
    method_id = fields.Many2one('lims.method', string='Analytical Method')
    equipment_id = fields.Many2one('lims.equipment', string='Equipment Used')

    # ─── Assignment ───────────────────────────────────────────────
    analyst_id = fields.Many2one('res.users', string='Assigned Analyst')
    validator_id = fields.Many2one('res.users', string='Validator', readonly=True)

    # ─── Planning ─────────────────────────────────────────────────
    date_planned = fields.Datetime(string='Planned Analysis Date')
    date_start = fields.Datetime(string='Analysis Start')
    date_end = fields.Datetime(string='Analysis End')
    duration = fields.Float(
        string='Duration (h)', compute='_compute_duration', store=True
    )

    # ─── Results ──────────────────────────────────────────────────
    result_ids = fields.One2many('lims.result', 'analysis_id', string='Results')
    result_count = fields.Integer(compute='_compute_result_count')

    # Final result (aggregated) — computed from retained measurements, editable
    final_value = fields.Float(
        string='Final Value',
        compute='_compute_final_value', store=True, readonly=False,
        help="Mean of the retained measurements (outliers and quality controls excluded). "
             "Computed automatically but can be overridden manually."
    )
    mean_measurements = fields.Float(
        string='Measurements Mean', compute='_compute_mean_measurements',
        help="Computed mean of the retained measurements. Reference value."
    )
    measurement_used_count = fields.Integer(
        string='Retained Measurements', compute='_compute_mean_measurements'
    )
    final_value_char = fields.Char(string='Result (text)', help='For qualitative results')
    unit_id = fields.Many2one(
        'lims.unit', string='Unit',
        related='parameter_id.unit_id', readonly=True
    )
    is_qualitative = fields.Boolean(string='Qualitative Analysis', default=False)
    qualitative_result = fields.Selection([
        ('positive', 'Positive / Present'),
        ('negative', 'Negative / Absent'),
        ('trace', 'Trace'),
    ], string='Qualitative Result')

    # ─── Conformity ───────────────────────────────────────────────
    conformity_state = fields.Selection([
        ('pending', 'Pending'),
        ('conform', 'Conform'),
        ('non_conform', 'Non Conform'),
        ('inconclusive', 'Inconclusive'),
        ('below_lod', 'Below LOD'),
    ], string='Conformity', compute='_compute_conformity', store=True)

    limit_min = fields.Float(
        string='Min Limit', related='parameter_id.limit_min', readonly=True
    )
    limit_max = fields.Float(
        string='Max Limit', related='parameter_id.limit_max', readonly=True
    )

    # ─── Measurement uncertainty (ISO 17025) ──────────────────────
    uncertainty = fields.Float(string='Measurement Uncertainty (±)')
    uncertainty_unit = fields.Many2one('lims.unit', string='Uncertainty Unit')
    confidence_level = fields.Float(string='Confidence Level (%)', default=95.0)

    # ─── Status ───────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Pending'),
        ('in_progress', 'In Progress'),
        ('results_entered', 'Results Entered'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)

    # ─── QC (internal Quality Control) ────────────────────────────
    is_qc_required = fields.Boolean(string='Quality Control Required', default=False)
    qc_sample_type = fields.Selection([
        ('blank', 'Reagent Blank'),
        ('duplicate', 'Duplicate'),
        ('spike', 'Spike'),
        ('standard', 'Reference Standard'),
        ('crs', 'Certified Reference Material'),
    ], string='QC Type')
    qc_result = fields.Float(string='QC Result')
    qc_accepted = fields.Boolean(string='QC Accepted')
    qc_note = fields.Text(string='QC Note')

    note = fields.Html(string='Observations')

    # ─── Computed ─────────────────────────────────────────────────
    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0.0

    @api.depends('result_ids')
    def _compute_result_count(self):
        for rec in self:
            rec.result_count = len(rec.result_ids)

    # Measurement types treated as quality control (excluded from the final result)
    _QC_MEASUREMENT_TYPES = ('blank', 'spike', 'standard', 'crs')

    def _get_valid_measurements(self):
        """Measurements retained for the final result: used, not flagged as outliers,
        and not quality controls (blank, spike, standard, CRM)."""
        self.ensure_one()
        return self.result_ids.filtered(
            lambda r: r.is_used_for_result
            and not r.is_outlier
            and r.measurement_type not in self._QC_MEASUREMENT_TYPES
        )

    @api.depends('result_ids.value_corrected', 'result_ids.is_used_for_result',
                 'result_ids.is_outlier', 'result_ids.measurement_type')
    def _compute_mean_measurements(self):
        for rec in self:
            valid = rec._get_valid_measurements()
            rec.measurement_used_count = len(valid)
            rec.mean_measurements = (
                sum(valid.mapped('value_corrected')) / len(valid) if valid else 0.0
            )

    @api.depends('result_ids.value_corrected', 'result_ids.is_used_for_result',
                 'result_ids.is_outlier', 'result_ids.measurement_type', 'is_qualitative')
    def _compute_final_value(self):
        for rec in self:
            # Qualitative result: the numeric value does not apply
            if rec.is_qualitative:
                rec.final_value = rec.final_value or 0.0
                continue
            valid = rec._get_valid_measurements()
            if valid:
                rec.final_value = sum(valid.mapped('value_corrected')) / len(valid)
            else:
                # No measurement: keep the manually entered value
                rec.final_value = rec.final_value or 0.0

    def action_compute_final_value(self):
        """Button: force recomputation of the final value from the measurements."""
        for rec in self:
            valid = rec._get_valid_measurements()
            if not valid:
                raise UserError(_("No retained measurement to average. "
                                  "Add measurements in the \"Individual Measurements\" tab."))
            rec.final_value = sum(valid.mapped('value_corrected')) / len(valid)

    @api.depends('final_value', 'limit_min', 'limit_max', 'state', 'is_qualitative', 'qualitative_result')
    def _compute_conformity(self):
        for rec in self:
            if rec.state != 'validated':
                rec.conformity_state = 'pending'
                continue
            if rec.is_qualitative:
                # Qualitative conformity: negative = conform
                rec.conformity_state = 'conform' if rec.qualitative_result == 'negative' else 'non_conform'
                continue
            # LOD check
            lod = rec.parameter_id.lod
            if lod and rec.final_value < lod:
                rec.conformity_state = 'below_lod'
                continue
            # Quantitative conformity
            has_min = rec.limit_min != 0
            has_max = rec.limit_max != 0
            if not has_min and not has_max:
                rec.conformity_state = 'inconclusive'
            elif has_min and rec.final_value < rec.limit_min:
                rec.conformity_state = 'non_conform'
            elif has_max and rec.final_value > rec.limit_max:
                rec.conformity_state = 'non_conform'
            else:
                rec.conformity_state = 'conform'

    # ─── ORM ──────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lims.analysis') or _('New')
        return super().create(vals_list)

    @api.onchange('parameter_id')
    def _onchange_parameter_id(self):
        if self.parameter_id:
            # Take the first available method
            if self.parameter_id.method_ids:
                self.method_id = self.parameter_id.method_ids[0]
            self.is_qualitative = False

    # ─── Workflow ─────────────────────────────────────────────────
    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.date_start = fields.Datetime.now()
            # Update the sample if needed
            if rec.sample_id.state == 'received':
                rec.sample_id.state = 'in_progress'

    def action_enter_results(self):
        for rec in self:
            if rec.is_qualitative:
                if not rec.qualitative_result:
                    raise UserError(_('Select a qualitative result before proceeding.'))
            else:
                valid = rec._get_valid_measurements()
                if not valid and rec.final_value == 0 and not rec.final_value_char:
                    raise UserError(_(
                        'Enter at least one measurement in the "Individual Measurements" tab '
                        'or set a final value before moving to the next step.'))
            rec.state = 'results_entered'
            rec.date_end = fields.Datetime.now()

    def action_validate(self):
        for rec in self:
            if rec.state != 'results_entered':
                raise UserError(_('Results must be entered before validation.'))
            if not rec.is_qualitative:
                valid = rec._get_valid_measurements()
                # A final value of 0 is accepted only if it comes from a real measurement
                if rec.final_value == 0 and not rec.final_value_char and not valid:
                    raise UserError(_('Please enter a result value or at least one measurement.'))
            elif not rec.qualitative_result:
                raise UserError(_('Select a qualitative result before validation.'))
            rec.state = 'validated'
            rec.validator_id = self.env.user.id
        # Check whether all the sample's results are validated
        for rec in self:
            sample = rec.sample_id
            all_validated = all(a.state in ('validated', 'cancelled') for a in sample.analysis_ids)
            if all_validated and sample.state == 'in_progress':
                sample.state = 'results_ready'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset(self):
        self.state = 'draft'

    def action_view_results(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Results'),
            'res_model': 'lims.result',
            'view_mode': 'list,form',
            'domain': [('analysis_id', '=', self.id)],
            'context': {'default_analysis_id': self.id},
        }
