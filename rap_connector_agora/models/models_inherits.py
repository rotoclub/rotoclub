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
                   ('StandardInvoice', 'Standard Invoice')],
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

    def _get_valid_liquidity_accounts(self):
        """"
            Inherit the standard function to add the account related with the center
            This change its important because its need to allow the account change in payment lines
        """
        res = super(AccountPayment, self)._get_valid_liquidity_accounts()
        center_account = self.env['sale.center.account'].search([('sale_center_id', '=', self.sale_center_id.id)], limit=1)
        if center_account:
            res = res + (center_account.account_id,)
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    validation_counter = fields.Integer(
        string='Counter'
    )
