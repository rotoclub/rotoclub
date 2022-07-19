# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, date, datetime
from dateutil.relativedelta import relativedelta
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class ServerConfig(models.Model):
    _name = 'server.config'
    _description = 'Server Config'
    _order = 'id desc'

    name = fields.Char('Name', index=True, default='New', required=True)
    title = fields.Char('Title', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', copy=False, check_company=True,  domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="The analytic account related to a Agora API.")
    agora_id = fields.Many2one('api.connection', 'API Connection')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    sale_flow = fields.Selection([
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed Order'),
        ('picking', 'Picking'),
        ('draft_invoice', 'Draft Invoice'),
        ('invoice', 'Invoice'),
        ('payment', 'Payment')], string='Sale Flow', default='quotation', required=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed')
    ], string='Status', index=True, default='open', required=True)
    user_id = fields.Many2one('res.users', 'Sales Person', index=True, required=True, default=lambda self: self.env.user)
    sale_api_ids = fields.One2many('sale.api', 'server_id')
    sale_api_count = fields.Integer(compute='_compute_sale_api_count')
    search_product_by = fields.Selection([
        ('id', 'Id'),
        ('reference', 'Reference'),
        ('sku', 'SKU')], string='Search Product By', default='id')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('server.config', sequence_date=seq_date) or _('New')
        return super(ServerConfig, self).create(vals)

    def action_view_api(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale API',
            'res_model': 'sale.api',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('server_id', '=', self.id)],
            'context': {'default_server_id': self.id}
        }

    def _compute_sale_api_count(self):
        for record in self:
            record.sale_api_count = len(record.sale_api_ids) if record.sale_api_ids else 0


class APIConnection(models.Model):
    _name = 'api.connection'
    _description = 'API Connection'

    name = fields.Char('Name', index=True, default='New')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    url_server = fields.Char('Host')
    check_message = fields.Boolean('Message?', default=False)
    state = fields.Selection([
        ('no_connect', 'Not connected'),
        ('connect', 'Connected')
    ], string='Status', index=True, default='no_connect')
    server_api_key = fields.Char('Api Pass')
    count_api = fields.Integer(compute='_compute_server_config')
    limit_sale_order = fields.Integer('Limit Sale Order')
    limit_origin = fields.Integer('Limit Number')
    default_product_id = fields.Many2one(comodel_name="product.product", string="Default Product")
    last_connection = fields.Datetime('Last Conexion')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('api.connection', sequence_date=seq_date) or _('New')
        return super(APIConnection, self).create(vals)

    # def get_connection(self):
    #     for record in self:
    #         try:
    #             connect = requests.get(record.url_server)
    #             if connect:
#                     if connect.status_code == 200:
#                         return {'status_code': 200, 'message': 'Connection done!'}
#                     else:
#                         return {'status_code': 401, 'message': 'Error: Api Provider'}
#             except Exception as e:
#                 _logger.error(e)
#                 raise UserError(_("Check your configuration, we can't get conect,\n"
#                                   "Here is the error:\n%s") % e)

    def test_connection(self):
        self.state = 'connect'
        self.last_connection = fields.Datetime.now()
        self.check_message = True
        # obj_connection = self.get_connection()
        # if obj_connection:
        #     if obj_connection['status_code'] == 200:
        #         self.state = 'connect'
        #         self.check_message = False
        #     else:
        #         self.check_message = True

    def test_disconnection(self):
        self.state = 'no_connect'
        self.check_message = False

    def _compute_server_config(self):
        server_id = self.env['server.config']
        for record in self:
            record.count_api = len(server_id.search([('agora_id', '=', record.id)]))

    def action_view_server(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Server config',
            'res_model': 'server.config',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('agora_id', '=', self.id)],
            'context': {'default_agora_id': self.id}
        }
