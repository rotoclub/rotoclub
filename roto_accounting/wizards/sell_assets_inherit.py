# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models,fields,api


class AssetSell(models.TransientModel):
    _inherit = "account.asset.sell"

    disable_reason = fields.Char(
        string="Disable reason"
    )

    def do_action(self):
        res = super(AssetSell, self).do_action()
        dis_reason = self.env['account.asset']
        dis_reason.browse(self._context.get("active_ids")).update({'disable_reason': self.disable_reason})
        return res
