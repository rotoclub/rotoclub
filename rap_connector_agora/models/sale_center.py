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
        comodel_name='res.company'
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
    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    tax_included = fields.Boolean(
        string='Tax Included'
    )
    location_ids = fields.One2many(
        string='Sale Locations',
        comodel_name='sale.location',
        inverse_name='center_id',
        ondelete='cascade'
    )
    pricelist_id = fields.Many2one(
        string='Pricelist',
        comodel_name='product.pricelist',
        ondelete='cascade'
    )


class SaleLocation(models.Model):
    _name = 'sale.location'
    _description = 'Locations for a Sale Center'

    name = fields.Char(
        string='Name'
    )
    center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company'
    )
