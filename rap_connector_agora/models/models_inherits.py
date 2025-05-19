# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict
from datetime import date, timedelta

_logger = logging.getLogger(__name__)


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
        default='new',
        copy=False
    )
    sale_center_ids = fields.One2many(
        string='Sale Center',
        comodel_name='sale.center',
        inverse_name='pricelist_id',
    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    agora_id = fields.Integer(
        string='Agora ID'
    )
    is_generic = fields.Boolean(
        string='Is generic Client'
    )

    def unlink(self):
        for rec in self:
            if rec.is_generic:
                raise ValidationError(_('Sorry a Generic record can not be deleted. ({})'
                                        ' Its used for sync purposes').format(rec.name))
        return super().unlink()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    number = fields.Char(
        string='Number'
    )
    serie = fields.Char(
        string='Serie'
    )
    work_place_id = fields.Many2one(
        string='Work Place',
        comodel_name='work.place'
    )
    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center'
    )
    standard_invoice = fields.Integer(
        string='Standard Inv',
        help='If there is a value means an Standard Invoice have been generated and this is the ID'
    )
    payment_method = fields.Many2one(
        comodel_name='account.payment.method',
        string='Payment Method'
    )
    business_date = fields.Date(
        string='Business Day'
    )
    is_incomplete = fields.Boolean(
        string='Is not complete'
    )
    waiter = fields.Char(
        string='Waiter'
    )
    document_type = fields.Selection(
        selection=[('BasicInvoice', 'Basic Invoice'),
                   ('StandardInvoice', 'Standard Invoice'),
                   ('BasicRefund', 'Basic Refund'),
                   ('StandardRefund', 'Standard Refund')],
        default='BasicInvoice',
        string="Document type"
    )
    tips_amount = fields.Monetary(
        string='Tips amount',
        default=0.0
    )


class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        help='This field is will be use to assign the journal in the payments related with this analytic group'
    )
    work_place_id = fields.Many2one(
        string='Work Place',
        comodel_name='work.place',
        compute='_compute_work_place',
        help='This field will be use to define the Group related with the SO. '
             'Work place always will come in the order data from Agora'
    )
    warehouse_id = fields.Many2one(
        string='Warehouse',
        comodel_name='stock.warehouse',
        help='This field will be use to define the Warehouse in the SO. '
             'Work place always will come in the order data from Agora'
    )

    def _compute_work_place(self):
        group_env = self.env['work.place']
        for rec in self:
            a_group = group_env.search([('analytic_group_id', '=', rec.id)], limit=1)
            rec.work_place_id = a_group.id


