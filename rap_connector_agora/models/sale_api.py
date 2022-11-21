# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError, ValidationError, AccessError

import logging
_logger = logging.getLogger(__name__)


class SaleApiLine(models.Model):
    _name = 'sale.api.line'
    _description = 'Sale Api lines'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True,
        ondelete='restrict',
        check_company=True
    )
    code = fields.Char(
        string='Code'
    )
    name = fields.Text(
        string='Description',
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='sale_api_id.company_id',
        string='Company',
        required=True,
        index=True
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='sale_api_id.currency_id',
        store=True,
        string='Currency',
        readonly=True
    )
    price_unit = fields.Float(
        string='Unit Price',
        required=True,
        digits='Product Price',
        default=0.0
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]", ondelete="restrict"
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id'
    )
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        domain=['|', ('active', '=', False), ('active', '=', True)]
    )
    sale_api_id = fields.Many2one(
        comodel_name='sale.api',
        string='Sale Api',
        ondelete='cascade'
    )
    discount = fields.Float(
        string='Discount (%)',
        default=0.0
    )
    price_subtotal = fields.Monetary(
        compute='_compute_amount',
        string='Subtotal',
        readonly=True,
        store=True
    )
    price_tax = fields.Float(
        compute='_compute_amount',
        string='Total Tax',
        readonly=True,
        store=True
    )
    price_total = fields.Monetary(
        compute='_compute_amount',
        string='Total',
        readonly=True,
        store=True
    )
    state = fields.Selection(
        selection=[('ready', 'Ready'),
                   ('error', 'Error')],
        string='Status',
        readonly=True,
        copy=False,
        index=True
    )

    @api.onchange('product_id')
    def product_id_change(self):
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id.id
        vals['product_uom_qty'] = self.product_uom_qty or 1.0
        vals['name'] = self.product_id.name
        product = self.product_id.with_context(
            partner=self.sale_api_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty, uom=self.product_uom.id
        )
        self._compute_tax_id()
        if self.sale_api_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.list_price, product.taxes_id, self.tax_id, self.company_id
            )
        self.update(vals)

    def _compute_tax_id(self):
        for line in self:
            fpos = line.sale_api_id.partner_id.property_account_position_id
            taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes, line.product_id, line.sale_api_id.partner_id) if fpos else taxes

    def get_sale_order_line_multiline_description_sale(self, product):
        return product.get_product_multiline_description_sale()

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.sale_api_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.sale_api_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


