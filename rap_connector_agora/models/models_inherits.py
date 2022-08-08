# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    color = fields.Char(
        string='Color'
    )


class ProductCategory(models.Model):
    _inherit = 'product.category'

    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    color = fields.Char(
        string='Color'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company'
    )


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center'
    )
