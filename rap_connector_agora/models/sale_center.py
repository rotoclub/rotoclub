# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class SaleCenter(models.Model):
    _name = 'sale.center'
    _description = 'Sales Zones for each CECO'

    name = fields.Char(
        string='Name'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        check_company=True
    )
    analytic_id = fields.Many2one(
        string='Analytic Account',
        comodel_name='account.analytic.account'
    )
    analytic_group_id = fields.Many2one(
        string='Analytic Group',
        related='analytic_id.group_id'
    )
    button_text = fields.Char(
        string='Button Text'
    )
    color = fields.Char(
        string='Color'
    )
    agora_id = fields.Char(
        string='Agora ID'
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        pricelist_env = self.env['product.pricelist']
        existing_list = pricelist_env.search([('sale_center_id', '=', res.id)])
        if not existing_list:
            # TODO: Generate the pricelist from the agora connector just to prevent pricelist deleted
            pricelist_env.create({
                'name': res.name,
                'company_id': res.company_id.id,
                'sale_center_id': res.id
            })
        return res
