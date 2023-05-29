# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models, api, fields, _


class ImportDataManually(models.TransientModel):
    _name = 'import.agora.data'
    _description = 'Wizard to select Info we need to update from Agora'

    data_model = fields.Selection(
        selection=[('price', 'PriceLists'),
                   ('workplace', 'Work Places'),
                   ('salecenter', 'Sale Centers'),
                   ('category', 'Categories'),
                   ('product', 'Products')],
        required=True,
        default='category',
        string="Import Data"
    )
    instance_id = fields.Many2one(
        string='Instance',
        required=True,
        comodel_name='api.connection'
    )
    company_id = fields.Many2one(
        related='instance_id.company_id'
    )

    def import_agora_data_action(self):
        self.ensure_one()
        if self.data_model == 'price':
            self.instance_id.get_master_pricelist()
        if self.data_model == 'workplace':
            self.instance_id.get_master_work_places()
        if self.data_model == 'salecenter':
            self.instance_id.get_master_sale_center()
        if self.data_model == 'category':
            self.instance_id.get_master_categories()
        if self.data_model == 'product':
            self.instance_id.get_master_products()
