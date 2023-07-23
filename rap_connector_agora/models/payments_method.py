# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AgoraPaymentMethod(models.Model):
    _name = 'agora.payment.method'
    _description = 'Payments coming from Agora'

    name = fields.Char(
        string="Name"
    )
    description = fields.Char(
        string="Description"
    )
    code = fields.Char(
        string="Code"
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company'
    )
