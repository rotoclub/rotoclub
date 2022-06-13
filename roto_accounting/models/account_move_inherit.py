# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    analytic_group_id = fields.Many2one(
        comodel_name='account.analytic.group',
        string='Business Center',
        compute='_compute_analytic_group',
        store=True
    )

    @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_account_id')
    def _compute_analytic_group(self):
        for rec in self:
            analytic_group = False
            if rec.invoice_line_ids and rec.invoice_line_ids.analytic_account_id:
                # Identify the Analytic group related with the invoice behind the analytic account
                group = rec.invoice_line_ids.analytic_account_id.group_id
                if group:
                    analytic_group = group[0]
            rec['analytic_group_id'] = analytic_group
