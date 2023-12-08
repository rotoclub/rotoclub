# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_agora_taxes(self):
        tax_id = self.env['agora.tax'].search([('agora_id', '!=', False), ('account_tax_id', '!=', False)], limit=1)
        return tax_id.account_tax_id if tax_id else False

    agora_id = fields.Integer(
        string='Agora ID',
        copy=False
    )
    base_format_id = fields.Integer(
        string='Base Sale Format',
        copy=False
    )
    parent_id = fields.Many2one(
        string='Parent Product',
        comodel_name='product.template'
    )
    agora_color = fields.Char(
        string='Agora Color'
    )
    button_text = fields.Char(
        string='Button Text'
    )
    ratio = fields.Float(
        string='Ratio'
    )
    product_sku = fields.Integer(
        string='PLU code'
    )
    sync_status = fields.Selection(
        selection=[('done', 'Completed'),
                   ('new', 'New'),
                   ('modified', 'Modified'),
                   ('error', 'Error')],
        default='new',
        copy=False,
        compute='_compute_sync_status'
    )
    preparation_id = fields.Many2one(
        string='Preparation Type',
        comodel_name='preparation.type',
        ondelete='restrict'
    )
    preparation_order_id = fields.Many2one(
        string='Preparation Order',
        comodel_name='preparation.order',
        ondelete='restrict'
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
        string='Sale Format',
        copy=False
    )
    product_formats_ids = fields.One2many(
        string='Formats',
        comodel_name='product.template',
        inverse_name='parent_id',
        ondelete='cascade'
    )
    min_addings = fields.Integer(
        string='Minimum',
        default=0
    )
    max_addings = fields.Integer(
        string='Maximum',
        default=1
    )
    product_addins_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_template_add_addings_rel',
        column1='product_id',
        column2='addins_id',
        string="Addins",
        check_company=True,
        copy=False,
    )
    product_pricelist_ids = fields.One2many(
        string='Pricelists',
        comodel_name='product.pricelist.item',
        inverse_name='product_tmpl_id'
    )
    tax_agora_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='account_agora_taxes_rel',
        column1='account_id',
        column2='agora_tax_id',
        string="Agora Taxes",
        compute='_compute_agora_taxes'
    )
    is_product_discount = fields.Boolean(
        string='Is Discount Product'
    )
    is_product_menu = fields.Boolean(
        string='Is Menu Product'
    )
    is_wrong_categ = fields.Boolean(
        string='Wrong Family',
        compute='_computed_family_validation'
    )
    aux_category = fields.Many2one(
        string='Family',
        comodel_name='product.category'
    )
    # adding new fields
    send_to_agora = fields.Boolean(
        string='Send to Agora',
        help='Allow to send the product to Agora.'
    )
    agora_taxes_id = fields.Many2many(
        comodel_name='account.tax',
        relation='agora_product_taxes_rel',
        column1='prod_id',
        column2='tax_id',
        help="Default taxes from Agora.",
        string='Agora Taxes',
        default=_get_agora_taxes
    )
    agora_product_ids = fields.One2many(
        string='Agora Products',
        comodel_name='agora.product',
        inverse_name='product_tmpl_id'
    )
    products_to_sync = fields.One2many(
        string='Products To Sync',
        comodel_name='product.instance.sync',
        inverse_name='product_templ_id'
    )
    instances_domain = fields.Many2many(
        comodel_name='api.connection',
        relation='product_instance_domain_rel',
        column1='prod_id',
        column2='connection_id',
        string='Instances Domain',
        compute='_get_instances_domain'
    )
    agora_instances = fields.Many2many(
        comodel_name='api.connection',
        relation='product_api_connection_rel',
        column1='prod_id',
        column2='connection_id',
        string='Agora Instances',
        help="Select the Agora instances to which you should send the product.",

    )
    category_domain = fields.Many2many(
        comodel_name='product.category',
        relation='product_category_domain_rel',
        column1='prod_id',
        column2='categ_id',
        string='Category Domain',
        help="Field to filter categ_id in the product.",
        compute='_get_category_domain'
    )
    # --------------------------------------
    #       Modifying standard fields
    # --------------------------------------
    # company_id = fields.Many2one(
    #     default=lambda self: self.env.company
    # )
    name = fields.Char(
        copy=False
    )
    type = fields.Selection(
        default='product'
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        mrp_bom_env = self.env['mrp.bom']
        mrp_bom_line_env = self.env['mrp.bom.line']
        product_env = self.env['product.product']
        product_sync_env = self.env['product.instance.sync']
        companies = self.env['res.company'].search([])
        is_first_charge = self.env.context.get('first_charge')
        if not is_first_charge:
            if res.parent_id:
                # When a format is created automatically a List of materials should be created
                # Should be created a list of material line too, as required in odoo
                material_list = mrp_bom_env.create({
                    'product_tmpl_id': res.id,
                    'type': 'phantom',
                    'company_id': res.company_id.id
                })
                product_product = product_env.search([('product_tmpl_id', '=', res.parent_id.id)], limit=1)
                mrp_bom_line_env.create({
                    'bom_id': material_list.id,
                    'product_id': product_product.id,
                    'product_qty': res.ratio,
                    'company_id': res.company_id.id
                })
            res.fields_validation()
            for instance in res.agora_instances:
                new_values = {
                    "product_templ_id": res.id,
                    "instance_id": instance.id,
                    "sync_status": "new",
                }
                product_sync_env.create(new_values)
        return res

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        product_sync_env = self.env['product.instance.sync']
        for rec in self:
            if vals.get('product_addins_ids'):
                rec.ask_for_addings = True
            if vals.get('ratio') and rec.parent_id:
                prods = rec.bom_ids.bom_line_ids.filtered(lambda l: l.product_id.product_tmpl_id.id == rec.parent_id.id)
                if prods:
                    prods.product_qty = rec.ratio
                instances = rec.agora_instances
                product_to_sync = product_sync_env.search([
                    ('product_templ_id', '=', rec.parent_id.id),
                    ('sync_status', '!=', 'new')]).filtered(lambda l: l.instance_id in instances)
                for prod in product_to_sync:
                    prod.sync_status = 'modified'
            if vals.get('uom_id'):
                rec.bom_line_ids.product_uom_id = rec.uom_id
            if vals.get('name') or vals.get('categ_id') or vals.get('ratio'):
                rec.fields_validation()
            # When products are archive/unarchive correspondent formats should be updated too
            if 'active' in vals and rec.product_formats_ids and vals.get('active') is False:
                rec.product_formats_ids.active = False
            if 'active' in vals and vals.get('active') is True:
                archived_formats = self.search([('parent_id', '=', rec.id), ('active', '=', False)])
                archived_formats.active = True
            # If new instances to sync are added or removed, we need to create or delete the record in the
            # product.instance.sync model
            if vals.get('agora_instances'):
                instances = vals['agora_instances'][0][2]
                prod_sync = self.products_to_sync.mapped('instance_id').ids
                instance_to_sync = [inst for inst in instances if inst not in prod_sync]
                for instance in instance_to_sync:
                    sync_status = "new"
                    # If the format has already been sent to agora at another time, the status must be "modified".
                    if any([inst.instance_id for inst in rec.agora_product_ids if inst.instance_id.id == instance]):
                        sync_status = "modified"
                    val = {
                        "product_templ_id": rec.id,
                        "instance_id": instance,
                        "sync_status": sync_status,
                    }
                    product_sync_env.create(val)
                    # If it is a format, we have to update the parent sync_status to "modified".
                    if rec.parent_id:
                        parent_prod_sync = product_sync_env.search([('product_templ_id', '=', rec.parent_id.id),
                                                                    ('instance_id', '=', instance)])
                        if parent_prod_sync:
                            parent_prod_sync.sync_status = "modified"
                # If you do not want to continue sending the product to an instance, that instance must be removed from
                # the synchronization model.
                inst_sync_delete = list(set(prod_sync) - set(instances))
                for inst in inst_sync_delete:
                    to_delete = product_sync_env.search([('product_templ_id', '=', rec.id), ('instance_id', '=', inst)])
                    to_delete.unlink()
        return res

    def unlink(self):
        """
        Overwrite the function to avoid the product deletion, always Products should be archive
        """
        for rec in self:
            # aqui hay que chequear si el producto tiene valores en la tabla agora.product
            # if rec.agora_id != 0 or rec.sale_format != 0:
            if rec.agora_product_ids:
                # If the product dont have agora_id and sale_format means is a new product dont sent to Agora
                # Can be deleted
                raise ValidationError(_('Sorry!! This product cant be deleted because its already synchronize'
                                        ' with Agora. Should be Archive instead'))
            if rec.is_product_discount:
                raise ValidationError(_('Sorry!! This product cant be deleted because its used'
                                        ' for discount by the system'))
            if rec.is_product_menu:
                raise ValidationError(_('Sorry!! This product cant be deleted because its used'
                                        ' for discount by the system'))
        return super(ProductTemplate, self).unlink()

    @api.onchange('aux_category')
    def onchange_aux_category(self):
        if self.aux_category:
            categs = self.search([('is_saleable_as_adding', '=', True),
                                  ('categ_id', '=', self.aux_category.id),
                                  ('company_id', '=', self.company_id.id)])
            self.product_addins_ids = [(6, 0, categs.mapped('id'))]
        else:
            self.product_addins_ids = [(6, 0, [])]

    @api.depends('company_id', 'parent_id')
    def _get_instances_domain(self):
        """Function to compute instances to filter in agora_instances field."""
        instance_env = self.env['api.connection']
        for rec in self:
            # Search all instances
            instances = instance_env.search([])
            # If the company is configured, just find the company instance
            if rec.company_id:
                instances = instance_env.search([('company_id', '=', rec.company_id.id)])
            # If the product is a format, the instances must be the parent product instances
            if rec.parent_id:
                instances = rec.parent_id.agora_instances.ids
            # In the xml view filter agora_instances by instances_domain
            rec.instances_domain = instances

    def _compute_sync_status(self):
        """
        Function to compute the product sync_status field depending on the value it has in the product_instance_sync
        model.
        """
        for rec in self:
            rec.sync_status = 'new'
            company = rec.company_id or self.env.company
            instance = self.env['api.connection'].search([('company_id', '=', company.id), ('state', '=', 'connect')])
            if rec.products_to_sync and instance:
                prod_sync = rec.products_to_sync.filtered(lambda l: l.instance_id == instance)
                rec.sync_status = prod_sync.sync_status

    @api.depends('company_id')
    def _compute_agora_taxes(self):
        for rec in self:
            # recs = self.env['agora.tax'].search([('company_id', '=', rec.company_id.id)])
            recs = self.env['agora.tax'].search([('agora_id', '!=', False), ('account_tax_id', '!=', False)])
            recs_taxes = recs.mapped('account_tax_id')
            rec.tax_agora_ids = recs_taxes.ids

    @api.depends('send_to_agora')
    def _get_category_domain(self):
        """Function to compute categories to filter in categ_id field."""
        prod_categ_env = self.env['product.category']
        for rec in self:
            # If the product will not be sent to agora, the categ_id field will not have a filter
            categories = prod_categ_env.search([])
            if rec.send_to_agora:
                # If the product will be sent to agora, we have to filter only categories that have the agora_id and
                # the company set
                categories = prod_categ_env.search([('agora_category_ids', '!=', False),
                                                    ('company_id', '=', self.company_id.id)])
            rec.category_domain = categories

    @api.depends('categ_id')
    def _computed_family_validation(self):
        for rec in self:
            is_wrong = False
            # if not rec.categ_id.agora_id:
            if not rec.categ_id.agora_category_ids:
                is_wrong = True
            rec.is_wrong_categ = is_wrong

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # When parent_id get a value Can be 'Sold' but can not be 'Purchased'
        # When parent_id is False Can be 'Sold' and 'Purchased'
        if self.parent_id:
            self.purchase_ok = False
            self.type = 'consu'
        else:
            self.purchase_ok = True
            self.type = 'product'

    @api.onchange('type')
    def onchange_parent_id(self):
        # When a product is 'Consumible' can be Sold but not 'Purchased'
        # When a product is 'Storaged' can be Sold and 'Purchased'
        if self.type == 'consu':
            self.purchase_ok = False
            self.sale_ok = True
        elif self.type == 'product':
            self.purchase_ok = True
            self.sale_ok = True

    @api.onchange('name')
    def change_button_text(self):
        # Set button test as default when Name is set
        if self.name:
            self.button_text = self.name

    def fields_validation(self):
        is_first_charge = self.env.context.get('first_charge')
        if not is_first_charge:
            # TODO ilike its not ok, because consider the product even if not match the whole product name
            # During the first charge any of these validations will be considering
            repeated = self.search([('name', 'ilike', self.name),
                                   ('company_id', '=', self.company_id.id),
                                   ('id', '!=', self.id)])
            # if repeated:
            #     raise ValidationError(_("Sorry!! Already exist a format with the same name."
            #                             " Duplicity are not allowed"))
            if self.parent_id and self.ratio <= 0:
                raise ValidationError(_("All Formats should have Ratio bigger than zero"))

    @api.constrains('agora_color', 'button_text', 'preparation_id', 'preparation_order_id', 'is_saleable_as_main',
                    'is_saleable_as_adding', 'is_sold_by_weight', 'ask_preparation_notes', 'ask_for_addings',
                    'print_zero', 'standard_price', 'active', 'categ_id', 'product_addins_ids', 'max_addings',
                    'min_addings')
    def verify_changed_values(self):
        is_first_charge = self.env.context.get('first_charge')
        product_sync_env = self.env['product.instance.sync']
        for rec in self:
            instances = rec.agora_instances
            if rec.parent_id:
                # If it is a format, we have to update the parent sync_status.
                product_to_sync = product_sync_env.search([
                    ('product_templ_id', '=', rec.parent_id.id),
                    ('sync_status', '!=', 'new')]).filtered(lambda l: l.instance_id in instances)
            else:
                # If it is a principal product, we have to update its sync_status.
                product_to_sync = product_sync_env.search([
                    ('product_templ_id', '=', rec.id),
                    ('sync_status', '!=', 'new')]).filtered(lambda l: l.instance_id in instances)
            # if not is_first_charge and rec.sync_status != 'new':
            if not is_first_charge and product_to_sync:
                # During the first charge is never set as 'modified'
                # Not even when is new
                for prod_sync in product_to_sync:
                    prod_sync.sync_status = 'modified'

    @api.constrains('agora_taxes_id')
    def validate_one_tax(self):
        for rec in self:
            if len(rec.agora_taxes_id) > 1:
                # Agora only allow one tax in the product
                # Same behaviour is replated in Odoo
                raise ValidationError(_('Sorry!! Only one Agora Tax can be set'))

    @api.constrains('product_sku')
    def validate_sku_duplicity(self):
        for rec in self:
            repeated = rec.search_count([('product_sku', '=', rec.product_sku)])
            if repeated > 1 and rec.product_sku:
                raise ValidationError(_('Please verify PLU value, exist already other product with the same value'))

    def action_sent_agora(self):
        """"
         Action to send 'New' and 'Modified' products to Agora
        """
        active_ids = self._context.get('active_ids')
        products = self.env['product.template'].search([('id', 'in', active_ids), ('active', 'in', [True, False])])
        if len(products.mapped('company_id')) > 1:
            raise ValidationError(_('Please select products from the same company at time to avoid Error Connection'))
        if products.mapped('parent_id'):
            raise ValidationError(_('Sorry this action should be executed from the Parent '
                                    'product and not from the format'))
        # Post products calling the main function in Api connection
        self.env['api.connection'].post_products(products)

    def action_add_format(self):
        """
         Action to add a new format inside of product template.
         Return:
              Action with the form view selected and some values set as default, coming from the main product
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.product_template_action")
        action.update({
            'views': '',
            'view_id': self.env.ref('product.product_template_only_form_view').id,
            'target': 'current',
            'view_mode': 'form',
            'context': {'default_parent_id': self.id,
                        'default_categ_id': self.categ_id.id,
                        'default_company_id': self.company_id.id,
                        'mail_create_nosubscribe': True,
                        'tracking_disable': True,
                        'default_list_price': 0.0,
                        'default_type': 'consu',
                        'default_agora_taxes_id': self.agora_taxes_id.ids,
                        'default_send_to_agora': True
                        }
        })
        return action

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        default_domain = self.env.context.get('default_domain')
        if default_domain:
            instance_id = self.env['api.connection'].search([('company_id', '=', self.env.company.id)])
            products_to_send = self.env['product.instance.sync'].search([('instance_id', '=', instance_id.id),
                                                                         ('sync_status', 'in', ['new', 'modified'])])
            products = products_to_send.product_templ_id.ids if products_to_send else False
            domain = [
                ('id', 'in', products),
                ('parent_id', '=', False),
                ('is_product_discount', '=', False),
                ('active', 'in', [True, False]),
                ('send_to_agora', '=', True)
            ]
            args += domain
        return super(ProductTemplate, self).search(args, offset=offset, limit=limit, order=order, count=count)


class ProductCompanySync(models.Model):
    _name = "product.instance.sync"
    _description = "Product Instance Synchronization Status"

    product_templ_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        required=True
    )
    instance_id = fields.Many2one(
        comodel_name="api.connection",
        string="Instance",
        required=True
    )
    sync_status = fields.Selection(
        selection=[
            ('done', 'Completed'),
            ('new', 'New'),
            ('modified', 'Modified'),
            ('error', 'Error')],
        string="Sync Status",
        default="new"
    )
