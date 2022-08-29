# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, _


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

    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    sync_status = fields.Selection(
        selection=[('done', 'Completed'),
                   ('new', 'New'),
                   ('modifiyed', 'Modifiyed'),
                   ('error', 'Error')],
        default='new'
    )

    def write(self, vals):
        res = super(ProductPricelist, self).write(vals)
        for rec in self:
            if rec.sync_status != 'new' and (vals.get('discount_policy') or vals.get('name') or 'active' in vals):
                rec.sync_status = 'modifiyed'
        return res
