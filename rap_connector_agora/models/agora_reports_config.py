# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class AgoraReportsConfig(models.Model):
    _name = 'agora.reports.config'
    _description = 'Configuration for Custom reports in Agora.' \
                   ' The Reports should be created in Agora, in Odoo anly will be consumed'

    name = fields.Char(
        string='Name'
    )
    guid = fields.Char(
        string='Guid',
        copy=False
    )
    description = fields.Char(
        string='Description'
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        default=lambda self: self.env.company
    )
    report_type = fields.Selection(
        selection=[
            ('last_ids', 'Last Ids report'),
            ('loss', 'Product Loss report')],
        string='Report Type'
    )
    last_update = fields.Datetime(
        string='Last Update'
    )
