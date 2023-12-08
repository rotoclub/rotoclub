# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AgoraProduct(models.Model):
    _name = 'agora.product'
    _description = 'Agora Product'

    instance_id = fields.Many2one(
        comodel_name='api.connection',
        string='Agora Instance'
    )
    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    base_format_id = fields.Integer(
        string='Base Sale Format',
        copy=False
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template'
    )
    sale_format = fields.Integer(
        string='Sale Format',
        copy=False
    )