class SaleApi(models.Model):
    _description = "Sale Api"
    _name = 'sale.api'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    def _default_journal_id(self):
        return self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])], limit=1)

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    name = fields.Char('Order Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    origin = fields.Char('Source Document', help="Reference of the document that generated this sales order request.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft', tracking=1)
    type_ticket = fields.Selection([
        ('command', 'Command'),
        ('ticket', 'Ticket'),
    ], string='Type ticket', copy=False, index=True, default='ticket', tracking=1)
    date_order = fields.Datetime('Order Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)], 'ready': [('readonly', False)]}, copy=False, default=fields.Datetime.now, help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.", tracking=1)
    create_date = fields.Datetime('Creation Date', readonly=True, index=True)
    currency_id = fields.Many2one("res.currency", readonly=True, required=True, default=lambda self: self.env.company.currency_id.id)
    user_id = fields.Many2one('res.users', related='server_id.user_id', string='Salesperson')
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True, states={'draft': [('readonly', False)], 'ready': [('readonly', False)]}, required=True, change_default=True, index=True, tracking=1)
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'ready': [('readonly', False)], 'done': [('readonly', False)]})
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'ready': [('readonly', False)], 'done': [('readonly', False)]})
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', check_company=True, required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms', check_company=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    server_id = fields.Many2one('server.config', 'Server API', required=True, tracking=1)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=1)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', tracking=1)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=1)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', domain="[('company_id', '=', company_id)]", check_company=True, help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. The default value comes from the customer.")
    sale_api_line_ids = fields.One2many('sale.api.line', 'sale_api_id', 'Sale Api Lines', states={'cancelled': [('readonly', True)], 'done': [('readonly', True)]}, copy=True, auto_join=True)
    sale_order = fields.Many2one('sale.order', string='Sale Order', readonly=True, copy=False)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True, copy=False)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True, copy=False)
    journal_id = fields.Many2one('account.journal', string='Journal', default=_default_journal_id)
    internal_note = fields.Char("Int. Note")
    team_id = fields.Many2one('crm.team', 'Sales Team', ondelete="set null", tracking=True, change_default=True, default=_get_default_team, check_company=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    analytic_account_id = fields.Many2one('account.analytic.account', related='server_id.analytic_account_id', string='Analytic Account', copy=False, check_company=True, help="The analytic account related to a sales order.")
    general_notes = fields.Text(string='General Notes')
    sale_notes = fields.Text(string='Sale Notes')
    picking_notes = fields.Text(string='Picking Notes')
    invoice_notes = fields.Text(string='Invoice Notes')
    payment_notes = fields.Text(string='Payment Notes')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.api', sequence_date=seq_date) or _('New')
        return super(SaleApi, self).create(vals)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id
        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        self.update(values)

    @api.depends('sale_api_line_ids.price_subtotal')
    def _amount_all(self):
        for sale in self:
            amount_untaxed = amount_tax = 0.0
            for line in sale.sale_api_line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            sale.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def action_ready(self):
        for rec in self:
            rec.state = 'ready'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_conver_to_draf(self):
        for rec in self:
            if rec.sale_order:
                raise ValidationError("Delete the associated order to move it to Draft")
            else:
                rec.state = 'draft'

    def execute_sale_api(self):
        _logger.info('Begin: execute_sale_api')
        try:
            if self.server_id.state == 'open':
                if self.server_id.sale_flow == 'quotation':
                    _logger.info('quotation:' + self.name)
                    self.action_quotation_sale()
                elif self.server_id.sale_flow == 'confirmed' and self.type_ticket != 'command':
                    _logger.info('confirmed:' + self.name)
                    self.action_confirmed_sale()
                elif self.server_id.sale_flow == 'picking' and self.type_ticket != 'command':
                    _logger.info('picking:' + self.name)
                    self.action_picking()
                elif self.server_id.sale_flow == 'draft_invoice' and self.type_ticket != 'command':
                    _logger.info('draft_invoice:' + self.name)
                    self.action_invoice()
                elif self.server_id.sale_flow == 'invoice' and self.type_ticket != 'command':
                    _logger.info('invoice:' + self.name)
                    self.action_invoice_published()
                # elif self.server_id.sale_flow == 'payment' and self.type_ticket != 'command':
                #     _logger.info('payment:' + self.name)
                #     self.action_payment()
            self.state = 'done'
        except Exception as exp:
            self.state = 'error'
            raise UserError(_("Check your data, we can't create the object,\n"
                              "Here is the error:\n%s") % exp)
            _logger.info('error:')
            _logger.info(exp)

    def action_quotation_sale(self):
        _logger.info('Begin: action_quotation_sale')
        product_obj = self.env['product.product']
        order_obj = self.env['sale.order']
        for record in self:
            order_lines = []
            for line in record.sale_api_line_ids:
                line_vals = {}
                product = product_obj.search([('id', '=', line.product_id.id)], limit=1)
                if product:
                    taxes = line.tax_id if line.tax_id else False
                    line_vals = {
                        'price_unit': line.price_unit if line.price_unit else 0.0,
                        'product_id': product.id,
                        'product_uom': product.uom_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'name': line.name,
                        'tax_id': [(6, 0, taxes.ids)] if taxes else False,
                        'currency_id': self.currency_id.id,
                    }
                    order_lines.append((0, 0, line_vals))
            analytic_id = self.analytic_account_id
            order_vals = {
                'partner_id': record.partner_id.id,
                'date_order': record.date_order,
                'order_line': order_lines,
                'partner_shipping_id': record.partner_shipping_id.id,
                'pricelist_id': record.partner_id.property_product_pricelist.id,
                'currency_id': self.currency_id.id,
                'user_id': self.user_id.id,
                'analytic_account_id': analytic_id.id if analytic_id else False,
                'note': self.sale_notes
            }
            record.sale_order = order_obj.create(order_vals)
            if record.sale_order:
                _logger.info('Order Created:')
                _logger.info(record.sale_order)

    def action_confirmed_sale(self):
        self.action_quotation_sale()
        self.sale_order.action_confirm()

    def action_picking(self):
        self.action_confirmed_sale()
        for picking in self.sale_order.picking_ids:
            picking.action_confirm()
            picking.action_assign()
            picking._action_done()
            for line in picking.move_ids_without_package:
                line.quantity_done = line.product_uom_qty
            picking.button_validate()
        self.picking_id = self.sale_order.picking_ids.id
        self.picking_id.write({'user_id': self.user_id.id, 'note': self.picking_notes})

    def action_invoice(self):
        invoice_obj = self.env['account.move']
        self.action_picking()
        vals = self._prepare_invoice_sale()
        self.invoice_id = invoice_obj.create(vals)

    def _prepare_invoice_sale(self):
        self.ensure_one()
        journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        vals = {
            'move_type': 'out_invoice',
            'invoice_origin': self.sale_order.name,
            'partner_id': self.sale_order.partner_id.id,
            'partner_shipping_id': self.sale_order.partner_shipping_id.id,
            'fiscal_position_id': self.sale_order.partner_id.property_account_position_id and self.sale_order.partner_id.property_account_position_id.id or False,
            'company_id': self.company_id.id,
            'invoice_user_id': self.user_id.id,
            'journal_id': journal_id.id,
            'currency_id': self.currency_id.id,
            'team_id': self.sale_order.team_id.id,
            'invoice_line_ids': [],
            'narration': self.invoice_notes
        }
        for line in self.sale_order.order_line:
            fpos = vals['fiscal_position_id']
            account = False
            accounts = line.product_id.product_tmpl_id.get_product_accounts(fpos)
            account = accounts['income']
            vals['invoice_line_ids'].append((0, 0,
                                             {'product_id': line.product_id.id,
                                              'quantity': line.product_uom_qty,
                                              'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                                              'price_unit': line.price_unit,
                                              'account_id': account.id,
                                              'company_id': self.company_id.id,
                                              'name': line.product_id.partner_ref,
                                              'product_uom_id': line.product_uom and line.product_uom.id or line.product_id.uom_id.id,
                                              'sale_line_ids': [(6, 0, [line.id])],
                                              'tax_ids': line.tax_id,
                                              }))
        return vals

    def action_invoice_published(self):
        self.action_invoice()
        self.invoice_id.action_post()

    # def action_payment(self):
    #     self.action_invoice_published()
    #     now = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    #     payment_method = self.journal_id.inbound_payment_method_ids
    #     vals = {
    #         'partner_id': self.invoice_id.partner_id.id,
    #         'name': 'CUST' + self.invoice_id.name,
    #         'payment_type': 'inbound',
    #         'amount': self.invoice_id.amount_total,
    #         'date': now,
    #         'partner_type': 'customer',
    #         'ref': self.invoice_id.name,
    #         'journal_id': self.journal_id.id,
    #         'payment_method_id': payment_method.id,
    #         'ref': self.payment_notes
    #     }
    #     self.payment_id = payment = self.env['account.payment'].create(vals)
    #     payment.action_post()
    #     for line in payment.line_ids:
    #         if line.credit > 0:
    #             line_id = line.id
    #     try:
    #         self.invoice_id.js_assign_outstanding_line(line_id)
    #     except:
    #         pass
