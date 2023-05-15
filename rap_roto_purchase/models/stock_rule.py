# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api, fields, models, registry, _
from odoo.tools import add, float_compare, frozendict, split_every
from odoo.addons.stock.models.stock_rule import ProcurementException
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from itertools import groupby


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_buy(self, procurements):
        """
        Overwrite the standard function to modify something in the middle of the standard behaviour
        Change only executed if come from "Orderpoint" (Context)
        """
        if self._context.get('from_orderpoint'):
            account_group_env = self.env['account.analytic.group']
            procurements_by_po_domain = defaultdict(list)
            errors = []
            for procurement, rule in procurements:

                # Get the schedule date in order to find a valid seller
                procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])

                supplier = False
                if procurement.values.get('supplierinfo_id'):
                    supplier = procurement.values['supplierinfo_id']
                else:
                    supplier = procurement.product_id.with_company(procurement.company_id.id)._select_seller(
                        partner_id=procurement.values.get("supplierinfo_name"),
                        quantity=procurement.product_qty,
                        date=procurement_date_planned.date(),
                        uom_id=procurement.product_uom)

                # Fall back on a supplier for which no price may be defined. Not ideal, but better than
                # blocking the user.
                supplier = supplier or procurement.product_id._prepare_sellers(False).filtered(
                    lambda s: not s.company_id or s.company_id == procurement.company_id
                )[:1]

                if not supplier:
                    msg = _(
                        'There is no matching vendor price to generate the purchase order for product %s'
                        ' (no vendor defined, minimum quantity not reached, dates not valid, ...). '
                        'Go on the product form and complete the list of vendors.') % (
                              procurement.product_id.display_name)
                    errors.append((procurement, msg))

                partner = supplier.name
                # we put `supplier_info` in values for extensibility purposes
                procurement.values['supplier'] = supplier
                procurement.values['propagate_cancel'] = rule.propagate_cancel

                domain = rule._make_po_get_domain(procurement.company_id, procurement.values, partner)
                procurements_by_po_domain[domain].append((procurement, rule))

            if errors:
                raise ProcurementException(errors)

            for domain, procurements_rules in procurements_by_po_domain.items():
                # Get the procurements for the current domain.
                # Get the rules for the current domain. Their only use is to create
                # the PO if it does not exist.
                procurements, rules = zip(*procurements_rules)

                # Get the set of procurement origin for the current domain.
                origins = set([p.origin for p in procurements])
                # Check if a PO exists for the current domain.
                po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
                company_id = procurements[0].company_id
                if not po:
                    positive_values = [p.values for p in procurements if
                                       float_compare(p.product_qty, 0.0, precision_rounding=p.product_uom.rounding) >= 0]
                    if positive_values:
                        # We need a rule to generate the PO. However the rule generated
                        # the same domain for PO and the _prepare_purchase_order method
                        # should only uses the common rules's fields.
                        vals = rules[0]._prepare_purchase_order(company_id, origins, positive_values)
                        # The company_id is the same for all procurements since
                        # _make_po_get_domain add the company in the domain.
                        # We use SUPERUSER_ID since we don't want the current user to be follower of the PO.
                        # Indeed, the current user may be a user without access to Purchase, or even be a portal user.
                        po = self.env['purchase.order'].with_company(company_id).with_user(SUPERUSER_ID).create(vals)
                        # When Purchase order is created the bussiness center should be set
                        acc_group = account_group_env.search([('picking_type_id', '=', po.picking_type_id.id)], limit=1)
                        po.analytic_group_id = acc_group
                else:
                    # If a purchase order is found, adapt its `origin` field.
                    if po.origin:
                        missing_origins = origins - set(po.origin.split(', '))
                        if missing_origins:
                            po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                    else:
                        po.write({'origin': ', '.join(origins)})

                procurements_to_merge = self._get_procurements_to_merge(procurements)
                procurements = self._merge_procurements(procurements_to_merge)

                po_lines_by_product = {}
                # The lines by default will be grouped by product uom,
                # but in the new behaviour should be by the cheaper supplier uom,
                # value previously changed in the procurement. Only will be set the behaviour is come from orderpoint
                if self._context.get('from_orderpoint'):
                    grouped_po_lines = groupby(
                        po.order_line.filtered
                            (lambda l: not l.display_type and l.product_uom == procurement.product_uom).sorted(
                            lambda l: l.product_id.id), key=lambda l: l.product_id.id)
                else:
                    grouped_po_lines = groupby(
                        po.order_line.filtered
                            (lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id).sorted(
                            lambda l: l.product_id.id), key=lambda l: l.product_id.id)
                for product, po_lines in grouped_po_lines:
                    po_lines_by_product[product] = self.env['purchase.order.line'].concat(*list(po_lines))
                po_line_values = []
                for procurement in procurements:
                    po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                    po_line = po_lines._find_candidate(*procurement)

                    if po_line:
                        # If the procurement can be merge in an existing line. Directly
                        # write the new values on it.
                        vals = self._update_purchase_order_line(procurement.product_id,
                                                                procurement.product_qty, procurement.product_uom,
                                                                company_id,
                                                                procurement.values, po_line)
                        po_line.write(vals)
                    else:
                        if float_compare(procurement.product_qty, 0,
                                         precision_rounding=procurement.product_uom.rounding) <= 0:
                            # If procurement contains negative quantity, don't create a new line that would contain negative qty
                            continue
                        # If it does not exist a PO line for current procurement.
                        # Generate the create values for it and add it to a list in
                        # order to create it in batch.
                        partner = procurement.values['supplier'].name
                        po_line_values.append \
                            (self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(
                            procurement.product_id, procurement.product_qty,
                            procurement.product_uom, procurement.company_id,
                            procurement.values, po))
                        # Check if we need to advance the order date for the new line
                        order_date_planned = procurement.values['date_planned'] - relativedelta(
                            days=procurement.values['supplier'].delay)
                        if fields.Date.to_date(order_date_planned) < fields.Date.to_date(po.date_order):
                            po.date_order = order_date_planned
                self.env['purchase.order.line'].sudo().create(po_line_values)
        else:
            super(StockRule, self)._run_buy(procurements)

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        """
        Overwrite the standard function to modify something in the middle of the standard behaviour
        Change only executed if come from "Orderpoint" (Context)
        """
        if self._context.get('from_orderpoint'):
            partner = values['supplier'].name
            # Use the qty from the procurenment and do not recompute with the product uom like as follow
            # product_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
            seller = product_id.with_company(company_id)._select_seller(
                partner_id=partner,
                quantity=line.product_qty + product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date(),
                uom_id=product_uom)

            price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.supplier_price, line.product_id.supplier_taxes_id, line.taxes_id, company_id) if seller else 0.0
            if price_unit and seller and line.order_id.currency_id and seller.currency_id != line.order_id.currency_id:
                price_unit = seller.currency_id._convert(
                    price_unit, line.order_id.currency_id, line.order_id.company_id, fields.Date.today())

            res = {
                'product_qty': line.product_qty + product_qty,
                'price_unit': price_unit,
                'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])]
            }
            orderpoint_id = values.get('orderpoint_id')
            if orderpoint_id:
                res['orderpoint_id'] = orderpoint_id.id
        else:
            res = super(StockRule, self)._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        return res
