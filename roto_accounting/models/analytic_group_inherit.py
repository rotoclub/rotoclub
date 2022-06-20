# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking'
    )
