# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_addins = fields.Boolean(
        string='Is Addins'
    )
    is_invitation = fields.Boolean(
        string='Invitation'
    )
    index = fields.Integer(
        string='Index',
        help='Number of the line coming from Agora to be identify'
    )
