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
    invoice_journal_ids = fields.One2many(
        comodel_name='invoice.type.journal',
        inverse_name='account_mapping_id',
        string='Journal/Invoice Type'
    )
    company_id = fields.Many2one(
        related='instance_id.company_id',
        store=True
    )
    center_account_ids = fields.One2many(
        comodel_name='sale.center.account',
        inverse_name='account_mapping_id',
        string='Sale Center/Accounts'
    )
    tips_config_ids = fields.One2many(
        comodel_name='tips.config',
        inverse_name='account_mapping_id',
        string='Tips Setting',
        required=True
    )
    tip_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Tips Journal"
    )
    inbound_payment_method_id = fields.Many2one(
        comodel_name='account.payment.method',
        string="Debit Method",
        domain=[('payment_type', '=', 'inbound')],
        help="Means of payment for collecting money. Odoo modules offer various"
             "payments handling facilities, but you can always use the 'Manual'"
             "payment method in order to manage payments outside of the"
             "software."
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
        selection=[('basic', 'Basic'),
                   ('standard', 'Standard')],
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
    company_id = fields.Many2one(
        related='account_mapping_id.company_id',
        store=True
    )

    @api.constrains('invoice_type')
    def validate_invoice_type_repeated(self):
        for rec in self:
            repeated = rec.search_count([('invoice_type', '=', rec.invoice_type),
                                         ('account_mapping_id', '=', rec.account_mapping_id.id)])
            if repeated > 1:
                raise ValidationError("Already exist a configuration for the selected Invoice Type")


class SaleCenterAccount(models.Model):
    _name = 'sale.center.account'
    _description = 'Relation of Sale Center with Accounts'

    payment_method_id = fields.Many2one(
        string='Agora Payment Method',
        comodel_name='agora.payment.method'
    )
    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center',
        required=True
    )
    account_id = fields.Many2one(
        string='Account',
        comodel_name='account.account',
        required=True
    )
    counterpart_account_id = fields.Many2one(
        string='Counterpart Account',
        comodel_name='account.account',
        required=True
    )
    account_mapping_id = fields.Many2one(
        comodel_name="account.mapping",
        string="Account Mapping"
    )
    company_id = fields.Many2one(
        related='account_mapping_id.company_id',
        store=True
    )

    @api.constrains('payment_method_id', 'sale_center_id')
    def model_validation(self):
        for rec in self:
            duplicated = rec.search_count([
                ('sale_center_id', '=', rec.sale_center_id.id),
                ('payment_method_id', '=', rec.payment_method_id.id)])
            if duplicated > 1:
                raise ValidationError(_("There is a duplicity of Sale Center Configuration"))


class TipsConfig(models.Model):
    _name = 'tips.config'
    _description = 'Configurations needed for tips'

    sale_center_id = fields.Many2one(
        string='Sale Center',
        comodel_name='sale.center',
        required=True
    )
    account_id = fields.Many2one(
        string='Account',
        comodel_name='account.account',
        required=True
    )
    counterpart_account_id = fields.Many2one(
        string='Counterpart Account',
        comodel_name='account.account',
        required=True
    )
    account_mapping_id = fields.Many2one(
        comodel_name="account.mapping",
        string="Account Mapping"
    )
    company_id = fields.Many2one(
        related='account_mapping_id.company_id',
        store=True
    )

    _sql_constraints = [('unique_company', 'unique(company_id,sale_center_id)',
                         "Already exist a configuration for this company and Sale Center! Only one its allowed")]
