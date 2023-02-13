# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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
    color = fields.Char(
        string='Color'
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
        default='new'
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
    is_wrong_categ = fields.Boolean(
        string='Wrong Family',
        compute='_computed_family_validation'
    )
    aux_category = fields.Many2one(
        string='Family',
        comodel_name='product.category'
    )
    # --------------------------------------
    #       Modifying standard fields
    # --------------------------------------
    company_id = fields.Many2one(
        default=lambda self: self.env.company
    )
    name = fields.Char(
        copy=False
    )
    detailed_type = fields.Selection(
        default='product'
    )

    @api.model
    def create(self, vals):
        res = super().create(vals)
        mrp_bom_env = self.env['mrp.bom']
        mrp_bom_line_env = self.env['mrp.bom.line']
        product_env = self.env['product.product']
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
        return res

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        for rec in self:
            if vals.get('product_addins_ids'):
                rec.ask_for_addings = True
            if vals.get('ratio') and rec.parent_id:
                prods = rec.bom_ids.bom_line_ids.filtered(lambda l: l.product_id.product_tmpl_id.id == rec.parent_id.id)
                if prods:
                    prods.product_qty = rec.ratio
            if vals.get('uom_id'):
                rec.bom_line_ids.product_uom_id = rec.uom_id
            if vals.get('name') or vals.get('categ_id') or vals.get('ratio'):
                rec.fields_validation()
        return res

    def unlink(self):
        """
        Overwrite the function to avoid the product deletion, always Products should be archive
        """
        for rec in self:
            if rec.agora_id != 0 or rec.sale_format != 0:
                # If the product dont have agora_id and sale_format means is a new product dont sent to Agora
                # Can be deleted
                raise ValidationError(_('Sorry!! This product cant be deleted because its already synchronize'
                                        ' with Agora. Should be Archive instead'))
            if rec.is_product_discount:
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

    @api.depends('company_id')
    def _compute_agora_taxes(self):
        for rec in self:
            recs = self.env['agora.tax'].search([('company_id', '=', rec.company_id.id)])
            recs_taxes = recs.mapped('account_tax_id')
            rec.tax_agora_ids = recs_taxes.ids

    @api.depends('categ_id')
    def _computed_family_validation(self):
        for rec in self:
            is_wrong = False
            if not rec.categ_id.agora_id:
                is_wrong = True
            rec.is_wrong_categ = is_wrong

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # When parent_id get a value Can be 'Sold' but can not be 'Purchased'
        # When parent_id is False Can be 'Sold' and 'Purchased'
        if self.parent_id:
            self.purchase_ok = False
            self.detailed_type = 'consu'
        else:
            self.purchase_ok = True
            self.detailed_type = 'product'

    @api.onchange('detailed_type')
    def onchange_parent_id(self):
        # When a product is 'Consumible' can be Sold but not 'Purchased'
        # When a product is 'Storaged' can be Sold and 'Purchased'
        if self.detailed_type == 'consu':
            self.purchase_ok = False
            self.sale_ok = True
        elif self.detailed_type == 'product':
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
            # During the first charge any of these validations will be considering
            repeated = self.search([('name', 'ilike', self.name),
                                   ('company_id', '=', self.company_id.id),
                                   ('id', '!=', self.id)])
            # if repeated:
            #     raise ValidationError(_("Sorry!! Already exist a format with the same name."
            #                             " Duplicity are not allowed"))
            if self.parent_id and self.ratio <= 0:
                raise ValidationError(_("All Formats should have Ratio bigger than zero"))

    @api.constrains(lambda self: self.get_onchange_fields())
    def verify_changed_values(self):
        is_first_charge = self.env.context.get('first_charge')
        for rec in self:
            if not is_first_charge and rec.sync_status != 'new':
                # During the first charge is never set as 'modified'
                # Not even when is new
                if rec.parent_id:
                    rec.parent_id.sync_status = 'modified'
                else:
                    rec.sync_status = 'modified'

    @api.constrains('taxes_id')
    def validate_one_tax(self):
        for rec in self:
            if len(rec.taxes_id) > 1:
                # Agora only allow one tax in the product
                # Same behaviour is replated in Odoo
                raise ValidationError(_('Sorry!! Only one Tax can be set'))

    @api.constrains('product_sku')
    def validate_sku_duplicity(self):
        for rec in self:
            repeated = rec.search_count([('product_sku', '=', rec.product_sku)])
            if repeated > 1 and rec.product_sku:
                raise ValidationError(_('Please verify PLU value, exist already other product with the same value'))

    @api.constrains('product_formats_ids')
    def update_state(self):
        for rec in self:
            if rec.sync_status != 'new':
                rec.sync_status = 'modified'

    @staticmethod
    def get_onchange_fields():
        """"
            Function to get the fields to be consider in a constrains to detect
            important changes in a product.
            Return: List of strings(field's name)
        """
        return ['color', 'button_text', 'preparation_id', 'preparation_order_id', 'is_saleable_as_main',
                'is_saleable_as_adding', 'is_sold_by_weight', 'ask_preparation_notes', 'ask_for_addings', 'print_zero',
                'standard_price', 'active', 'categ_id', 'product_addins_ids', 'max_addings', 'min_addings', 'taxes_id']

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
        """"
         Action to add a new format inside of product template.
         Return:
              Action with the form view seleted and some values set as default, coming from the main product
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
                        'default_detailed_type': 'consu',
                        'default_taxes_id': self.taxes_id.ids,
                        }
        })
        return action
