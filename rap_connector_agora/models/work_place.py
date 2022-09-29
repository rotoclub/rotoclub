# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class WorkPlace(models.Model):
    _name = 'work.place'
    _description = 'Work Place'

    agora_id = fields.Integer(
        string='Agora ID'
    )
    name = fields.Char(
        string='Name'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company'
    )
