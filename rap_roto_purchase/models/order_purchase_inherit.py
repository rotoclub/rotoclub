# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_set_supplier_uom(self):
        # Set supplier info by default
        if self.product_id and self.order_id.partner_id:
            # Convert standard qty to supplier uom
            product = self.env['product.supplierinfo'].search([('name', '=', self.order_id.partner_id.id),
                                                               ('product_tmpl_id', '=', self.product_id.id)])
            if product:
                # If there is not supplier product should be keeped the standard values
                self.product_uom = product.supplier_uom
                self.product_qty = product.supplier_qty

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super()._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        if self._context.get('from_orderpoint'):
            product_taxes = product_id.supplier_taxes_id.filtered(lambda x: x.company_id.id == company_id.id)
            taxes = po.fiscal_position_id.map_tax(product_taxes)
            partner = supplier.name
            uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
            seller = product_id.with_company(company_id)._select_seller(
                partner_id=partner,
                quantity=uom_po_qty,
                date=po.date_order and po.date_order.date(),
                uom_id=product_id.uom_po_id)
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                supplier.supplier_price, product_taxes, taxes, company_id) if supplier else 0.0
            if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                price_unit = seller.currency_id._convert(
                    price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())
            res.update({
                'product_qty': product_qty,
                'product_uom': product_uom.id,
                'price_unit': price_unit
            })
        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def _onchange_supplier_qty(self):
        # The objective is to convert the qty and uom depending on the Supplier
        # There are onchange functions inside of the line to the the same with other triggers
        for val in self.order_line:
            if val.product_id and self.partner_id:
                product = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id),
                                                                   ('product_tmpl_id', '=', val.product_id.id)])
                if product:
                    val.product_uom = product.supplier_uom
                    val.product_qty = product.supplier_qty

