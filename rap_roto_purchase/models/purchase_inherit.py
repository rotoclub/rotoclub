# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    supplier_qty = fields.Float(
        string='Supplier Qty'
    )
    supplier_uom = fields.Many2one(
        string='Supplier Uom',
        comodel_name='uom.uom',
    )
    price_per_unit = fields.Float(
        string='Price/Unit',
        compute='_compute_price_per_unit'
    )

    @api.onchange('product_uom')
    def onchange_filter(self):
        uom_ids = self.env['uom.uom'].sudo().search([('category_id', '=', self.product_uom.category_id.id)])
        if uom_ids:
            return {'domain': {'supplier_uom': [('id', 'in', uom_ids.ids)]}}

    @api.onchange('supplier_uom', 'supplier_qty', 'product_uom')
    def _onchange_supplier_qty(self):
        # Convert from supplier unit of messure to product unit of messure
        if self.supplier_uom and self.product_uom:
            qty = self.supplier_uom._compute_quantity(self.supplier_qty, self.product_uom, rounding_method='HALF-UP')
            self.min_qty = qty

    @api.depends('price', 'min_qty')
    def _compute_price_per_unit(self):
        for rec in self:
            price = 0.0
            if rec.min_qty:
                price = rec.price / rec.min_qty
            rec.price_per_unit = price



