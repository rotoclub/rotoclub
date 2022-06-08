# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Shipping'
    )
    address = fields.Char(
        string='Address'
    )

    street = fields.Char(
        string='Street'
    )
    street2 = fields.Char(
        string='Street2'
    )
    zip = fields.Char(
        string='Zip'
    )
    city = fields.Char(
        string='City'
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string='State'
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country'
    )

    @api.model
    def create(self, vals):
        res = super(AccountAnalyticGroup, self).create(vals)
        if not res.partner_id:
            # To use an specific address its necesary a contact related
            # If not exist should be created
            res.partner_id = res.create_partner().id
        return res

    def create_partner(self):
        """"
        Function to create a Contact related with the actual group
        """
        vals = {
            'name': self.name,
            'company_type': 'company',
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
        }
        partner = self.env['res.partner'].create(vals)
        return partner
