# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ServerConfig(models.Model):
    _name = 'server.config'
    _description = 'Server Config'
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        index=True,
        default='New',
        required=True
    )
    title = fields.Char(
        string='Title',
        required=True
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        copy=False,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a Agora API."
    )
    agora_id = fields.Many2one(
        comodel_name='api.connection',
        string='API Connection'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        atring='Company',
        index=True,
        default=lambda self: self.env.company
    )
    sale_flow = fields.Selection(
        selection=[
            ('quotation', 'Quotation'),
            ('confirmed', 'Confirmed Order'),
            ('picking', 'Picking'),
            ('draft_invoice', 'Draft Invoice'),
            ('invoice', 'Invoice'),
            ('payment', 'Payment')],
        string='Sale Flow',
        default='quotation',
        required=True
    )
    state = fields.Selection(
        selection=[('open', 'Open'),
                   ('closed', 'Closed')],
        string='Status',
        index=True,
        default='open',
        required=True
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Sales Person',
        index=True,
        required=True,
        default=lambda self: self.env.user
    )
    sale_api_ids = fields.One2many(
        string='Api requests',
        comodel_name='sale.api',
        inverse_name='server_id'
    )
    sale_api_count = fields.Integer(
        compute='_compute_sale_api_count'
    )
    search_product_by = fields.Selection(
        selection=[('id', 'Id'),
                   ('reference', 'Reference'),
                   ('sku', 'SKU')],
        string='Search Product By',
        default='id'
    )

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('server.config', sequence_date=seq_date) or _('New')
        return super(ServerConfig, self).create(vals)

    def action_view_api(self):
        """"
        Action for smart button Sale Api
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale API',
            'res_model': 'sale.api',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('server_id', '=', self.id)],
            'context': {'default_server_id': self.id}
        }

    @api.depends('sale_api_ids')
    def _compute_sale_api_count(self):
        for record in self:
            record.sale_api_count = len(record.sale_api_ids)


class APIConnection(models.Model):
    _name = 'api.connection'
    _description = 'API Connection'

    name = fields.Char(
        string='Name',
        index=True,
        default='New'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        index=True,
        default=lambda self: self.env.company
    )
    url_server = fields.Char(
        string='Host'
    )
    check_message = fields.Boolean(
        string='Message?',
        default=False
    )
    state = fields.Selection(
        selection=[
            ('no_connect', 'Not connected'),
            ('connect', 'Connected')],
        string='Status',
        index=True,
        default='no_connect'
    )
    server_api_key = fields.Char(
        string='Api Pass'
    )
    count_api = fields.Integer(
        compute='_compute_server_config'
    )
    limit_sale_order = fields.Integer(
        string='Limit Sale Order'
    )
    limit_origin = fields.Integer(
        string='Limit Number'
    )
    default_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Default Product"
    )
    default_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Default Client"
    )
    last_connection = fields.Datetime(
        string='Last Conexion'
    )

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('api.connection', sequence_date=seq_date) or _('New')
        return super().create(vals)

    def _compute_server_config(self):
        server_id = self.env['server.config']
        for record in self:
            record.count_api = server_id.search_count([('agora_id', '=', record.id)])

    @api.constrains('url_server', 'server_api_key')
    def validate_new_config(self):
        for rec in self:
            if rec.state == 'connect':
                rec.test_connection()

    @staticmethod
    def get_request(url, end_point, token, params):
        """"
        Function to make GET request
        Params:
            url: Host
            endpoint: Endpoint to complement the Host
            token: Token for authentication. Always Required
            Params: Aditional Filters
            Example: (http://localhost:8984/api, '/export-master', 'U22RgEi*o6g!', {'filter': 'Series'})
        Return: Request Response if went OK(200), False if went sommething wrong(!200), Exception if there was an error
        """
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'Content-Type': 'application/json; charset=utf-8',
            'Api-Token': token
        }
        url = '{}{}'.format(url, end_point)
        try:
            connect = requests.get(url=url, headers=headers, params=params)
            if connect:
                if connect.status_code == 200:
                    return connect
                else:
                    return False
        except Exception as e:
            _logger.error(e)
            raise UserError(_("Check your configuration, we can't get conect,\n"
                              "Here is the error:\n%s") % e)

    def test_connection(self):
        """"
        Function to verify the Api connection config
        Make a request to an endpoint to verify the response and update connection status
        Set state to Connect
        """
        self.ensure_one
        self.check_message = True
        params = {
            'filter': 'Series'
        }
        obj_connection = self.get_request(self.url_server, '/export-master', self.server_api_key, params)
        if obj_connection:
            self.state = 'connect'
            self.check_message = False
            self.last_connection = fields.Datetime.now()
        else:
            self.check_message = True
            self.state = 'no_connect'

    def test_disconnection(self):
        """"
         Function to set the connection status to No-Connect
        """
        self.state = 'no_connect'
        self.check_message = False

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

    def _agora_sync(self):
        """"
        Main Function to make the call to all the functions need it to complete the sync
        """
        conections = self.search([('state', '=', 'connect')])
        for record in conections:
            export_endpoint = '/export-master'
            record.get_master_sale_center(export_endpoint)
            record.get_master_categories(export_endpoint)
            record.get_master_products(export_endpoint)

    def get_master_products(self, endpoint):
        """"
        Function to get Products from Agora
        Generate Product.template record for each Agora Product that not exist in Odoo
        """
        products_env = self.env['product.template']
        params = {
            'filter': 'Products'
        }
        products = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if products and products.json().get('Products'):
            json_products = products.json().get('Products')
            for record in json_products:
                existing_prod = products_env.search([('agora_id', '=', record.get('Id')),
                                                    ('active', 'in', [True, False])])
                values_dict = self.get_product_dict()
                if record.get('DeletionDate') and existing_prod.active:
                    # If the product have being deleted in Agora Should be Archive in Odoo
                    existing_prod.active = False
                    continue
                prices = record.get('Prices')
                if not existing_prod:
                    category_id = self.env['product.category'].search(
                        [('agora_id', '=', record.get('FamilyId'))], limit=1)
                    values_dict.update({
                        'name': record.get('Name'),
                        'agora_id': record.get('Id'),
                        'color': record.get('Color'),
                        'categ_id': category_id.id,
                        'standard_price': record.get('CostPrice'),
                    })
                    product = products_env.create(values_dict)
                else:
                    product = existing_prod
                if record.get('DeletionDate'):
                    product.update({'active': False})
                else:
                    product.update({'active': True})
                self.generate_product_prices(product, prices)

    def generate_product_prices(self, product, prices):
        """"
        Function to generate or update the product prices
        Params:
            product: Product to be updated
            Prices: Dict of prices related with the current product
        """
        pricelist_env = self.env['product.pricelist']
        pricelist_item_env = self.env['product.pricelist.item']
        sale_centers = self.env['sale.center'].search([])
        if prices:
            for center in sale_centers:
                pricelist_id = pricelist_env.search([('sale_center_id', '=', center.id)])
                prod_prices = list(filter(lambda l: l.get('PriceListId') == int(center.agora_id), prices))
                if prod_prices and product:
                    agora_id = int(prod_prices[0].get('PriceListId'))
                    exist = pricelist_item_env.search([('product_tmpl_id', '=', product.id),
                                                       ('date_end', '=', False),
                                                       ('pricelist_id.sale_center_id.agora_id', '=', agora_id)])
                    if not exist:
                        # create new pricelist
                        data = {
                            'pricelist_id': pricelist_id.id,
                            'product_tmpl_id': product.id,
                            'fixed_price': prod_prices[0].get('MainPrice'),
                            'date_start': fields.Datetime.now(),
                        }
                        pricelist_item_env.create(data)
                    elif exist.filtered(lambda pl: pl.fixed_price != prod_prices[0].get('MainPrice')):
                        # update existing pricelist
                        # The existing record will keep the old price but will be closed behind the end_date
                        # New price will be created with start date today. In order to keep the historical prices
                        uptdata = {
                            'date_end': fields.Datetime.now(),
                        }
                        exist[0].update(uptdata)
                        # create new price list
                        data = {
                            'pricelist_id': pricelist_id.id,
                            'product_tmpl_id': product.id,
                            'fixed_price': prod_prices[0].get('MainPrice'),
                            'date_start': fields.Datetime.now(),
                        }
                        pricelist_item_env.create(data)

    def get_master_categories(self, endpoint):
        """"
        Function to get Categories from Agora
        Generate a Product.category record for each Agora Family that not exist in Odoo
        """
        prod_cat_env = self.env['product.category']
        params = {
            'filter': 'Families'
        }
        categories = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if categories and categories.json().get('Families'):
            json_categories = categories.json().get('Families')
            for record in json_categories:
                existing_cat = prod_cat_env.search([('agora_id', '=', record.get('Id'))])
                values_dict = self.get_categories_dict()
                if record.get('DeletionDate') and existing_cat:
                    existing_cat.unlink()
                    continue
                if not existing_cat and not record.get('DeletionDate'):
                    values_dict.update({
                        'name': record.get('Name'),
                        'complete_name': record.get('Name'),
                        'agora_id': record.get('Id'),
                        'color': record.get('Color')
                    })
                    prod_cat_env.create(values_dict)

    def get_master_sale_center(self, endpoint):
        """"
        Function to get de Sales centers
        This function needs the previous creation of the Default Price List
        """
        sale_center_env = self.env['sale.center']
        params = {
            'filter': 'SaleCenters'
        }
        centers = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if centers and centers.json().get('SaleCenters'):
            json_centers = centers.json().get('SaleCenters')
            for record in json_centers:
                existing_cent = sale_center_env.search([('agora_id', '=', record.get('Id'))])
                if not existing_cent:
                    values_dict = self.get_sale_center_dict()
                    values_dict.update({
                        'name': record.get('Name'),
                        'button_text': record.get('ButtonText'),
                        'agora_id': record.get('Id'),
                        'color': record.get('Color')
                    })
                    sale_center_env.create(values_dict)

    def get_product_dict(self):
        """"
        Return: Clean Product dictionary
        """
        values = {
            'name': '',
            'company_id': self.company_id.id
        }
        return values

    def get_categories_dict(self):
        """"
        Return: Clean Category dictionary
        """
        values = {
            'name': '',
            'complete_name': '',
            'agora_id': '',
            'color': '',
            'company_id': self.company_id.id
        }
        return values

    def get_sale_center_dict(self):
        """"
        Return: Clean Sale Center dictionary
        """
        values = {
            'name': '',
            'button_text': '',
            'agora_id': '',
            'color': '',
            'company_id': self.company_id.id
        }
        return values
