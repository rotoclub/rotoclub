# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
from odoo.exceptions import ValidationError
from dateutil import parser
from datetime import datetime
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
    count_api = fields.Integer(
        compute='_compute_server_config'
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

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('api.connection', sequence_date=seq_date) or _('New')
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            if vals.get('state') == 'connect':
                duplicated = rec.search_count([('company_id', '=', rec.company_id.id), ('state', '=', 'connect')])
                if duplicated:
                    raise ValidationError(_('Sorry!! Exist another API connection for the same company'
                                            ' already connected'))
        return super().write(vals)

    def _compute_server_config(self):
        server_id = self.env['server.config']
        for record in self:
            record.count_api = server_id.search_count([('agora_id', '=', record.id)])

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
            if connect:
                if connect.status_code == 200:
                    return connect
                else:
                    return False
        except Exception as e:
            _logger.error(e)
            raise UserError(_("There was an error during the connection, please try again in a few minutes\n"
                              "The following error was return:\n%s") % e)

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

    def get_master_products(self, endpoint):
        """"
        Function to get Products from Agora
        Generate Product.template record for each Agora Product that not exist in Odoo
        """
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
                                                     ('company_id', '=', self.company_id.id)])
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

    def get_master_sale_center(self, endpoint):
        """"
        Function to get de Sales centers
        This function needs the previous creation of the Default Price List
        """
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

    def get_master_pricelist(self, endpoint):
        """"
        Function to get de PriceList
        """
        pricelist_env = self.env['product.pricelist']
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

    def get_master_work_places(self, endpoint):
        """"
        Function to get Work Places
        """
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
            params = {
                'QueryGuid': '{533750D6-11DE-4D33-8D11-8A3B63C33F22}',
                'Params': {}
            }
            agora_ids = self.post_request(connec.url_server, '/custom-query', connec.server_api_key, params)
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
                    post = self.post_request(connection.url_server, '/import', connection.server_api_key, data)
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
                        raise ValidationError(_('Sorry the synchronization could not be completed for the product {}.\n'
                                                ' Please verify all the required fields'.format(product.name)))
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
            basic_invoices = list(filter(lambda inv: inv.get('DocumentType') in ['BasicInvoice', 'StandardInvoice'], json_invoices))
            basic_refunds = list(filter(lambda inv: inv.get('DocumentType') == 'BasicRefund', json_invoices))
            for record in basic_invoices:
                sos = self._create_sale_order(record)
                self.generate_invoice(sos)
            for refund in basic_refunds:
                self.generate_credit_note(refund)

    def generate_invoice(self, sos):
        """"
        Function to generate the Invoices for the provided S.Orders
        """
        if self.sale_flow != 'sale':
            invoices = []
            for so in sos:
                if so.order_line:
                    # For each So generated should be create the related invoice in POSTED
                    so._force_lines_to_invoice_policy_order()
                    # Create Invoice associated with the SO
                    invoice = so._create_invoices()
                    invoice.update({'number': so.number, 'serie': so.serie})
                    invoices.append(invoice)
                    # Update values in the created Inv
                    invoice.invoice_line_ids.analytic_account_id = so.sale_center_id.analytic_id.id
                    invoice.invoice_date = so.date_order.date()
                    self.post_invoice(invoice)
                    # Create the Payment associated with the created invoice
                    self.paid_invoice(invoice)
                    _logger.info("POSTED SO : {} - {}".format(so.number, so.name))
            return invoices

    def post_invoice(self, invoices):
        if self.sale_flow in ['invoice', 'payment']:
            for inv in invoices:
                # Post invoices
                inv.action_post()

    def paid_invoice(self, invoices):
        """
         This method create the payment for invoice automatically
        """
        account_payment_env = self.env['account.payment']
        if self.sale_flow == 'payment':
            for invoice in invoices:
                if invoice.amount_residual:
                    vals = self.prepare_payment_data(invoice)
                    payment_id = account_payment_env.create(vals)
                    payment_id.action_post()
                    self.reconcile_payment(payment_id, invoice)
            return True

    def prepare_payment_data(self, invoice):
        """
        This method use to prepare a vals dictionary for payment
        """
        date = invoice.date
        if self.is_date_from_invoice:
            date = invoice.invoice_date
        return {
            'journal_id': invoice.analytic_group_id.journal_id.id,
            'ref': invoice.payment_reference,
            'currency_id': invoice.currency_id.id,
            'payment_type': 'inbound',
            'date': date,
            'partner_id': invoice.commercial_partner_id.id,
            'amount': invoice.amount_residual,
            'payment_method_id': invoice.analytic_group_id.payment_method_id.id,
            'partner_type': 'customer'
        }

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

    def validate_picking(self, so):
        """"
            Function to Assign and Validate the Stock Picking
        """
        for picking in so.picking_ids:
            picking.action_confirm()
            picking.action_assign()
            picking._action_done()
            # The Picking should be validated only if all the products are covered
            all_available = True
            for so_line in so.order_line:
                if so_line.product_id.id not in so.picking_ids.move_ids_without_package.mapped('product_id').ids:
                    all_available = False
            if all_available:
                # If are all available should be Done the Picking
                for line in picking.move_ids_without_package:
                    line.quantity_done = line.product_uom_qty
                picking.button_validate()

    def generate_credit_note(self, refund):
        """This function will generate a credit note in Odoo when a refund come from Agora.
            :param refund: Record of refund coming from Agora.
        """
        if self.sale_flow == 'payment':
            order = self.env['sale.order'].search([('number', '=', refund['RelatedInvoice'].get('Number')),
                                                   ('serie', '=', refund['RelatedInvoice'].get('Serie'))], limit=1)
            refund_inv = self.env['account.move'].search([('number', '=', refund.get('Number')),
                                                          ('move_type', '=', 'out_refund'),
                                                          ('serie', '=', refund.get('Serie'))], limit=1)
            if order and not refund_inv:
                moves2revert = order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.payment_state in ['paid',
                                                                                                                     'in_payment'])
                default_values_list = []
                for move in moves2revert:
                    default_values_list.append({
                        'ref': _('Reversal of: {}'.format(move.name)),
                        'date': move.date,
                        'number': refund.get('Number'),
                        'serie': refund.get('Serie'),
                        'invoice_date': move.is_invoice(include_receipts=True) and move.date,
                        'journal_id': move.journal_id.id,
                        'invoice_payment_term_id': None
                    })
                revert = moves2revert._reverse_moves(default_values_list)
                revert.action_post()
                self.paid_invoice(revert)
                order.picking_ids.write({'state': 'cancel'})
                return True

    def _create_sale_order(self, record):
        work_place_env = self.env['work.place']
        so_line_env = self.env['sale.order.line']
        so_env = self.env['sale.order']
        sale_center_env = self.env['sale.center']
        partner = self.get_partner(record)
        generated_sos = []
        for item in record.get('InvoiceItems'):
            exist_so = so_env.search([('number', '=', record.get('Number')),
                                      ('serie', '=', record.get('Serie')),
                                      ('company_id', '=', self.company_id.id)])
            if not exist_so:
                so_data = {
                    'partner_id': partner.id,
                    'company_id': self.company_id.id,
                    'number': record.get('Number'),
                    'serie': record.get('Serie'),
                    'date_order': parser.parse(record.get('Date')),
                    'business_date': datetime.strptime(record.get('BusinessDay'), '%Y-%m-%d').date()
                }
                if record.get('Workplace'):
                    wp = work_place_env.search([('agora_id', '=', record['Workplace'].get('Id')),
                                                ('company_id', '=', self.company_id.id)], limit=1)
                    so_data.update({'work_place_id': wp.id})
                if item.get('SaleCenter'):
                    sc = sale_center_env.search([('agora_id', '=', item['SaleCenter'].get('Id')),
                                                ('company_id', '=', self.company_id.id)], limit=1)
                    so_data.update({'sale_center_id': sc.id})
                so = so_env.create(so_data)
                generated_sos.append(so)
                global_discount = 0.0
                if item['Discounts'].get('DiscountRate'):
                    global_discount = item['Discounts'].get('DiscountRate') * 100
                for line in item.get('Lines'):
                    data = self.get_so_lines(line, so, global_discount, False)
                    if data:
                        so_line_env.create(data)
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
                so.action_confirm()
                self.validate_picking(so)
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

    def get_so_lines(self, line, so, global_discount, is_addin):
        prod_prod_env = self.env['product.product']
        tax_env = self.env['agora.tax']
        format_id = line.get('SaleFormatId')
        product = prod_prod_env.search(['|',
                                        ('product_tmpl_id.base_format_id', '=', format_id),
                                        ('product_tmpl_id.sale_format', '=', format_id),
                                        ('product_tmpl_id.company_id', '=', self.company_id.id)], limit=1)
        tax = tax_env.search([('agora_id', '=', line.get('VatId')), ('company_id', '=', self.company_id.id)])
        line_data = False
        if product:
            line_data = {
                'index': line.get('Index'),
                'name': product.product_tmpl_id.name,
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
        return line_data

    def get_partner(self, record):
        partner = self.env['res.partner'].search([('name', 'like', 'Generic Client'),
                                                  ('company_id', '=', self.company_id.id)])
        if record.get('Customer'):
            agora_id = record.get('Customer').get('Id')
            exist = self.env['res.partner'].search([('agora_id', '=', agora_id),
                                                    ('company_id', '=', self.company_id.id)], limit=1)
            if not exist and record.get('Customer').get('FiscalName'):
                # Create new partner
                self.env['res.partner'].create({
                    'name': record.get('Customer').get('FiscalName'),
                    'agora_id': record.get('Customer').get('Id'),
                    'vat': record.get('Customer').get('Cif'),
                    'zip': record.get('Customer').get('ZipCode'),
                    'street': record.get('Customer').get('Street'),
                    'city': record.get('Customer').get('City'),
                })
            else:
                partner = exist
        return partner

# -----------------------------------------------------------------------------------------------------
# --------------------------------------- ACTIONS -----------------------------------------------------
# -----------------------------------------------------------------------------------------------------
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

    def _agora_first_sync(self):
        """"
        Main Function to make the call to all the functions need it to complete the sync
        """
        conections = self.search([('state', '=', 'connect')])
        for record in conections:
            export_endpoint = '/export-master'
            record.get_master_pricelist(export_endpoint)
            record.get_master_work_places(export_endpoint)
            record.get_master_sale_center(export_endpoint)
            record.get_master_categories(export_endpoint)
            record.get_master_products(export_endpoint)
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
