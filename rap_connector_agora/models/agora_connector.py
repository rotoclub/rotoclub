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


# class DateEgginWizard(models.TransientModel):
#     _name = 'date.eggin.wizard'
#     _description = 'Date Eggin Wizard'
#     _rec_name = 'type_date'
#
#     type_date = fields.Selection([
#         ('today', 'Today'),
#         ('yesterday', 'Yesterday'),
#         ('dates', 'Other dates')
#     ], string='Filter', index=True, required=True, default='today')
#     start_date = fields.Date('Date Init')
#     end_date = fields.Date('Date Finish')
#
#     def action_create_records(self):
#         if self.env.context.get('active_id'):
#             active_id = self.env.context.get('active_id')
#             connect_settings = self.env['eggin.setting'].search([('id', '=', active_id), ('state', '=', 'connect')])
#             for eggin_setting in connect_settings:
#                 eggin_setting._connector_eggin_api(self)
#
#
# class CrossEmployee(models.Model):
#     _name = 'cross.employee'
#     _description = 'Cross Employee'
#
#     name = fields.Char('Username Eggin', index=True, default='new', required=True)
#     eggin_id = fields.Many2one('eggin.setting', 'Setting')
#     company_id = fields.Many2one(related="eggin_id.company_id", string='Company')
#     employee_id = fields.Many2one('hr.employee', 'Employee', index=True)
#     society = fields.Selection([
#         ('0', '-'),
#         ('1', 'Arch SA'),
#         ('2', 'Source Procurement'),
#         ('3', 'Arch Creativity'),
#         ('4', 'Ventiventi'),
#     ], string='Society', index=True, default='0')
#
#     @api.constrains('name', 'employee_id')
#     def _check_name_employee_exists(self):
#         obj_cross_employee_ids = self.env['cross.employee']
#         for record in self:
#             obj_cross_employee_ids.search([('eggin_id', '=', record.id)])
#             if record.name:
#                 if any(obj_cross_employee_ids.filtered(lambda r: r.name == record.name)):
#                     raise UserError(_("The username must be unique"))
#             if record.employee_id:
#                 if any(obj_cross_employee_ids.filtered(lambda r: r.employee_id == record.employee_id)):
#                     raise UserError(_("The employee must be unique"))
#
#     def action_read_cross(self):
#         self.ensure_one()
#         return {
#             'name': self.display_name,
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'cross.employee',
#             'res_id': self.id,
#         }
#
#
# class EgginLog(models.Model):
#     _name = 'eggin.log'
#     _description = 'Log'
#
#     name = fields.Char('API', index=True, required=True)
#     server_id = fields.Many2one('eggin.server', 'Server')
#     content_dict = fields.Text('Dictionary')
#     count_record = fields.Char('Records')
#     eggin_id = fields.Many2one('eggin.setting', 'Setting')
#     company_id = fields.Many2one(related="eggin_id.company_id", string='Company')
#
#     def action_read_log(self):
#         self.ensure_one()
#         return {
#             'name': self.display_name,
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'eggin.log',
#             'res_id': self.id,
#         }
#
#
class AgoraAPI(models.Model):
    _name = 'agora.api'
    _description = 'Agora API'
    _order = 'id desc'

    name = fields.Char('Name', index=True, default='New', required=True)
    title = fields.Char('Title', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', copy=False, check_company=True,  domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="The analytic account related to a Agora API.")
    agora_id = fields.Many2one('agora.server', 'Server')
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
    # sale_api_ids = fields.One2many('sale.api', 'api_server_id')
    # sale_api_count = fields.Integer(compute='_compute_sale_api_count')
    user_id = fields.Many2one('res.users', 'Sales Person', index=True, required=True,
                              default=lambda self: self.env.user)
    # sale_order_ids = fields.Many2many('sale.order', compute='_get_all')
    # sale_order_count = fields.Integer(compute='_get_all')
    # picking_ids = fields.Many2many('stock.picking', compute='_get_all')
    # picking_count = fields.Integer(compute='_get_all')
    # invoice_ids = fields.Many2many('account.move', compute='_get_all')
    # invoice_count = fields.Integer(compute='_get_all')
    # payment_ids = fields.Many2many('account.payment', compute='_get_all')
    # payment_count = fields.Integer(compute='_get_all')
    search_product_by = fields.Selection([
        ('id', 'Id'),
        ('reference', 'Reference'),
        ('sku', 'SKU')], string='Search Product By', default='id')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('agora.api', sequence_date=seq_date) or _('New')
        return super(AgoraAPI, self).create(vals)

    # server_ip = fields.Char('IP')
    # server_user = fields.Char('User')
    # server_api_key = fields.Char('Api Pass')
    # consumer_key = fields.Char('Consumer key')
    # consumer_secret = fields.Char('Consumer secret')
    # access_token = fields.Char('Access token')
    # token_secret = fields.Char('Token secret')
    # limit_sale_order = fields.Integer('Limit Sale Order')

    # handling_shipping_product_id = fields.Many2one(comodel_name="product.product", string="Handling Shipping Product")

    # """
    # order_ids = fields.One2many('sale.order', 'magento_server_id', 'Order')
    # order_count = fields.Integer('Orders', compute='_compute_order_count')
    # """

    # limit_origin = fields.Char('Limit Number')

    # """
    # def action_view_orders(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Órdenes creadas',
    #         'res_model': 'sale.order',
    #         'view_mode': 'tree,kanban,calendar,pivot,graph,form',
    #         'view_type': 'form',
    #         'domain': [('id', 'in', self.order_ids.ids)]
    #     }"""
    #
    # """
    # def _compute_order_count(self):
    #     for record in self:
    #         record.order_count = len(record.order_ids)"""
    #
    # version = fields.Selection([
    #     ('1.9', '1.9'),
    #     ('2.0', '2.0'),
    #     ('2.4', '>= 2.4')],
    #     string='Version', index=True,  default='1.9', track_visibility='onchange', copy=False)
    #
    # state = fields.Selection([
    #     ('open', 'Open'),
    #     ('close', 'Close')],
    #     string='State', index=True, readonly=True, default='close', track_visibility='onchange', copy=False)
    #
    # notes = fields.Text('Notes')
    #
    # user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    #
    # api_server_id = fields.Many2one('sale.api.server.config', string='API Server')
    #
    # company_id = fields.Many2one('res.company', string="Company", required=True,
    #                              default=lambda self: self.env.user.company_id.id)
    #
    # entry_date = fields.Datetime('Entry date', default=fields.Datetime.now)
    #
    # last_conexion = fields.Datetime('Last Conexion')
#

#     log_ids = fields.One2many('eggin.log', 'server_id', 'Log')
#
#     @api.model
#     def create(self, vals):
#         if not vals.get('name'):
#             seq_date = None
#             vals['name'] = self.env['ir.sequence'].next_by_code('eggin.server', sequence_date=seq_date) or _('New')
#         return super(EgginServer, self).create(vals)


class AgoraServer(models.Model):
    _name = 'agora.server'
    _description = 'Server'

#     def _default_url(self):
#         return 'https://smartthings.altervista.org'
#
#     def _default_server(self):
#         return 'https://smartthings.altervista.org/clock/esporta.php'
#
    name = fields.Char('Name', index=True, default='New')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
#     url = fields.Char('URL', default=_default_url)
#     url_server = fields.Char('Server', default=_default_server)
    check_message = fields.Boolean('Message?', default=False)
    state = fields.Selection([
        ('no_connect', 'Not connected'),
        ('connect', 'Connected')
    ], string='Status', index=True, default='no_connect')
#     f_checking = fields.Char('F. check-in', help="First check-in in Eggin", default='1IN')
#     checking = fields.Char('Check-in', help="Check-in in Eggin", default='IN')
#     checkout = fields.Char('Check-out', help="Check-out in Eggin", default='OUT')
#     employee_ids = fields.One2many('cross.employee', 'eggin_id', 'Employees')
    count_api = fields.Integer(compute='_compute_agora_api')
    limit_sale_order = fields.Integer('Limit Sale Order')
    limit_origin = fields.Integer('Limit Number')
    default_product_id = fields.Many2one(comodel_name="product.product", string="Default Product")

    # order_ids = fields.One2many('sale.order', 'magento_server_id', 'Order')
    # order_count = fields.Integer('Orders', compute='_compute_order_count')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('agora.server', sequence_date=seq_date) or _('New')
        return super(AgoraServer, self).create(vals)
#
#     def get_connection(self):
#         for record in self:
#             try:
#                 connect = requests.get(record.url_server)
#                 if connect:
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

    def _compute_agora_api(self):
        agora_api = self.env['agora.api']
        for record in self:
            record.count_api = len(agora_api.search([('agora_id', '=', record.id)]))

    def action_view_server(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agora APIs',
            'res_model': 'agora.api',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': [('agora_id', '=', self.id)],
            'context': {'default_agora_id': self.id}
        }

#     def get_info_eggin(self, setting, wizard):
#         attendances = []
#         ir_config_obj = self.env['ir.config_parameter']
#         url = setting.url_server
#         if self.env.context.get('origin_view') == 'wizard_filter':
#             if wizard.type_date:
#                 period = 1
#                 if wizard.type_date == 'today':
#                     data = '?fromdata=' + str(date.today()) + '&todata=' + str(
#                         date.today() + timedelta(days=int(period)))
#                 elif wizard.type_date == 'yesterday':
#                     data = '?fromdata=' + str(date.today() - timedelta(days=int(period))) + '&todata=' + str(
#                         date.today())
#                 else:
#                     data = '?fromdata=' + str(wizard.start_date) + '&todata=' + str(wizard.end_date)
#         else:
#             period = ir_config_obj.get_param('eggin.api.period')
#             data = '?fromdata=' + str(date.today() - timedelta(days=int(period))) + '&todata=' + str(date.today())
#         url += data
#         response = requests.get(url)
#         if response.text != 'zero':
#             attendances = json.loads(response.text)
#         return attendances
#
#     @staticmethod
#     def action_open_wizard(self):
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Import records',
#             'res_model': 'date.eggin.wizard',
#             'view_mode': 'form',
#             'view_type': 'form',
#             'target': 'new',
#             'context': {'origin_view': 'wizard_filter'}
#         }
#
#     def generated_attendance_by_eggin(self, obj_eggin, setting):
#         create_attendance = self.env['hr.attendance']
#         # Mapped eggin username with the employees name
#         list_employees = [eggin for eggin in obj_eggin if
#                           obj_eggin and eggin['username'] in setting.employee_ids.mapped('name')]
#         list_item = [item for item in setting.employee_ids]
#         # Group the attendance list by username
#         list_attendance = [{'username': item, 'values': [attendance for attendance in list_employees if
#                                                          attendance['username'] == item.name]} for item in list_item]
#         for attendance in list_attendance:
#             attendance_in = ''
#             attendance_out = ''
#             # List of all check_in and check_out for the user in the range of date
#             list_current_attendance = attendance['values']
#             # Group the check_in and check_out by date
#             attendance_by_date = self._group_attendande_by_date(list_current_attendance)
#             for att_key, att_value in attendance_by_date.items():
#                 # att_value contains the list of check_in and check_out for each day
#                 total_attendances = len(att_value)
#                 current_position = total_attendances - 1
#                 sum_hours = timedelta()
#                 list_action = []
#                 # Go through the list starting by the last position which is the first register(IN or OUT)
#                 while current_position >= 0:
#                     # If value is distinct of "OUT" is an IN or 1IN
#                     if att_value[current_position]['verso'] != "OUT":
#                         # Create the attendance check_in
#                         attendance_in = att_value[current_position]['CAST(Time AS date)'] + ' ' + att_value[current_position]['CAST(Time AS time)']
#                         current_position -= 1
#                         if current_position >= 0:
#                             if att_value[current_position]['verso'] == "OUT":
#                                 # Create the attendance check_out
#                                 attendance_out = att_value[current_position]['CAST(Time AS date)'] + ' ' + att_value[current_position]['CAST(Time AS time)']
#                                 current_position -= 1
#                             # Difference between check_out and check_in
#                             diff_hour = datetime.strptime(attendance_out, '%Y-%m-%d %H:%M:%S') - datetime.strptime(attendance_in, '%Y-%m-%d %H:%M:%S')
#                             # Total of hours worked for the day
#                             sum_hours += diff_hour
#                             # Add the attendance to the list
#                             list_action.append({'employee_id': attendance['username'].employee_id.id, 'check_in': attendance_in, 'check_out': attendance_out})
#                     else:
#                         # just decrement the position of the counter
#                         current_position -= 1
#                 if list_action:
#                     self.check_and_create_attendance(attendance, create_attendance, list_action, sum_hours)
#
#     def check_and_create_attendance(self, attendance, create_attendance, list_action, sum_hours):
#         hours_per_day = attendance['username'].employee_id.resource_calendar_id.hours_per_day * 3600
#         employee_work_hours = timedelta(0, hours_per_day, 0, 0)
#         for rec in list_action:
#             check_in = rec['check_in']
#             check_out = rec['check_out']
#             obj_result_employee = self.all_attendance_by_employee(create_attendance, attendance, check_in, check_out)
#             if not obj_result_employee:
#                 create_attendance.create(rec)
#             if sum_hours <= employee_work_hours:
#                 # Check if the user has time off for this day
#                 date_att = date.fromisoformat(list_action[0]['check_in'].split(' ')[0])
#                 leave_env = self.env['hr.leave'].search(
#                     [('employee_id', '=', attendance['username'].employee_id.id), ('request_date_from', '=', date_att)])
#                 if leave_env:
#                     attendance_in = leave_env.date_from
#                     attendance_out = leave_env.date_to
#                     new_attendance = {'employee_id': attendance['username'].employee_id.id, 'check_in': attendance_in,
#                                       'check_out': attendance_out}
#                     obj_result_employee = self.all_attendance_by_employee(create_attendance, attendance, attendance_in,
#                                                                           attendance_out)
#                     if not obj_result_employee:
#                         create_attendance.create(new_attendance)
#
#     def all_attendance_by_employee(self, create_attendance, attendance, check_in, check_out):
#         obj_result_employee = create_attendance.search(
#             [('employee_id', '=', attendance['username'].employee_id.id), ('check_in', '=', check_in),
#              ('check_out', '=', check_out)])
#         if obj_result_employee:
#             return True
#         return False
#
#     def _group_attendande_by_date(self, list_current_attendance):
#         att_by_date = {}
#         for rec in list_current_attendance:
#             att_date = rec['CAST(Time AS date)']
#             if att_date not in att_by_date:
#                 att_by_date[att_date] = [rec]
#             else:
#                 att_by_date[att_date].append(rec)
#         sorted_dict_by_date = {}
#         for i in sorted(att_by_date.keys(), key=lambda item: (datetime.strptime(item, '%Y-%m-%d'))):
#             sorted_dict_by_date[i] = att_by_date[i]
#         return sorted_dict_by_date
#
#     def _connector_eggin_api(self, wizard=False):
#         domain = [('state', '=', 'connect')]
#         if self.env.context.get('origin_view') and self.env.context.get('origin_view') == 'wizard_filter':
#             active_id = self.env.context.get('active_id')
#             domain.append(('id', '=', active_id))
#         obj_settings = self.env['eggin.setting'].search(domain)
#         if obj_settings:
#             obj_server = self.env['eggin.server']
#             obj_log = self.env['eggin.log']
#             for record in obj_settings:
#                 dict_server = {
#                     'eggin_id': record.id
#                 }
#                 dict_log = {
#                     'name': 'New',
#                     'server_id': False,
#                     'eggin_id': False,
#                     'count_record': 0
#                 }
#                 create_obj = obj_server.create(dict_server)
#                 if create_obj:
#                     dict_log['server_id'] = create_obj.id
#                     dict_log['eggin_id'] = record.id
#                     obj_connection = record.get_connection()
#                     if obj_connection:
#                         if obj_connection['status_code'] == 200:
#                             obj_eggin = self.get_info_eggin(record, wizard)
#                             if obj_eggin:
#                                 dict_log['name'] = 'Attendance Eggin'
#                                 dict_log['content_dict'] = obj_eggin
#                                 dict_log['count_record'] = len(obj_eggin)
#                                 obj_log.create(dict_log)
#                                 self.generated_attendance_by_eggin(obj_eggin, record)
#                             else:
#                                 create_obj.message_post(body=_("There are no records to import at this moment."))
#