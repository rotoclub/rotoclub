# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    Migration to update some configs
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_taxes_price_include(env)


def update_taxes_price_include(env):
    """
    Method that change to true all the taxes price_include field
    """
    taxes = env['account.tax'].search([])
    for tax in taxes:
        tax.price_include = True
