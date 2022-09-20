# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AgoraTax(models.Model):
    _name = 'agora.tax'
    _description = 'Agora Taxes to match records with odoo'

    name = fields.Char(
        string='Tax Name'
    )
    agora_id = fields.Integer(
        'Agora ID',
        copy=False
    )
    account_tax_id = fields.Many2one(
        string='Tax',
        comodel_name='account.tax'
    )
    charge_rate = fields.Float(
        string='Charge Rate'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
