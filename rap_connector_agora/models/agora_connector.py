# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
from odoo.exceptions import ValidationError
from dateutil import parser
from datetime import datetime
from itertools import groupby
import json

requests.packages.urllib3.util.connection.HAS_IPV6 = False


_logger = logging.getLogger(__name__)


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
    # ---------------------
    #     Config fields
    # ---------------------
    sale_flow = fields.Selection(
        selection=[
            ('sale', 'Sale'),
            ('draft_invoice', 'Draft Invoice'),
            ('invoice', 'Invoice'),
            ('payment', 'Payment')],
        string='Sale Flow',
        default='payment'
    )
    is_date_from_invoice = fields.Boolean(
        string='Date from Invoice',
        default=True
    )
    last_connection = fields.Datetime(
        string='Last Connection'
    )
    last_product_id = fields.Integer(
        string='Last Product ID'
    )
    last_format_id = fields.Integer(
        string='Last Format ID'
    )

    _sql_constraints = [('unique_name', 'unique(name)',
                         "Already exist an Instance with the same Name, to avoid confusions please select a New Name")]

    def write(self, vals):
        for rec in self:
            if vals.get('state') == 'connect':
                duplicated = rec.search_count([('company_id', '=', rec.company_id.id), ('state', '=', 'connect')])
                if duplicated:
                    raise ValidationError(_('Sorry!! Exist another API connection for the same company'
                                            ' already connected'))
        return super().write(vals)

    @api.constrains('url_server', 'server_api_key')
    def validate_new_config(self):
        for rec in self:
            if rec.state == 'connect':
                rec.test_connection()

