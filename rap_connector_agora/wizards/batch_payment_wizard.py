# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class BatchPaymentWizard(models.TransientModel):
    _name = 'batch.payment.wizard'
    _description = 'Wizard to select dates to create batch payments'

    date_from = fields.Date(
        string='Date from',
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date to',
        default=fields.Date.context_today
    )
    # company_id = fields.Many2one(
    #     string='Company',
    #     comodel_name='res.company',
    #     default=lambda self: self.env.company
    # )

    def create_batch_payment_for_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('Sorry, the from date cannot be greater than the to date.'))
        self.env['account.payment'].create_batch_payments_for_date_range(self.date_from, self.date_to)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
