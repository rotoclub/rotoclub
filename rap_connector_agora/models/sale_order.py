# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_api_origin = fields.Many2one(
        comodel_name='sale.api',
        string='Sale Api',
        ondelete='restrict'
    )
    origin = fields.Char(
        string='Origin',
        related='sale_api_origin.origin'
    )

