# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, _


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist.item'

    product_company = fields.Many2one(
        string='Product Company',
        related='product_tmpl_id.company_id',
    )
