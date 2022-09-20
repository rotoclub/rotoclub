# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
                   ('modified', 'Modified'),
                   ('error', 'Error')],
        default='new'
    )
    sale_center_ids = fields.One2many(
        string='Sale Center',
        comodel_name='sale.center',
        inverse_name='pricelist_id',
    )

    def write(self, vals):
        res = super(ProductPricelist, self).write(vals)
        for rec in self:
            if rec.sync_status != 'new' and (vals.get('discount_policy') or vals.get('name') or 'active' in vals):
                rec.sync_status = 'modified'
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    agora_id = fields.Integer(
        string='Agora ID'
    )

    def unlink(self):
        for rec in self:
            if rec.name == 'Generic client':
                raise ValidationError(_('Sorry the record named {} can not be deleted.'
                                        ' Its used for sync purposes').format(rec.name))
        return super().unlink()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    agora_global_id = fields.Char(
        string='Global ID'
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

