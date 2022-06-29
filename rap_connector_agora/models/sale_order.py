# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_api_origin = fields.Many2one('sale.api', string='Sale Api', ondelete='restrict')
    origin = fields.Char('Origin', related='sale_api_origin.origin')
