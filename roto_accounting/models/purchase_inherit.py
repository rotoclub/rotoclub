# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    analytic_group_id = fields.Many2one(
        comodel_name='account.analytic.group',
        string='Business Center'
    )
    default_analytic = fields.Many2one(
        comodel_name='account.analytic.account',
        compute='_compute_default_analytic'
    )

    @api.depends('analytic_group_id')
    def _compute_default_analytic(self):
        analytic_env = self.env['account.analytic.account']
        for rec in self:
            analytic = analytic_env.search([('group_id', '=', rec.analytic_group_id.id)], limit=1)
            rec.default_analytic = analytic

    @api.onchange('analytic_group_id')
    def default_analytic_account(self):
        picking = self._get_picking_type(self.env.context.get('company_id') or self.env.company.id)
        if self.analytic_group_id.picking_type_id:
            picking = self.analytic_group_id.picking_type_id.id
        self.picking_type_id = picking


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    order_group_id = fields.Many2one(
        related='order_id.analytic_group_id',
        string='Order Analytic Group'
    )
