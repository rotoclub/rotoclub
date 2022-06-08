# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def unlink(self):
        account_group_env = self.env['account.analytic.group']
        for rec in self:
            group = account_group_env.search([('partner_id', '=', rec.id)], limit=1)
            if group:
                raise ValidationError(_('Sorry!! This Contact can not be deleted because its'
                                        ' related with the Analytic Group: {}').format(rec.name))
        return super().unlink()
