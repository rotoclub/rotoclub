# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class OrderDownloadDate(models.TransientModel):
    _name = 'order.download.date'
    _description = 'Wizard to select the date to be downloaded from Agora'

    tikect_date = fields.Date(
        string='Date'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )

    def get_order_from_agora(self):
        if self.tikect_date > fields.date.today():
            raise ValidationError(_('Sorry a future date can not be select'))
        self.env['api.connection'].download_by_date(self.tikect_date, self.env.company)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
