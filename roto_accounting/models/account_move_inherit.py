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
    partner_embargado = fields.Boolean(
        string='Partner Embargado',
        related='partner_id.es_embargado',
        store=True
    )
    estado_embargo = fields.Char(
        string='Estado Embargo',
        compute='_compute_estado_embargo',
        store=True
    )

    @api.depends('partner_embargado')
    def _compute_estado_embargo(self):
        for record in self:
            record.estado_embargo = 'EMBARGADO' if record.partner_embargado else False

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
