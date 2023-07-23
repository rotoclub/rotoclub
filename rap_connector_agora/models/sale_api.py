# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class SaleApis(models.Model):
    _description = "Sale Api"
    _name = 'sale.api'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )
    data_date = fields.Date(
        string='Data Date'
    )
    api_line_ids = fields.One2many(
        comodel_name='sale.api.line',
        inverse_name='sale_api_id',
        string='API lines'
    )
    executed_by = fields.Many2one(
        string='Executed by',
        comodel_name='res.users'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company'
    )
    draft_state_count = fields.Integer(
        string='Draft count',
        compute="_compute_total_record_count"
    )
    fail_state_count = fields.Integer(
        string='Failed count',
        compute="_compute_total_record_count"
    )
    done_state_count = fields.Integer(
        string='Done count',
        compute="_compute_total_record_count"
    )
    state = fields.Selection(
        string='State',
        selection=[("draft", "Draft"),
                   ("fail", "Failed"),
                   ("done", "Done")],
        compute='_compute_state_log'
    )
    is_completed = fields.Boolean(
        string='Is completed',
        compute='_compute_completed_logs'
    )

    @api.depends('api_line_ids', 'api_line_ids.state')
    def _compute_completed_logs(self):
        for rec in self:
            complet = True
            draft = rec.api_line_ids.filtered(lambda l: l.state == 'draft')
            if draft:
                complet = False
            rec.is_completed = complet

    @api.depends('api_line_ids', 'api_line_ids.state')
    def _compute_state_log(self):
        for rec in self:
            state = 'draft'
            if rec.api_line_ids:
                fails = rec.api_line_ids.filtered(lambda l: l.state == 'fail')
                drafts = rec.api_line_ids.filtered(lambda l: l.state == 'draft')
                if fails:
                    state = 'fail'
                elif not fails and not drafts:
                    state = 'done'
            rec.state = state

    @api.depends('data_date')
    def _compute_name(self):
        for rec in self:
            rec.name = 'Orders({})'.format(str(rec.data_date))

    @api.depends("api_line_ids.state")
    def _compute_total_record_count(self):
        """
        This method used to count records of queue line base on the queue state.
        It displays the count records in the form view of the queue.
        """
        for record in self:
            lines = record.api_line_ids
            record.total_record_count = len(lines)
            record.draft_state_count = len(lines.filtered(lambda x: x.state == "draft"))
            record.done_state_count = len(lines.filtered(lambda x: x.state == "done"))
            record.fail_state_count = len(lines.filtered(lambda x: x.state == "failed"))


class SaleApiLine(models.Model):
    _name = 'sale.api.line'
    _description = 'Sale Api lines'

    name = fields.Char(
        string='name'
    )
    state = fields.Selection(
        selection=[("draft", "Draft"),
                   ("fail", "Failed"),
                   ("done", "Done")],
        default="draft"
    )
    order_data = fields.Text(
        string='Order Data'
    )
    sale_api_id = fields.Many2one(
        comodel_name='sale.api',
        string='Sale API'
    )
    company_id = fields.Many2one(
        related='sale_api_id.company_id'
    )
    order_customer = fields.Char(
        string='Customer'
    )
    ticket_number = fields.Integer(
        string='Ticket Number'
    )
    ticket_serial = fields.Char(
        string='Ticket Serial'
    )
    document_type = fields.Char(
        string='Document Type'
    )
    message = fields.Text(
        string='Error Message'
    )
    product_with_error = fields.Char(
        string='Products with error'
    )

    def update_log_message(self, value):
        message = ''
        if value == 1:
            message = "There is at least One product not identified." \
                      " Probably its necessary a masive Product List Update"
        self.update({'message': message, 'state': 'fail'})

    def update_product_error(self, product):
        message = self.product_with_error
        if message:
            self.product_with_error = '{},{}'.format(message, product)
        else:
            self.product_with_error = '{}'.format(product)
