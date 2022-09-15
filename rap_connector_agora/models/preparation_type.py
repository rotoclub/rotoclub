# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class PreparationType(models.Model):
    _name = 'preparation.type'
    _description = 'Preparations Type'
    _check_company_auto = True

    name = fields.Char(
        string='Preparation Type'
    )
    agora_id = fields.Integer(
        'Agora ID',
        copy=False
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
