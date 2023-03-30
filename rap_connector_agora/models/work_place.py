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
    analytic_group_id = fields.Many2one(
        string='Analytic Group',
        comodel_name='account.analytic.group',
        compute='_compute_analytic_group'
    )

    def _compute_analytic_group(self):
        group_env = self.env['account.analytic.group']
        for rec in self:
            a_group = group_env.search([('work_place_id', '=', rec.id)], limit=1)
            rec.analytic_group_id = a_group.id

