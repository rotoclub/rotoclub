# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    analytic_group_id = fields.Many2one(
        comodel_name='account.analytic.group',
        string='Business Center'
    )
    delivery_address = fields.Char(
        string='Delivery Address',
        readonly=True
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.analytic_group_id:
            partner = res.analytic_group_id.partner_id
            if not res.analytic_group_id.partner_id:
                partner = res.analytic_group_id.create_partner().id
            res.analytic_group_id.partner_id = partner
            res.dest_address_id = partner
        return res

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if vals.get('analytic_group_id'):
                partner = rec.analytic_group_id.partner_id
                if not rec.analytic_group_id.partner_id:
                    partner = rec.analytic_group_id.create_partner().id
                rec.analytic_group_id.partner_id = partner
                rec.dest_address_id = partner
        return res

    @api.onchange('analytic_group_id')
    def _generate_address(self):
        delivery_partner = self.analytic_group_id.partner_id
        address = ''
        if delivery_partner:
            street = delivery_partner.street or ''
            zip_code = delivery_partner.zip or ''
            city = delivery_partner.city or ''
            country = delivery_partner.country_id.name or ''
            address = '{} {} {} {}'.format(street, zip_code, city, country)
        self.delivery_address = address

    @api.onchange('analytic_group_id')
    def default_analytic_account(self):
        # FIXME: Change this behavior to make as default if order line is added
        if self.analytic_group_id and self.order_line:
            account_env = self.env['account.analytic.account']
            default_account = account_env.search([('group_id', '=', self.analytic_group_id.id)], limit=1)
            self.order_line.account_analytic_id = default_account
            self.dest_address_id = self.analytic_group_id.partner_id.id

