# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ProductsAddings(models.Model):
    _name = 'product.addings'
    _description = 'Model for adding grouping'

    name = fields.Char(
        string='Group Name'
    )
    button_tex = fields.Char(
        string='Button Text'
    )
    min_addings = fields.Integer(
        string='Minimum'
    )
    max_addings = fields.Integer(
        string='Maximum'
    )
    preparation = fields.Selection(
        selection=[('FromMain', 'Use main Product preparation'),
                   ('FromAddin', 'Use adding Product preparation')]
    )
    product_addings_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_template_addings_group_rel',
        column1='product_id',
        column2='group_id',
        string="Addins Group",
        check_company=True,
        copy=False
    )
    company_id = fields.Many2one(
        string='Company',
    )