class AccountMove(models.Model):
    _inherit = 'account.move'

    number = fields.Char(
        string='Number'
    )
    serie = fields.Char(
        string='Serie'
    )
    document_type = fields.Selection(
        selection=[('BasicInvoice', 'Basic Invoice'),
                   ('StandardInvoice', 'Standard Invoice'),
                   ('BasicRefund', 'Basic Refund'),
                   ('StandardRefund', 'Standard Refund')],
        default='BasicInvoice',
        string="Document type"
    )
    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center'
    )
    work_place_id = fields.Many2one(
        string='Work Place',
        comodel_name='work.place'
    )
    business_date = fields.Date(
        string='Business Day'
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        res = super(ResCompany, self).create(vals)
        self.env['product.template'].sudo().create({
            'name': 'Discount Product [{}]'.format(res.name),
            'type': 'service',
            'default_code': 'Discount',
            'invoice_policy': 'order',
            'is_product_discount': True,
            'company_id': res.id
        })
        self.env['product.template'].sudo().create({
            'name': 'Menu [{}]'.format(res.name),
            'type': 'service',
            'default_code': 'Menu',
            'is_product_menu': True,
            'invoice_policy': 'order',
            'company_id': res.id
        })
        self.env['res.partner'].sudo().create({
            'name': 'Generic Client {}'.format(res.name),
            'company_id': res.id,
            'is_generic': True
        })
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    agora_payment_id = fields.Many2one(
        comodel_name='agora.payment.method',
        string="Agora Payment"
    )
    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center'
    )
    business_date = fields.Date(
        string='Business Day'
    )

    def _get_valid_liquidity_accounts(self):
        """"
            Inherit the standard function to add the account related with the center
            This change its important because its need to allow the account change in payment lines
        """
        res = super(AccountPayment, self)._get_valid_liquidity_accounts()
        center_account = self.env['sale.center.account'].search([('sale_center_id', '=', self.sale_center_id.id)], limit=1)
        if center_account:
            _logger.info("Accounts append LIST: {} ------ {}".format(res, center_account.account_id.code))
            res = (*res, (center_account.account_id,))
        return res

    def action_create_batch_payment(self):
        yesterday = date.today() - timedelta(days=1)
        batch_payments = self.create_create_batch_payment_by_date(yesterday)
        return batch_payments

    def create_create_batch_payment_by_date(self, payment_date):
        batch_payment_env = self.env['account.batch.payment']
        if not payment_date:
            payment_date = date.today()
        payments = self.search([('partner_type', '=', 'customer'),
                                ('payment_type', '=', 'inbound'),
                                ('business_date', '=', payment_date)]).filtered(
            lambda l: l.agora_payment_id.allow_batch_payment)
        batch_payments_dict = []
        # Group the payments by agora payment method, journal and payment method
        grouped_lines = self.group_by_agora_payment_and_journal(payments)
        for (agora, journal, method), group in grouped_lines.items():
            business_date = group[0].business_date
            payment_ids = [payment.id for payment in group]
            exist_batch_payment = batch_payment_env.search([('state', '=', 'draft'),
                                                            ('batch_type', '=', method.payment_type),
                                                            ('journal_id', '=', journal.id),
                                                            ('payment_method_id', '=', method.id),
                                                            ('agora_payment_id', '=', agora.id),
                                                            ('business_date', '=', business_date)], limit=1)
            if exist_batch_payment:
                # Get the IDs of the payments already present in the batch payment
                existing_payment_ids = set(exist_batch_payment.payment_ids.ids)
                # Filter out new payment_ids that are not in the batch payment
                new_payment_ids = [pid for pid in payment_ids if pid not in existing_payment_ids]
                if new_payment_ids:
                    exist_batch_payment.write({
                        'payment_ids': [(4, pid) for pid in new_payment_ids]
                    })
            else:
                data_dict = {}
                data_dict.update({
                    'batch_type': method.payment_type,
                    'journal_id': journal.id,
                    'agora_payment_id': agora.id,
                    'payment_ids': [(6, 0, payment_ids)],
                    'business_date': business_date
                })
                batch_payments_dict.append(data_dict)
        batch_payments = batch_payment_env.create(batch_payments_dict)
        return batch_payments

    def create_batch_payments_for_date_range(self, start_date, end_date):
        """
        Create batch payments for each day within the range [start_date, end_date].

        :param start_date: Start date (type date)
        :param end_date: End date (type date)
        :return: Combined list of batch payments created on each date
        """
        all_batch_payments = self.env['account.batch.payment']
        # Make sure the dates are in the correct order
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        current_date = start_date
        while current_date <= end_date:
            batch_payments = self.create_create_batch_payment_by_date(current_date)
            all_batch_payments |= batch_payments
            current_date += timedelta(days=1)
        return all_batch_payments

    def group_by_agora_payment_and_journal(self, payments):
        """
        Group the account payments by agora payment method, journal and payment method.
        :return: A nested dictionary with the structure ((agora_payment), (journal), (payment_method)) = {payment list}
        """
        grouped = defaultdict(list)
        for payment in payments:
            key = (
                payment.agora_payment_id,
                payment.journal_id,
                payment.payment_method_id
            )
            grouped[key].append(payment)
        return grouped


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    validation_counter = fields.Integer(
        string='Counter'
    )


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    agora_payment_id = fields.Many2one(
        comodel_name='agora.payment.method',
        string="Agora Payment"
    )
    business_date = fields.Date(
        string='Business Day'
    )


