# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    parent_id = fields.Many2one(
        string='Parent Product',
        comodel_name='product.template'
    )
    color = fields.Char(
        string='Color'
    )
    button_text = fields.Char(
        string='Button Text'
    )
    sync_status = fields.Selection(
        selection=[('done', 'Completed'),
                   ('new', 'New'),
                   ('modifiyed', 'Modifiyed'),
                   ('error', 'Error')],
        default='new'
    )
    preparation_id = fields.Many2one(
        string='Preparation Type',
        comodel_name='preparation.type'
    )
    preparation_order_id = fields.Many2one(
        string='Preparation Order',
        comodel_name='preparation.order'
    )
    agora_tax_id = fields.Many2one(
        string='Agora Tax',
        comodel_name='agora.tax'
    )
    is_saleable_as_main = fields.Boolean(
        string='Saleable as Main',
        help='Allow Sale as main product.'
    )
    is_saleable_as_adding = fields.Boolean(
        string='Saleable as Adding',
        help='Allow Sale as adding product of other product.'
    )
    is_sold_by_weight = fields.Boolean(
        string='Is Sold by Weight',
        help='Allow sold the product by Weight.'
    )
    ask_preparation_notes = fields.Boolean(
        string='Need Preparation Note',
        help='Ask automatically for preparation notes'
    )
    ask_for_addings = fields.Boolean(
        string='Need Addings',
        help='Ask automatically for addings'
    )
    print_zero = fields.Boolean(
        string='Print Price Zero',
        help='Do not print the ticket when price is equal zero'
    )
    sale_format = fields.Integer(
        'Sale Format'
    )

    @api.constrains(lambda self: self.get_onchange_fields())
    def verify_changed_values(self):
        is_first_charge = self.env.context.get('first_charge')
        for rec in self:
            if not is_first_charge and rec.sync_status != 'new':
                rec.sync_status = 'modifiyed'

    @staticmethod
    def get_onchange_fields():
        return ['color', 'button_text', 'preparation_id', 'preparation_order_id', 'agora_tax_id', 'is_saleable_as_main',
                'is_saleable_as_adding', 'is_sold_by_weight', 'ask_preparation_notes', 'ask_for_addings', 'print_zero']

    def action_sent_agora(self):
        active_ids = self._context.get('active_ids')
        products = self.env['product.template'].search([('id', 'in', active_ids)])
        print('sent to agora')