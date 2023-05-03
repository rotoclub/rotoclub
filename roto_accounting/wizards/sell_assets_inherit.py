# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models,fields,api


class assetSell(models.TransientModel):
    _inherit = "account.asset.sell"

    disable_reason = fields.Char(
        string="Disable reason"
    )

    def do_action(self):
        dis_reas = self.env['account.asset']
        dis_reas.browse(self._context.get("active_ids")).update({'disable_reason': self.disable_reason})
        invoice_line = self.env[
            'account.move.line'] if self.action == 'dispose' else self.invoice_line_id or self.invoice_id.invoice_line_ids
        return self.asset_id.set_to_close(invoice_line_id=invoice_line, date=invoice_line.move_id.invoice_date)
