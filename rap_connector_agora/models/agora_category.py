# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AgoraCategory(models.Model):
    _name = 'agora.category'
    _description = 'Category from Agora'

    instance_id = fields.Many2one(
        comodel_name='api.connection',
        string='Agora Instance'
    )
    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    product_categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Product Category'
    )
