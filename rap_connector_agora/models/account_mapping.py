# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountingMapping(models.Model):
    _name = 'account.mapping'
    _rec_name = 'instance_id'
    _description = 'Configuration to mapp account and journals'

    instance_id = fields.Many2one(
        comodel_name='api.connection',
        string='Agora Instance'
    )
    agora_payment_ids = fields.One2many(
        comodel_name='payment.method.account',
        inverse_name='account_mapping_id',
        string='Payment Methods/Account'
    )
    invoice_journal_ids = fields.One2many(
        comodel_name='invoice.type.journal',
        inverse_name='account_mapping_id',
        string='Journal/Invoice Type'
    )
    company_id = fields.Many2one(
        related='instance_id.company_id'
    )

    @api.constrains('instance_id')
    def validate_invoice_type_repeated(self):
        for rec in self:
            repeated = rec.search_count([('instance_id', '=', rec.instance_id.id)])
            if repeated > 1:
                raise ValidationError("Already exist a configuration for the selected Account Mapping")


class InvoiceTypeJournal(models.Model):
    _name = 'invoice.type.journal'
    _description = 'Depending the Agora Invoice Type will have a journal associated'

    invoice_type = fields.Selection(
        selection=[('simplified', 'Simplified'),
                   ('regular', 'Regular')],
        required=True,
        string="Invoice type"
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
        string="Journal"
    )
    account_mapping_id = fields.Many2one(
        comodel_name="account.mapping",
        required=True,
        string="Account Mapping"
    )

    @api.constrains('invoice_type')
    def validate_invoice_type_repeated(self):
        for rec in self:
            repeated = rec.search_count([('invoice_type', '=', rec.invoice_type),
                                         ('account_mapping_id', '=', rec.account_mapping_id.id)])
            if repeated > 1:
                raise ValidationError("Already exist a configuration for the selected Invoice Type")


class PaymentMethodAccount(models.Model):
    _name = 'payment.method.account'

    payment_method_id = fields.Many2one(
        comodel_name='agora.payment.method',
        required=True,
        string="Payment method"
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        required=True,
        string="Account"
    )
    account_mapping_id = fields.Many2one(
        comodel_name="account.mapping",
        required=True,
        string="Account Mapping"
    )

    @api.constrains('payment_method_id')
    def validate_invoice_type_repeated(self):
        for rec in self:
            repeated = rec.search_count([('payment_method_id', '=', rec.payment_method_id.id),
                                         ('account_mapping_id', '=', rec.account_mapping_id.id)])
            if repeated > 1:
                raise ValidationError("Already exist a configuration for the selected Payment Method")
