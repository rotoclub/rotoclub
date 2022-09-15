# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class PreparationOrder(models.Model):
    _name = 'preparation.order'
    _description = 'Preparation Order'
    _check_company_auto = True

    name = fields.Char(
        string='Name'
    )
    agora_id = fields.Integer(
        'Agora ID',
        copy=False
    )
    priority = fields.Integer(
        string='Priority'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
