# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo import api
from odoo import fields

class AccounAssetInherit(models.Model):
    _inherit = "account.asset"

    disable_reason = fields.Char(
        string="Disable reason"
    )