# -----------------------------------------------------------------------------------------------------
# ----------------------------------------- MAIN REQUESTS ---------------------------------------------
# -----------------------------------------------------------------------------------------------------
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
            connect = requests.get(url=url, headers=headers, params=params, verify=False)
            if connect:
                if connect.status_code == 200:
                    return connect
                else:
                    raise ValidationError(_("Sorry!! There was an error in the connection"))
            else:
                raise ValidationError(_("Sorry!! The connection couldnt be completed. Probably the Agora server"
                                        " it's not available. Please try again in a few minutes."))
        except Exception as e:
            _logger.error(e)
            raise UserError(_('{}'.format(e)))

    @staticmethod
    def post_request(url, end_point, token, json):
        """"
        Function to make POST request
        Params:
            url: Host
            endpoint: Endpoint to complement the Host
            token: Token for authentication. Always Required
            Json: Data
            Example: (http://localhost:8984/api, '/import', 'U22RgEi*o6g!', {'filter': 'Series'})
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
            connect = requests.post(url=url, headers=headers, json=json, verify=False)
            if connect is not None:
                if connect.status_code == 200:
                    return connect, connect.content
                else:
                    return False, connect.content
        except Exception as e:
            _logger.error(e)
            return False, connect.content

# -----------------------------------------------------------------------------------------------------
# ------------------------------ ACTIVATE/DEACTIVATE CONNECTIONS --------------------------------------
# -----------------------------------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------------------------------
# -------------------- GET REQUEST TO GENERATE MASTERS DATA IN ODOO -----------------------------------
# -----------------------------------------------------------------------------------------------------

    def get_master_products(self):
        """"
        Function to get Products from Agora
        Generate Product.template record for each Agora Product that not exist in Odoo
        """
        endpoint = '/export-master'
        self_prod_creation = self.with_context({'first_charge': True})
        products_env = self_prod_creation.env['product.template']
        params = {
            'filter': 'Products'
        }
        products = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        addings = []
        if products and products.json().get('Products'):
            json_products = products.json().get('Products')
            for record in json_products:
                existing_prod = products_env.search([('agora_id', '=', record.get('Id')),
                                                     ('active', 'in', [True, False]),
                                                     ('company_id', '=', self.company_id.id)], limit=1)
                if record.get('DeletionDate') and existing_prod.active:
                    # If the product have being deleted in Agora Should be Archive in Odoo
                    existing_prod.active = False
                    continue
                if not existing_prod:
                    # If product dont exist, Should be created
                    values_dict = {}
                    product = self.create_product(record, values_dict, False)
                    addings.append(product.get('addings'))
                    if record.get('AdditionalSaleFormats'):
                        # If product have formats, should be created as products
                        formats = self.generate_sale_formats(product.get('product'), record)
                        for form in formats:
                            addings.append(form)
                else:
                    product = existing_prod
                if record.get('DeletionDate'):
                    product.update({'active': False})
                else:
                    product.update({'active': True})
            self.create_addings(addings)

    def create_addings(self, addings):
        """"
        Function to create the relation of the product with the correspondent addins
        """
        self_prod_creation = self.with_context({'first_charge': True})
        product_env = self_prod_creation.env['product.template']
        for record in addings:
            if record.get('addins'):
                add = []
                if record.get('is_format'):
                    product = product_env.search([('sale_format', '=', record.get('prod')),
                                                  ('company_id', '=', self.company_id.id)])
                else:
                    product = product_env.search([('base_format_id', '=', record.get('prod')),
                                                  ('company_id', '=', self.company_id.id)])
                for addin in record.get('addins'):
                    prod_addins = product_env.search(['|', ('sale_format', '=', addin.get('AddinSaleFormatId')),
                                                      ('base_format_id', '=',  addin.get('AddinSaleFormatId')),
                                                      ('company_id', '=', self.company_id.id)], limit=1)
                    add.append(prod_addins.id)
                if product and prod_addins:
                    product.product_addins_ids = [(6, 0, add)]

    def create_product(self, record, values_dict, is_format):
        """"
        Function to create a product from a provided json record
        """
        self_prod_creation = self.with_context({'first_charge': True})
        products_env = self_prod_creation.env['product.template']
        category_id = self.env['product.category'].search([('agora_id', '=', record.get('FamilyId')),
                                                           ('company_id', '=', self.company_id.id)], limit=1).id
        if values_dict.get('categ_id'):
            category_id = values_dict.get('categ_id')

        taxes_id = self.env['agora.tax'].search([('agora_id', '=', record.get('VatId')),
                                                 ('company_id', '=', self.company_id.id)], limit=1).account_tax_id.ids
        if values_dict.get('taxes_id'):
            taxes_id = values_dict.get('taxes_id')
        prep_type_id = self.env['preparation.type'].search([('agora_id', '=', record.get('PreparationTypeId')),
                                                            ('company_id', '=', self.company_id.id)], limit=1)
        prep_order_id = self.env['preparation.order'].search([('agora_id', '=', record.get('PreparationOrderId')),
                                                              ('company_id', '=', self.company_id.id)], limit=1)
        values_dict.update({
            'name': record.get('Name'),
            'agora_id':  record.get('Id') if not ('sale_format' in values_dict) else '',
            'sale_format': record.get('Id') if ('sale_format' in values_dict) else '',
            'base_format_id': record.get('BaseSaleFormatId'),
            'color': record.get('Color'),
            'standard_price': record.get('CostPrice'),
            'list_price': 0.0,
            'sync_status': 'done',
            'ratio': record.get('Ratio'),
            'button_text': record.get('ButtonText'),
            'detailed_type': values_dict.get('detailed_type') if 'detailed_type' in values_dict else 'product',
            'preparation_id': values_dict.get('preparation_id') if 'preparation_id' in values_dict else prep_type_id.id,
            'preparation_order_id': values_dict.get('preparation_order_id')
                                    if 'preparation_order_id' in values_dict else prep_order_id.id,
            'taxes_id': [(6, 0, taxes_id)],
            'is_saleable_as_main': record.get('SaleableAsMain'),
            'is_saleable_as_adding': record.get('SaleableAsAddin'),
            'is_sold_by_weight': record.get('IsSoldByWeight'),
            'ask_preparation_notes': record.get('AskForPreparationNotes'),
            'ask_for_addings': record.get('AskForAddins'),
            'print_zero': not record.get('PrintWhenPriceIsZero'),
            'company_id': self.company_id.id,
            'responsible_id': False
        })
        if category_id:
            values_dict.update({'categ_id': category_id})
        product = products_env.create(values_dict)
        _logger.info("Product created ==> {}".format(product.name))
        prices = record.get('Prices')
        addings = {'is_format': is_format, 'prod': product.base_format_id, 'addins': record.get('Addins')}
        if product.parent_id:
            addings = {'is_format': is_format, 'prod': product.sale_format, 'addins': record.get('Addins')}
        self.generate_product_prices(product, prices)
        return {'product': product, 'addings': addings}

    def generate_sale_formats(self, product, record):
        mrp_bom_env = self.env['mrp.bom']
        mrp_bom_line_env = self.env['mrp.bom.line']
        addings = []
        for format in record.get('AdditionalSaleFormats'):
            values = {
                'parent_id': product.id,
                'detailed_type': 'consu',
                'sale_format': True,
                'purchase_ok': False,
                'preparation_id': product.preparation_id.id,
                'categ_id': product.categ_id.id,
                'taxes_id': product.taxes_id.ids,
                'preparation_order_id': product.preparation_order_id.id
            }
            if format.get('DeletionDate'):
                values.update({'active': False})
            product_create = self.create_product(format, values, True)
            sub_product = product_create.get('product')
            material_list = mrp_bom_env.create({
                'product_tmpl_id': sub_product.id,
                'type': 'phantom',
                'company_id': self.company_id.id
            })
            product_product = self.env['product.product'].search(
                [('product_tmpl_id', '=', sub_product.parent_id.id)], limit=1)
            mrp_bom_line_env.create({
                'bom_id': material_list.id,
                'product_id': product_product.id,
                'product_qty': format.get('Ratio'),
                'company_id': self.company_id.id
            })
            addings.append(product_create.get('addings'))
            _logger.info("Format ==> {} ---- Parent : {}".format(sub_product.name, product.name))
        return addings

    def generate_product_prices(self, product, prices):
        """"
        Function to generate or update the product prices
        Params:
            product: Product to be updated
            Prices: Dict of prices related with the current product
        """
        self_price_creation = self.with_context({'first_charge': True})
        pricelist_item_env = self_price_creation.env['product.pricelist.item']
        price_list_env = self.env['product.pricelist']
        if prices:
            for price in prices:
                price_list = price_list_env.search([('agora_id', '=', price.get('PriceListId')),
                                                    ('company_id', '=', self.company_id.id)])
                if product:
                    exist = pricelist_item_env.search([('product_tmpl_id', '=', product.id),
                                                       ('date_end', '=', False),
                                                       ('pricelist_id.agora_id', '=', price.get('PriceListId'))],
                                                      limit=1)
                    if not exist:
                        # create new pricelist
                        data = {
                            'pricelist_id': price_list.id,
                            'product_tmpl_id': product.id,
                            'fixed_price': price.get('MainPrice'),
                            'addin_price': price.get('AddinPrice'),
                            'menuitem_price': price.get('MenuItemPrice'),
                        }
                        pricelist_item_env.create(data)
                    else:
                        # create values in the existing pricelist
                        upt_data = {
                            'fixed_price': price.get('MainPrice'),
                            'addin_price': price.get('AddinPrice'),
                            'menuitem_price': price.get('MenuItemPrice'),
                        }
                        exist.update(upt_data)

    def get_master_categories(self):
        """"
        Function to get Categories from Agora
        Generate a Product.category record for each Agora Family that not exist in Odoo
        """
        endpoint = '/export-master'
        prod_cat_env = self.env['product.category']
        params = {
            'filter': 'Families'
        }
        categories = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if categories and categories.json().get('Families'):
            json_categories = categories.json().get('Families')
            for record in json_categories:
                existing_cat = prod_cat_env.search([('agora_id', '=', record.get('Id')),
                                                    ('company_id', '=', self.company_id.id)])
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

    def get_master_sale_center(self):
        """"
        Function to get de Sales centers
        This function needs the previous creation of the Default Price List
        """
        endpoint = '/export-master'
        sale_center_env = self.env['sale.center']
        pricelist_env = self.env['product.pricelist']
        location_env = self.env['sale.location']
        params = {
            'filter': 'SaleCenters'
        }
        centers = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if centers and centers.json().get('SaleCenters'):
            json_centers = centers.json().get('SaleCenters')
            for record in json_centers:
                existing_cent = sale_center_env.search([('agora_id', '=', record.get('Id')),
                                                        ('company_id', '=', self.company_id.id)])
                if not existing_cent:
                    values_dict = self.get_sale_center_dict()
                    pric_list = pricelist_env.search([('agora_id', '=', int(record.get('PriceListId'))),
                                                      ('company_id', '=', self.company_id.id)], limit=1)
                    values_dict.update({
                        'name': record.get('Name'),
                        'button_text': record.get('ButtonText'),
                        'agora_id': int(record.get('Id')),
                        'pricelist_id': pric_list.id,
                        'color': record.get('Color')
                    })
                    existing_cent = sale_center_env.create(values_dict)
                for location in record.get('SaleLocations'):
                    exist_loc = location_env.search([('name', '=', location.get('Name')),
                                                     ('center_id', '=', existing_cent.id),
                                                     ('company_id', '=', self.company_id.id)])
                    if not exist_loc:
                        location_env.create({
                            'name': location.get('Name'),
                            'center_id': existing_cent.id,
                            'company_id': self.company_id.id
                        })

    def get_master_pricelist(self):
        """"
        Function to get de PriceList
        """
        pricelist_env = self.env['product.pricelist']
        endpoint = '/export-master'
        params = {
            'filter': 'PriceLists'
        }
        prices = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if prices and prices.json().get('PriceLists'):
            json_centers = prices.json().get('PriceLists')
            for record in json_centers:
                existing_cent = pricelist_env.search([('agora_id', '=', int(record.get('Id'))),
                                                      ('company_id', '=', self.company_id.id)])
                if not existing_cent:
                    values_dict = {}
                    values_dict.update({
                        'name': record.get('Name'),
                        'agora_id': int(record.get('Id')),
                        'company_id': self.company_id.id
                    })
                    pricelist_env.create(values_dict)

    def get_master_work_places(self):
        """"
        Function to get Work Places
        """
        endpoint = '/export-master'
        work_place_env = self.env['work.place']
        params = {
            'filter': 'WorkplacesSummary'
        }
        prices = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if prices and prices.json().get('WorkplacesSummary'):
            json_centers = prices.json().get('WorkplacesSummary')
            for record in json_centers:
                existing_cent = work_place_env.search([('agora_id', '=', int(record.get('Id'))),
                                                      ('company_id', '=', self.company_id.id)])
                if not existing_cent:
                    values_dict = {}
                    values_dict.update({
                        'name': record.get('Name'),
                        'agora_id': int(record.get('Id')),
                        'company_id': self.company_id.id
                    })
                    work_place_env.create(values_dict)

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

# -----------------------------------------------------------------------------------------------------
# -------------------- POST REQUEST TO GENERATE PRODUCT DATA IN AGORA ---------------------------------
# -----------------------------------------------------------------------------------------------------

    def get_related_connection(self, record):
        """
        Function to get the right connection for a record
        The objective of this function is to be sure the data is going to the rigth Agora Instance
        """
        connection = False
        if record.company_id:
            company = record.company_id
            connection = self.env['api.connection'].search([('company_id', '=', company.id), ('state', '=', 'connect')])
        return connection

    def verify_active_companies(self):
        """
        Function to verify if there are more than one company active
        Will be useful to be consider during the sync operation
        """
        if len(self.env.companies) > 1:
            raise ValidationError(_('Please select only one company to make this operation.'))

    def _get_last_ids(self):
        """"
        Function to update the last Format_id and Product_id at the api_connection
        This IDs will be used to assign new agora_id when a product or format is created
        """
        conections = self.search([('state', '=', 'connect')])
        for connec in conections:
            report_config = self.env['agora.reports.config'].search([('company_id', '=', connec.company_id.id),
                                                                     ('report_type', '=', 'last_ids')], limit=1)
            if report_config:
                params = {
                    'QueryGuid': '{%s}' % report_config.guid,
                    'Params': {}
                    }
                agora_ids, message = self.post_request(connec.url_server, '/custom-query', connec.server_api_key, params)
                if agora_ids:
                    ids = agora_ids.json()[0]
                    connec.update({'last_format_id': ids.get('last_format_id'),
                                   'last_product_id': ids.get('last_product_id')})

    def get_additional_formats(self, parent_product, connection):
        """"
        Function to get the correspondent formats to the provided product
        Params:
            parent_product: Product Main in Odoo, this product could have formats(children products)
            connection: Api connection to be used, should be taked considering the product company_id
        Return:
            List of dictionaries, considering the rigth estructure to be send it to Agora
        """
        formats = []
        all_formats = self.env['product.template'].search([('parent_id', '=', parent_product.id),
                                                           ('company_id', '=', parent_product.company_id.id),
                                                           ('active', 'in', [True, False])])
        for product in all_formats:
            format_id = product.sale_format
            if product.sale_format == 0:
                format_id = connection.last_format_id + 1
                connection.last_format_id = format_id
            prices = self.get_post_prices(product)
            product_data = {
                "Id": format_id,
                "Name": product.name,
                "Ratio": product.ratio,
                "ButtonText": product.button_text,
                "Color": product.color or "#BACDE2",
                "SaleableAsMain": product.is_saleable_as_main,
                "SaleableAsAddin": product.is_saleable_as_adding,
                "AskForAddins": product.ask_for_addings,
                "DeletionDate": None if product.active else product.write_date.isoformat(),
                "Prices": prices
            }
            formats.append(product_data)
            if product.product_addins_ids:
                addins = []
                for add in product.product_addins_ids:
                    base_format = add.sale_format if add.parent_id else add.base_format_id
                    addins.append({"SaleFormatId": base_format})
                product_data.update({'MinAddins': product.min_addings,
                                     'MaxAddins': product.max_addings,
                                     'Addins': addins})
        return formats

    @staticmethod
    def get_post_prices(product):
        """
        Function to get the prices related with the provided product
        Return:
            Prices List considering only the active pricelist by date
        """
        prices = []
        for price in product.product_pricelist_ids:
            if not price.date_end:
                price_rec = {
                    "PriceListId": price.pricelist_id.agora_id,
                    "MainPrice": price.fixed_price,
                    "AddinPrice": price.addin_price,
                    "MenuItemPrice": price.menuitem_price
                }
                prices.append(price_rec)
        return prices

    def product_data(self, product, is_new, connection):
        """
        Function to get the FULL data to create a product POST
        Return:
            Dictionary with product data and Sale Formats associated
        """
        tax = self.env['agora.tax'].search([('account_tax_id', '=', product.taxes_id[0].id),
                                            ('company_id', '=', connection.company_id.id)])
        product_id = product.agora_id
        base_format_id = product.base_format_id
        if is_new:
            product_id = connection.last_product_id + 1
            connection.last_product_id = product_id
            base_format_id = connection.last_format_id + 1
            connection.last_format_id = base_format_id
        data = {
            "Products": [
                {
                    "Id": product_id,
                    "Name": product.name,
                    "BaseSaleFormatId": base_format_id,
                    "ButtonText": product.button_text,
                    "Color": product.color or "#BACDE2",
                    "PLU": product.product_sku if product.product_sku != 0 else "",
                    "FamilyId": product.categ_id.agora_id if product.categ_id.name != 'All' else None,
                    "VatId": tax.agora_id,
                    "UseAsDirectSale": False,
                    "SaleableAsMain": product.is_saleable_as_main,
                    "SaleableAsAddin": product.is_saleable_as_adding,
                    "IsSoldByWeight": product.is_sold_by_weight,
                    "AskForPreparationNotes": product.ask_preparation_notes,
                    "AskForAddins": product.ask_for_addings,
                    "PrintWhenPriceIsZero": not product.print_zero,
                    "PreparationTypeId": product.preparation_id.agora_id or None,
                    "PreparationOrderId": product.preparation_order_id.agora_id or None,
                    "CostPrice": product.standard_price,
                    "Barcodes": product.barcode,
                    "DeletionDate": None if product.active else product.write_date.isoformat(),
                    "Prices": self.get_post_prices(product),
                    "AdditionalSaleFormats": self.get_additional_formats(product, connection)
                }
            ]
        }
        if product.product_addins_ids:
            addins = []
            for add in product.product_addins_ids:
                base_format = add.sale_format if add.parent_id else add.base_format_id
                addins.append({"SaleFormatId": base_format})
            data['Products'][0].update({'MinAddins': product.min_addings,
                                        'MaxAddins': product.max_addings,
                                        'Addins': addins})
        # # Discomment the following lines to get de json data
        # import json
        # json = json.dumps(data, indent=4)
        return data

    def post_products(self, products):
        """"
        Function to send to Agora all products provided in the params
        """
        product_env = self.env['product.template']
        self._get_last_ids()
        for product in products:
            connection = self.get_related_connection(product)
            if connection:
                is_new = False
                if product.sync_status == 'new':
                    is_new = True
                data = self.product_data(product, is_new, connection)
                try:
                    post, message = self.post_request(connection.url_server, '/import', connection.server_api_key, data)
                    if post and post.status_code and post.status_code == 200:
                        # If the execution went OK
                        # Instantly should be updated the product status, because even if there is block in the function
                        # because another error this changes are already updated in Agora
                        # self.update_sync_status(product)
                        product.sync_status = 'done'
                        product.product_formats_ids.sync_status = 'done'
                        # Execute commit() to be sure the product status its updated
                        # even if the script fail in other products sync
                        self._cr.commit()
                        if is_new:
                            agora_id = data.get('Products')[0].get('Id')
                            base_format_id = data.get('Products')[0].get('BaseSaleFormatId')
                            product.update({'agora_id': agora_id, 'base_format_id': base_format_id})
                        for rec in data.get('Products')[0].get('AdditionalSaleFormats'):
                            current_format = product_env.search([('name', '=', rec.get('Name')),
                                                                 ('parent_id', '=', product.id)])
                            if current_format.sale_format == 0:
                                current_format.sale_format = rec.get('Id')
                    else:
                        raise ValidationError(_(" Agora system detected the following exception:\n%s") % message.decode())
                except Exception as e:
                    _logger.error(e)
                    raise ValidationError(_("ERROR RESPONSE:\n %s") % e)

# -----------------------------------------------------------------------------------------------------
# -------------------- GET REQUEST TO GENERATE SALES DATA IN ODOO -------------------------------------
# -----------------------------------------------------------------------------------------------------

    def get_invoices(self, date):
        """"
        Function to get Products from Agora
        Generate Sale Order record for each Agora Invoice
        Exist 4 type of invoices in Agora:
            ▪ BasicInvoice: Factura simplificada
            ▪ StandardInvoice: Factura nominal
            ▪ BasicRefund: Devolucion de factura simplificada
            ▪ StandardRefund: Devolucion de factura nominal
        endpoint example => /export/?business-day=2022-06-05&filter=Invoices
        """
        endpoint = '/export/?business-day={}'.format(date)
        params = {
            'filter': 'Invoices',
        }
        invoices = self.get_request(self.url_server, endpoint, self.server_api_key, params)
        if invoices and invoices.json().get('Invoices'):
            json_invoices = invoices.json().get('Invoices')
            # Generate the Logs from the data
            log = self.generate_sale_api_logs(json_invoices)
            # Divide Invoices and Refunds
            basic_invoices = log.api_line_ids.filtered(
                lambda l: l.state != 'done' and l.document_type in ['BasicInvoice', 'StandardInvoice'])
            basic_refunds = log.api_line_ids.filtered(
                lambda l: l.state != 'done' and l.document_type in ['BasicRefund', 'StandardRefund'])
            # Firstable will be process the invoice, because could be a refund related with one of this refunds
            # Only 100 Invoices will be process to avoid time out in Odoo.sh
            for invoice in basic_invoices[0:100]:
                record = json.loads(invoice.order_data)
                log_line = self.get_related_log_line(record)
                sos = self._create_sale_order(record, log_line)
                self.generate_invoice(sos, record.get('DocumentType'))
            for refund in basic_refunds[0:100]:
                record = json.loads(refund.order_data)
                if record:
                    log_refund = self.get_related_log_line(record)
                    self.generate_credit_note(record, log_refund)

    def generate_sale_api_logs(self, json_invoices):
        """"
        Function to generate logs with all the ticket items coming from the Agora Data
        There is a _cr_commit to save instantly the data generated from this function.
        """
        log_obj = self.env['sale.api']
        log_line_obj = self.env['sale.api.line']
        if json_invoices:
            api_line_ids = []
            business_date = datetime.strptime(json_invoices[0].get('BusinessDay'), '%Y-%m-%d').date()
            log = log_obj.search([('data_date', '=', business_date), ('company_id', '=', self.company_id.id)])
            if not log:
                log = log_obj.create({'data_date': business_date, 'executed_by': self._uid,
                                      'company_id': self.company_id.id})
            for record in json_invoices:
                existing_line = log_line_obj.search([('ticket_number', '=', record.get('Number')),
                                                     ('ticket_serial', '=', record.get('Serie')),
                                                     ('sale_api_id.company_id', '=', self.company_id.id)])
                if not existing_line:
                    json_record = json.dumps(record)
                    line = log_line_obj.create({
                        'order_data': json_record,
                        'order_customer': record.get('Customer').get('FiscalName') if record.get('Customer') else 'Generic',
                        'ticket_number': record.get('Number'),
                        'ticket_serial': record.get('Serie'),
                        'document_type': record.get('DocumentType')
                    })
                    api_line_ids.append(line)
            log.api_line_ids = [(4, x.id) for x in api_line_ids]
            self._cr.commit()
        return log

    @staticmethod
    def complete_sequence(number):
        length = 6
        return str(number).zfill(length)

    def generate_invoice(self, sos, doc_type):
        """"
        Function to generate the Invoices for the provided S.Orders
        """
        if self.sale_flow != 'sale':
            invoices = []
            for sale in sos:
                so = sale.get('so')
                order_data = sale.get('data')
                if so.order_line and not so.is_incomplete:
                    # For each So generated should be create the related invoice in POSTED
                    so._force_lines_to_invoice_policy_order()
                    # Create Invoice associated with the SO
                    invoice = so._create_invoices()
                    invoice.sale_center_id = so.sale_center_id
                    self.update_account_and_journal(invoice, doc_type)
                    invoices.append(invoice)
                    # Update values in the created Inv
                    invoice.invoice_line_ids.analytic_account_id = so.sale_center_id.analytic_id.id
                    invoice.invoice_date = so.date_order.date()
                    name = '{}/{}'.format(so.serie, self.complete_sequence(so.number))
                    invoice.update({
                        'invoice_date_due': invoice.invoice_date,
                        'date': invoice.invoice_date,
                        'number': so.number,
                        'serie': so.serie,
                        'name': name
                    })
                    self.post_invoice(invoice)
                    # Create the Payment associated with the created invoice
                    self.paid_invoice(invoice, order_data)
                    _logger.info("POSTED SO : {} - {}".format(so.number, so.name))
            return invoices

    def get_custom_journal(self, doc_type):
        """"
        Function to get the rigth journal in case its mapped in configuration.
        Mapped is get it from Agora/Settings/Accounting config/Journal-Invoice
        @Return the journal related with the document type coming in the Agora ticket
        """
        journal = False
        if doc_type == 'BasicInvoice':
            journal = self.env['invoice.type.journal'].search([('invoice_type', '=', 'basic'),
                                                               ('company_id', '=', self.company_id.id)])
        if doc_type == 'StandardInvoice':
            journal = self.env['invoice.type.journal'].search([('invoice_type', '=', 'standard'),
                                                               ('company_id', '=', self.company_id.id)])
        return journal

    def update_custom_mapping_accounts(self, invoice):
        """"
        Function to get the rigth journal in case its mapped in configuration.
        Mapped is get it from Agora/Settings/Accounting config/Sale Center-Accounts
        @Return the Accounts related with the Sale Center coming from Agora ticket
        """
        center_account = self.env['sale.center.account'].search([('sale_center_id', '=', invoice.sale_center_id.id)], limit=1)
        if center_account:
            invoice.invoice_line_ids.account_id = center_account.account_id
            counterpart = invoice.line_ids.filtered(lambda l: l.debit > 0)
            counterpart.account_id = center_account.counterpart_account_id

    def update_account_and_journal(self, invoice, doc_type):
        # Assign the journal depending the invoice type (Standard or basic)
        invoice.document_type = doc_type
        journal = self.get_custom_journal(doc_type)
        if journal:
            invoice.update({'journal_id': journal.journal_id.id})
        self.update_custom_mapping_accounts(invoice)

    def post_invoice(self, invoices):
        if self.sale_flow in ['invoice', 'payment']:
            for inv in invoices:
                # Post invoices
                inv.action_post()

    def paid_invoice(self, invoices, order_data=False):
        """
         This method create the payment for invoice automatically
        """
        account_payment_env = self.env['account.payment']
        center_account = self.env['sale.center.account'].search([('sale_center_id', '=', invoices.sale_center_id.id)], limit=1)
        if self.sale_flow == 'payment':
            for invoice in invoices:
                if invoice.amount_residual:
                    payments = self.prepare_payment_data(invoice, order_data)
                    for payment in payments:
                        payment_id = account_payment_env.create(payment)
                        # Update the account in case a configuration exist
                        if center_account:
                            # Change the accounts in the payment lines before posted
                            # Filter Counterpart lines
                            if payment_id.payment_type == 'inbound':
                                counterpart_account = payment_id.line_ids.filtered(lambda l: l.credit > 0)
                                counterpart_account.account_id = center_account.counterpart_account_id
                            elif payment_id.payment_type == 'outbound':
                                account_id = payment_id.line_ids.filtered(lambda l: l.credit > 0)
                                account_id.account_id = center_account.account_id
                                counterpart_account = payment_id.line_ids.filtered(lambda l: l.credit == 0)
                                counterpart_account.account_id = center_account.counterpart_account_id
                        payment_id.action_post()
                        self.reconcile_payment(payment_id, invoice)
            return True

    def get_payments_group_by_method(self, order_data):
        """"
        Return {'code': 'efectivo' , 'qty': 200}
        """
        total_payments = []
        for k, g in groupby(order_data.get('Payments'), key=lambda x: (x.get('MethodName'))):
            groupList = list(g)
            total_payments.append({
                'method': k,
                'qty': sum(c['Amount'] for c in groupList),
                'tip': sum(c['TipAmount'] for c in groupList)
            })
        total_payments = self.verify_payment_methods(total_payments)
        return total_payments

    def verify_payment_methods(self, total_payments):
        method_env = self.env['agora.payment.method']
        for rec in total_payments:
            exist = method_env.search([('code', '=', rec.get('method')),
                                       ('company_id', '=', self.company_id.id)])
            if not exist:
                exist = method_env.create({'code': rec.get('method'),
                                           'name': rec.get('method'),
                                           'company_id': self.company_id.id,
                                           'description': 'Auto-Generated'})
            rec.update({'method': exist})
        return total_payments

    def prepare_payment_data(self, invoice, order_data):
        """
        This method use to prepare a vals dictionary for payment
        """
        payment_list = []
        date = invoice.date
        mapping = self.env['account.mapping'].search([('company_id', '=', self.company_id.id)])
        if self.is_date_from_invoice:
            date = invoice.invoice_date
        payments = self.get_payments_group_by_method(order_data)
        for method in payments:
            journal = invoice.analytic_group_id.journal_id
            payment_type = 'inbound'
            if method.get('qty') < 0:
                payment_type = 'outbound'
            payment_list.append({
                'journal_id': journal.id,
                'ref': invoice.ref,
                'currency_id': invoice.currency_id.id,
                'payment_type': payment_type,
                'date': date,
                'agora_payment_id': method.get('method').id,
                'partner_id': invoice.commercial_partner_id.id,
                'amount': abs(method.get('qty')),
                'partner_type': 'customer',
                'sale_center_id': invoice.sale_center_id.id,
                'analytic_group_id': invoice.analytic_group_id.id
            })
        return payment_list

    def reconcile_payment(self, payment_id, invoice):
        """
        This method is use to reconcile payment.
        """
        move_line_obj = self.env['account.move.line']
        domain = [('account_internal_type', 'in', ('receivable', 'payable')),
                  ('reconciled', '=', False)]
        line_ids = move_line_obj.search([('move_id', '=', invoice.id)])
        to_reconcile = [line_ids.filtered(lambda line: line.account_internal_type == 'receivable')]

        for payment, lines in zip([payment_id], to_reconcile):
            payment_lines = payment.line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                         ('reconciled', '=', False)]).reconcile()

    def validate_picking(self, pickings):
        """"
            Function to Assign and Validate the Stock Picking
        """
        for picking in pickings:
            picking.action_confirm()
            picking.action_assign()
            picking._action_done()
            if picking.products_availability_state == 'available':
                # If are all available should be Done the Picking
                for line in picking.move_ids_without_package:
                    line.quantity_done = line.product_uom_qty
                picking.button_validate()
            else:
                picking.validation_counter += 1

    def generate_credit_note(self, refund, log_refund):
        """This function will generate a credit note in Odoo when a refund come from Agora.
            :param refund: Record of refund coming from Agora.
        """
        if self.sale_flow == 'payment':
            order = self.env['sale.order'].search([('number', '=', refund['RelatedInvoice'].get('Number')),
                                                   ('company_id', '=', self.company_id.id),
                                                   ('serie', '=', refund['RelatedInvoice'].get('Serie'))], limit=1)
            refund_inv = self.env['account.move'].search([('number', '=', refund.get('Number')),
                                                          ('move_type', '=', 'out_refund'),
                                                          ('company_id', '=', self.company_id.id),
                                                          ('serie', '=', refund.get('Serie'))], limit=1)
            if order and not refund_inv:
                moves2revert = order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.payment_state in ['paid',
                                                                                                                     'in_payment'])
                default_values_list = []
                for move in moves2revert:
                    serie = refund.get('Serie').replace('0', '00')
                    name = '{}/{}'.format(serie, self.complete_sequence(refund.get('Number')))
                    default_values_list.append({
                        'ref': _('Reversal of: {}'.format(move.name)),
                        'date': move.date,
                        'name': name,
                        'number': refund.get('Number'),
                        'document_type': refund.get('DocumentType'),
                        'serie': refund.get('Serie'),
                        'invoice_date': move.is_invoice(include_receipts=True) and move.date,
                        'journal_id': move.journal_id.id,
                        'invoice_payment_term_id': None
                    })
                revert = moves2revert._reverse_moves(default_values_list)
                revert.action_post()
                self.paid_invoice(revert, refund)
                order.picking_ids.write({'state': 'cancel'})
                log_refund.update({'state': 'done'})
                return True

    def get_related_log_line(self, data):
        log_line_obj = self.env['sale.api.line']
        existing_line = log_line_obj.search([('ticket_number', '=', data.get('Number')),
                                             ('ticket_serial', '=', data.get('Serie')),
                                             ('sale_api_id.company_id', '=', self.company_id.id)])
        return existing_line or False

    def get_card_tips(self, record):
        """"
        Function to get tips related with tarjeta.
        Its a little bit harcoding because in Agora there is not a property to
        recognize the different method types. Only the name(string) can give us a clou
        """
        payments = self.get_payments_group_by_method(record)
        total_tip = 0.0
        for pay in payments:
            if 'tarjeta' in pay.get('method').code.lower():
                total_tip += pay.get('tip')
        return total_tip

    def _create_sale_order(self, record, log_line):
        """"
        Function to create Sale Order from Agora Data
        Return a List of dictionary with the following structure
        """
        work_place_env = self.env['work.place']
        so_line_env = self.env['sale.order.line']
        so_env = self.env['sale.order']
        sale_center_env = self.env['sale.center']
        partner = self.get_partner(record)
        card_tips = self.get_card_tips(record)
        generated_sos = []
        log_line.message = ''
        serie = record.get('Serie').replace('0', '00') if record.get('Serie').count('0') == 1 else record.get('Serie')
        for item in record.get('InvoiceItems'):
            exist_so = so_env.search([('number', '=', record.get('Number')),
                                      ('serie', '=', serie),
                                      ('company_id', '=', self.company_id.id)])
            # Validate if its available the SO creation
            so_creation_ok = True
            if not exist_so:
                for line in item.get('Lines'):
                    exist_prod = self.verify_so_line_product(line)
                    if exist_prod != 0:
                        so_creation_ok = False
                        log_line.update_log_message(exist_prod)
                        log_line.update_product_error(line.get('ProductName'))
            else:
                log_line.update({'state': 'done'})
            if not exist_so and so_creation_ok:
                if so_creation_ok:
                    so_data = {
                        'partner_id': partner.id,
                        'company_id': self.company_id.id,
                        'number': record.get('Number'),
                        'tips_amount': card_tips,
                        'document_type': record.get('DocumentType'),
                        'waiter': record.get('User').get('Name') if record.get('User') else 'Generic Waiter',
                        'serie': serie,
                        'business_date': datetime.strptime(record.get('BusinessDay'), '%Y-%m-%d').date()
                    }
                    if record.get('Workplace'):
                        wp = work_place_env.search([('agora_id', '=', record['Workplace'].get('Id')),
                                                    ('company_id', '=', self.company_id.id)], limit=1)
                        so_data.update({'work_place_id': wp.id, 'warehouse_id': wp.analytic_group_id.warehouse_id.id})
                    if item.get('SaleCenter'):
                        sc = sale_center_env.search([('agora_id', '=', item['SaleCenter'].get('Id')),
                                                    ('company_id', '=', self.company_id.id)], limit=1)
                        so_data.update({'sale_center_id': sc.id, 'analytic_account_id': sc.analytic_id.id})
                    so = so_env.create(so_data)
                    if so:
                        generated_sos.append({'so': so, 'data': record})
                        global_discount = 0.0
                        if item['Discounts'].get('DiscountRate'):
                            global_discount = item['Discounts'].get('DiscountRate') * 100
                        for line in item.get('Lines'):
                            data = self.get_so_lines(line, so, global_discount, False)
                            if data:
                                so_line_env.create(data)
                            else:
                                so.is_incomplete = True
                            if line.get('Addins'):
                                for add in line.get('Addins'):
                                    add_data = self.get_so_lines(add, so, global_discount, True)
                                    if add_data:
                                        add_data.update({'is_addins': True,
                                                         'product_uom_qty': line.get('Quantity'),
                                                         'qty_delivered': line.get('Quantity')})
                                        so_line_env.create(add_data)
                        if item['Discounts'].get('CashDiscount'):
                            amount = item['Discounts'].get('CashDiscount')
                            discount_line = self.get_discount_line(so, amount)
                            so_line_env.create(discount_line)
                        if not so.is_incomplete:
                            so.action_confirm()
                            so.picking_ids.sale_id = so.id
                            self.validate_picking(so.picking_ids)
                            log_line.update({'state': 'done'})
                        so.date_order = parser.parse(record.get('Date'))
                        so.effective_date = so.expected_date
                        if so.tips_amount > 0:
                            so.generate_tip_account()
        return generated_sos

    def get_discount_line(self, so, amount):
        discount_prod = self.env['product.product'].search([('product_tmpl_id.is_product_discount', '=', True),
                                                            ('company_id', '=', so.company_id.id)], limit=1)
        line_data = {
            'name': discount_prod.product_tmpl_id.name,
            'product_id': discount_prod.id,
            'order_id': so.id,
            'tax_id': [(6, 0, [])],
            'price_unit': abs(amount) * -1,
            'product_uom': discount_prod.product_tmpl_id.uom_id.id,
            'company_id': self.company_id.id,
            'product_uom_qty': 1,
            'qty_delivered': 1,
        }
        return line_data

    def verify_so_line_product(self, line):
        product = self.get_product_for_line(line)
        if not product:
            return 1
        return 0

    def get_so_lines(self, line, so, global_discount, is_addin):
        tax_env = self.env['agora.tax']
        product = self.get_product_for_line(line)
        tax = tax_env.search([('agora_id', '=', line.get('VatId')), ('company_id', '=', self.company_id.id)])
        if product:
            line_data = {
                'index': line.get('Index'),
                'name': line.get('ProductName'),
                'product_id': product.id,
                'order_id': so.id,
                'tax_id': [(6, 0, tax.account_tax_id.ids)],
                'price_unit': line.get('TotalAmount') / line.get('Quantity') if not is_addin else 0.0,
                'product_uom': product.product_tmpl_id.uom_id.id,
                'company_id': self.company_id.id,
                'discount': global_discount,
                'product_uom_qty': line.get('Quantity') or 1.0,
                'qty_delivered': line.get('Quantity') or 1.0,
            }
            if line.get('DiscountRate') and line['DiscountRate'] == 1:
                line_data.update({'is_invitation': True})
        else:
            return False
        return line_data

    def get_product_for_line(self, line):
        """"
         Function to Identify the related product with an Order Line
         Exist a default product to be used for Menus.
         In case Its not a Menu should be localize by the Format ID coming in the ticket line
        """
        prod_prod_env = self.env['product.product']
        format_id = line.get('SaleFormatId')
        if line.get('Type') == 'MenuHeader':
            product = prod_prod_env.search([('is_product_menu', '=', True),
                                            ('product_tmpl_id.company_id', '=', self.company_id.id)], limit=1)
        else:
            product = prod_prod_env.search(['|',
                                            ('product_tmpl_id.base_format_id', '=', format_id),
                                            ('product_tmpl_id.sale_format', '=', format_id),
                                            ('product_tmpl_id.company_id', '=', self.company_id.id)], limit=1)
        return product

    def get_partner(self, record):
        partner = self.env['res.partner'].search([('name', 'like', 'Generic Client'),
                                                  ('company_id', '=', self.company_id.id)])
        if record.get('Customer'):
            agora_id = record.get('Customer').get('Id')
            exist = self.env['res.partner'].search([('agora_id', '=', agora_id),
                                                    ('company_id', '=', self.company_id.id)], limit=1)
            if not exist and record.get('Customer'):
                customer = record.get('Customer')
                # Create new partner
                self.env['res.partner'].create({
                    'name': customer.get('FiscalName'),
                    'company_type': 'person',
                    'agora_id': customer.get('Id'),
                    'vat': customer.get('Cif'),
                    'zip': customer.get('ZipCode'),
                    'street': customer.get('Street'),
                    'city': customer.get('City'),
                    'company_id': self.company_id.id,
                })
            else:
                partner = exist
        return partner

    def _get_loss_products_from_agora(self, start_date, end_date):
        """"
        Function to update the Loss Products.
        With this Loss should be generated a new Validated SO
        """
        order_line_env = self.env['sale.order.line']
        loss_dict = []
        report_config = self.env['agora.reports.config'].search([('company_id', '=', self.company_id.id),
                                                                ('report_type', '=', 'loss')], limit=1)
        start_date.isoformat()
        if report_config:
            params = {
                'QueryGuid': '{%s}' % report_config.guid,
                'Params': {
                    'from': start_date.isoformat(),
                    'to': end_date.isoformat()
                }
            }
            loss_products = self.post_request(self.url_server, '/custom-query', self.server_api_key, params)
            if loss_products and loss_products.status_code and loss_products.status_code == 200:
                products = loss_products.json()
                for product in products:
                    exist = order_line_env.search([('agora_loss_id', '=', product.get('StockChangeId')),
                                                   ('product_id.product_tmpl_id.agora_id', '=', product.get('ProductId'))])
                    if not exist:
                        prod_data = {
                            'agora_loss_id': product.get('StockChangeId'),
                            'quantity': product.get('Quantity'),
                            'product_agora_id': product.get('ProductId')
                        }
                        loss_dict.append(prod_data)
        return loss_dict

    def _create_so_for_loss_products(self, loss_products, date):
        prod_prod_env = self.env['product.product']
        so_line_env = self.env['sale.order.line']
        if loss_products:
            # Create SO
            partner = self.get_partner(loss_products[0])
            so_data = {
                'partner_id': partner.id,
                'company_id': self.company_id.id,
                'date_order': date.date()
            }
            so = self.env['sale.order'].create(so_data)
            for line in loss_products:
                # Create the lines under the same order
                product_id = prod_prod_env.search([('product_tmpl_id.agora_id', '=', line.get('product_agora_id')),
                                                   ('product_tmpl_id.company_id', '=', self.company_id.id)], limit=1)
                if product_id:
                    line_data = {
                        'index': line.get('Index'),
                        'name': '[Loss]{}'.format(product_id.name),
                        'product_id': product_id.id,
                        'order_id': so.id,
                        'tax_id': [(6, 0, [])],
                        'price_unit': 0.0,
                        'product_uom': product_id.product_tmpl_id.uom_id.id,
                        'company_id': self.company_id.id,
                        'product_uom_qty': line.get('quantity') or 1.0,
                        'qty_delivered': line.get('quantity') or 1.0,
                        'agora_loss_id': line.get('agora_loss_id')
                    }
                    so_line_env.create(line_data)
            so.action_confirm()
            self.validate_picking(so.picking_ids)

# -----------------------------------------------------------------------------------------------------
# --------------------------------------- ACTIONS -----------------------------------------------------
# -----------------------------------------------------------------------------------------------------
    def action_view_server(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Server config',
            'res_model': 'agora.service.config',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('agora_id', '=', self.id)],
            'context': {'default_agora_id': self.id}
        }

    def _agora_first_sync(self):
        """"
        Main Function to make the call to all the functions need it to complete the sync
        """
        conections = self.search([('state', '=', 'connect')])
        for record in conections:
            record.get_master_pricelist()
            record.get_master_work_places()
            record.get_master_sale_center()
            record.get_master_categories()
            record.get_master_products()
            _logger.info("***Finish a company connection**")

    def _update_masters_from_agora(self):
        """"
        Action to keep updated the Masters in Odoo
        """
        conections = self.search([('state', '=', 'connect')])
        for record in conections:
            export_endpoint = '/export-master'
            record.get_master_pricelist(export_endpoint)
            record.get_master_work_places(export_endpoint)
            record.get_master_sale_center(export_endpoint)
            record.get_master_categories(export_endpoint)

    def _update_products_from_odoo(self):
        """"
        Action to post products in Odoo
        """
        conections = self.search([('state', '=', 'connect')])
        product_env = self.env['product.template']
        for connec in conections:
            product_to_send = product_env.search([('company_id', '=', connec.company_id.id),
                                                  ('sync_status', 'in', ['new', 'modified']),
                                                  ('active', 'in', [True, False])])
            if product_to_send:
                self.post_products(product_to_send)

    def _update_sales_from_agora(self, date=False):
        """"
        Action to get invoices from Agora
        """
        conections = self.search([('state', '=', 'connect')])
        if not date:
            date = fields.Date.today()
        for connec in conections:
            connec.get_invoices(date)

    def download_by_date(self, date, company):
        """"
        Action to get invoices from Agora
        But just for the related company and for specific date
        """
        conection = self.search([('state', '=', 'connect'), ('company_id', '=', company.id)], limit=1)
        if conection:
            conection.get_invoices(date)

    def _update_loss_products(self):
        """"
        Action to get invoices from Agora
        """
        conections = self.search([('state', '=', 'connect')])
        start_datetime = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_datetime = fields.Datetime.now()
        for connec in conections:
            loss_products = connec._get_loss_products_from_agora(start_datetime, end_datetime)
            if loss_products:
                # Generate a SO
                connec._create_so_for_loss_products(loss_products, end_datetime)

    def action_to_validate_pickings(self):
        """"
        Action called from Schedulle action to set to Done the Picking coming from SO.
        Was stablich a limit to avoid time out problems
        """
        pickings = self.env['stock.picking'].search([('state', 'not in', ['done', 'cancel']), ('sale_id', '!=', False)],
                                                    limit=100, order='validation_counter asc')
        if pickings:
            self.validate_picking(pickings)
