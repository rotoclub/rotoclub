# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
from odoo.exceptions import ValidationError

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
            connect = requests.get(url=url, headers=headers, params=params)
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
            connect = requests.post(url=url, headers=headers, json=json)
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
        if record.get('Name') == 'Harina':
            print('Harina')
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
            'print_zero': record.get('PrintWhenPriceIsZero'),
            'company_id': self.company_id.id,
            'responsible_id': False
        })
        if category_id:
            values_dict.update({'categ_id': category_id})
        product = products_env.create(values_dict)
        print('Product created ===> ' + product.name)
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
            print('Product ==> ' + sub_product.name + ' hijo de ==> ' + product.name)
        return addings

    def generate_product_prices(self, product, prices):
        """"
        Function to generate or update the product prices
        Params:
            product: Product to be updated
            Prices: Dict of prices related with the current product
        """
        pricelist_item_env = self.env['product.pricelist.item']
        price_list_env = self.env['product.pricelist']
        if prices:
            for price in prices:
                price_list = price_list_env.search([('agora_id', '=', price.get('PriceListId')),
                                                    ('company_id', '=', self.company_id.id)])
                if product:
                    exist = pricelist_item_env.search([('product_tmpl_id', '=', product.id),
                                                       ('date_end', '=', False),
                                                       ('pricelist_id.agora_id', '=', price.get('PriceListId'))])
                    if not exist:
                        # create new pricelist
                        data = {
                            'pricelist_id': price_list.id,
                            'product_tmpl_id': product.id,
                            'fixed_price': price.get('MainPrice'),
                            'date_start': fields.Datetime.now(),
                        }
                        pricelist_item_env.create(data)
                    elif exist.filtered(lambda pl: pl.fixed_price != price.get('MainPrice')):
                        # update existing pricelist
                        # The existing record will keep the old price but will be closed behind the end_date
                        # New price will be created with start date today. In order to keep the historical prices
                        uptdata = {
                            'date_end': fields.Datetime.now(),
                        }
                        exist[0].update(uptdata)
                        # create new price list
                        data = {
                            'pricelist_id': price_list.id,
                            'product_tmpl_id': product.id,
                            'fixed_price': price.get('MainPrice'),
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
                existing_cent = pricelist_env.search([('agora_id', '=', record.get('Id')),
                                                      ('company_id', '=', self.company_id.id)])
                if not existing_cent:
                    values_dict = {}
                    values_dict.update({
                        'name': record.get('Name'),
                        'agora_id': int(record.get('Id')),
                        'company_id': self.company_id.id
                    })
                    pricelist_env.create(values_dict)

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

    def get_last_ids(self, record):
        """"
        Function to get the last Farmat_id and Product_id
        Return:
             Dictionary {'format_id': xx, 'product_id':yy}
        """
        connection = self.get_related_connection(record)
        params = {
            'filter': 'Products'
        }
        products = self.get_request(connection.url_server, '/export-master', connection.server_api_key, params)
        if products and products.json().get('Products'):
            json_products = products.json().get('Products')
            last_product = max([rec['Id'] for rec in json_products if rec['BaseSaleFormatId']])
            base_formats = [rec['BaseSaleFormatId'] for rec in json_products if rec['BaseSaleFormatId']]
            list_formats = [rec['AdditionalSaleFormats'] for rec in json_products if rec['AdditionalSaleFormats']]
            for formats in list_formats:
                for form in formats:
                    base_formats.append(form['Id'])
            last_format = max(base_formats)
        connection.update({'last_format_id': last_format, 'last_product_id': last_product})

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
                    "AddinPrice": price.fixed_price,
                    "MenuItemPrice": 0.000
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
                    "PrintWhenPriceIsZero": product.print_zero,
                    "PreparationTypeId": product.preparation_id.agora_id,
                    "PreparationOrderId": product.preparation_order_id.agora_id,
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
        import json
        json = json.dumps(data, indent=4)
        return data

    def post_products(self, products):
        """"
        Function to send to Agora all products provided in the params
        """
        product_env = self.env['product.template']
        for product in products:
            is_new = False
            if product.sync_status == 'new':
                is_new = True
            self.get_last_ids(product)
            connection = self.get_related_connection(product)
            data = self.product_data(product, is_new, connection)
            try:
                post = self.post_request(connection.url_server, '/import', connection.server_api_key, data)
                if post and post.status_code and post.status_code == 200:
                    product.sync_status = 'done'
                    product.product_formats_ids.sync_status = 'done'
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
                    raise ValidationError(_('Sorry the synchronization could not be completed'))
            except Exception as e:
                _logger.error(e)
                raise ValidationError(_("ERROR RESPONSE:\n %s") % e)

# -----------------------------------------------------------------------------------------------------
# -------------------- GET REQUEST TO GENERATE SALE DATA IN ODOO --------------------------------------
# -----------------------------------------------------------------------------------------------------



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
            record.get_master_sale_center(export_endpoint)
            record.get_master_categories(export_endpoint)
            record.get_master_products(export_endpoint)
            print(' *************** finish one connection')

    def _update_masters_from_agora(self):
        """"
        Action to keep updated the Masters in Odoo
        """
        conections = self.search([('state', '=', 'connect')])
        for record in conections:
            export_endpoint = '/export-master'
            record.get_master_pricelist(export_endpoint)
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
                                                  ('sync_status', 'in', ['new', 'modifyied']),
                                                  ('active', 'in', [True, False])])
            if product_to_send:
                self.post_products(product_to_send)
