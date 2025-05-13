# Copyright 2025-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    es_embargado = fields.Boolean(
        string='Embargado',
        default=False,
        help='Indica si el partner está embargado'
    )
