# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
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
        string='Company',
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

