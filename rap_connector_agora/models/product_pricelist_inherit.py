# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    product_company = fields.Many2one(
        string='Product Company',
        related='product_tmpl_id.company_id',
    )
    addin_price = fields.Float(
        string='Addin Price',
        digits='Product Price'
    )
    menuitem_price = fields.Float(
        string='Menu Item Price',
        digits='Product Price'
    )

    @api.model
    def create(self, values):
        res = super(ProductPricelistItem, self).create(values)
        is_first_charge = self.env.context.get('first_charge')
        if not is_first_charge and res.product_tmpl_id and res.product_tmpl_id.sync_status != 'new':
            # When a new pricelist is created the Product related should be mark as modified
            res.product_tmpl_id.sync_status = 'modified'
            res.product_tmpl_id.parent_id.sync_status = 'modified'
        return res

    def write(self, vals):
        res = super(ProductPricelistItem, self).write(vals)
        is_first_charge = self.env.context.get('first_charge')
        for rec in self:
            if not is_first_charge and rec.product_tmpl_id.sync_status != 'new' and \
                    (vals.get('pricelist_id') or vals.get('fixed_price') or vals.get('addin_price') or vals.get('menuitem_price')):
                # When some values change the Product related should be mark as modified
                rec.product_tmpl_id.sync_status = 'modified'
                rec.product_tmpl_id.parent_id.sync_status = 'modified'
        return res

    @api.constrains('pricelist_id')
    def validate_pricelist_duplicity(self):
        for rec in self:
            exist = rec.product_tmpl_id.product_pricelist_ids.filtered(lambda l: l.id != rec.id and
                                                                                 l.pricelist_id == rec.pricelist_id)
            if exist:
                raise ValidationError(_('Sorry can not be more than one record with the same Pricelist associated'))
