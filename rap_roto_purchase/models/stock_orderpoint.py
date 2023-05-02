# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, registry, _
from odoo.tools import add, float_compare, frozendict, split_every
from psycopg2 import OperationalError
from odoo.addons.stock.models.stock_rule import ProcurementException

import logging
_logger = logging.getLogger(__name__)


class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=None, raise_user_error=True):
        """
        Overwrite the standard function to modify something in the middle of the standdard behaviour
        Change only executed if come from "Orderpoint" (Context)
        """
        self = self.with_company(company_id)

        for orderpoints_batch_ids in split_every(1000, self.ids):
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            orderpoints_batch = self.env['stock.warehouse.orderpoint'].browse(orderpoints_batch_ids)
            all_orderpoints_exceptions = []
            while orderpoints_batch:
                procurements = []
                for orderpoint in orderpoints_batch:
                    origins = orderpoint.env.context.get('origins', {}).get(orderpoint.id, False)
                    if origins:
                        origin = '%s - %s' % (orderpoint.display_name, ','.join(origins))
                    else:
                        origin = orderpoint.name
                    if float_compare(orderpoint.qty_to_order, 0.0,
                                     precision_rounding=orderpoint.product_uom.rounding) == 1:
                        date = orderpoint._get_orderpoint_procurement_date()
                        values = orderpoint._prepare_procurement_values(date=date)
                        # Get the new values to create the procurement
                        # New values came from the cheaper supplier orderpoint.qty_to_order, orderpoint.product_uom
                        new_uom, new_qty, supp = self.get_supplier_qty_and_uom(orderpoint.product_uom,
                                                                         orderpoint.product_id, orderpoint.qty_to_order)
                        if supp:
                            values.update({'supplierinfo_id': supp})
                        # The Procurement will be created with the new QTY and UOM
                        procurements.append(self.env['procurement.group'].Procurement(
                            orderpoint.product_id, new_qty, new_uom,
                            orderpoint.location_id, orderpoint.name, origin,
                            orderpoint.company_id, values))

                try:
                    with self.env.cr.savepoint():
                        self.env['procurement.group'].with_context(from_orderpoint=True).run(procurements,
                                                                                             raise_user_error=raise_user_error)
                except ProcurementException as errors:
                    orderpoints_exceptions = []
                    for procurement, error_msg in errors.procurement_exceptions:
                        orderpoints_exceptions += [(procurement.values.get('orderpoint_id'), error_msg)]
                    all_orderpoints_exceptions += orderpoints_exceptions
                    failed_orderpoints = self.env['stock.warehouse.orderpoint'].concat(
                        *[o[0] for o in orderpoints_exceptions])
                    if not failed_orderpoints:
                        _logger.error('Unable to process orderpoints')
                        break
                    orderpoints_batch -= failed_orderpoints

                except OperationalError:
                    if use_new_cursor:
                        cr.rollback()
                        continue
                    else:
                        raise
                else:
                    orderpoints_batch._post_process_scheduler()
                    break

            # Log an activity on product template for failed orderpoints.
            for orderpoint, error_msg in all_orderpoints_exceptions:
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', orderpoint.product_id.product_tmpl_id.id),
                    ('res_model_id', '=', self.env.ref('product.model_product_template').id),
                    ('note', '=', error_msg)])
                if not existing_activity:
                    orderpoint.product_id.product_tmpl_id.activity_schedule(
                        'mail.mail_activity_data_warning',
                        note=error_msg,
                        user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
                    )

            if use_new_cursor:
                cr.commit()
                cr.close()
                _logger.info("A batch of %d orderpoints is processed and committed", len(orderpoints_batch_ids))
        return {}

    def get_supplier_qty_and_uom(self, uom, product, qty):
        """
        New function to get the cheaper supplier for an specific product.
        @Params:UOM, PRODUCT, QTY from the standard stock rule iin execution
        @Return: new_uom, new_qty from the cheaper supplier, QTY is recalculated depending on the new UOM
        """
        # By deafult will uom and qty will take the recommended value from odoo
        new_uom = uom
        new_qty = qty
        supplier = False
        product_suppliers = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', product.product_tmpl_id.id)])
        if product_suppliers:
            # If the product has suppliers. The cheaper should be found.
            min_price = min(product_suppliers.mapped('price_per_unit'))
            cheap_supplier = product_suppliers.filtered(lambda m: m.price_per_unit == min_price)
            supplier = cheap_supplier[0]
            # Get new Uom from supplier
            new_uom = supplier.supplier_uom
            # Convert old qty to the new UOM
            new_qty = uom._compute_quantity(qty, new_uom, rounding_method='HALF-UP')
        return new_uom, new_qty, supplier

    def _get_lead_days_values(self):
        """"
        Inherit the standard function to add the cheaper supplier related with the actual product
        Change only executed if come from "Orderpoint"
        """
        values = super()._get_lead_days_values()
        product_suppliers = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)])
        if product_suppliers and self._context.get('from_orderpoint'):
            min_price = min(product_suppliers.mapped('price_per_unit'))
            cheap_supplier = product_suppliers.filtered(lambda m: m.price_per_unit == min_price)
            values['supplierinfo'] = cheap_supplier[0]
        return values
