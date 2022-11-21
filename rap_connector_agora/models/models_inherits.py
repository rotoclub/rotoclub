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
    sale_api_origin = fields.Many2one(
        comodel_name='sale.api',
        string='Sale Api',
        ondelete='restrict'
    )


class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    work_place_id = fields.Many2one(
        string='Work Place',
        comodel_name='work.place'
    )


class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    payment_method_id = fields.Many2one(
        comodel_name='account.payment.method',
        string='Payment Method',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal'
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    number = fields.Char(
        string='Number'
    )
    serie = fields.Char(
        string='Serie'
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        res = super(ResCompany, self).create(vals)
        self.env['product.template'].create({
            'name': 'Discount Product [{}]'.format(res.name),
            'type': 'service',
            'default_code': 'Discount',
            'invoice_policy': 'order',
            'is_product_discount': True,
            'company_id': res.id
        })
        return res
