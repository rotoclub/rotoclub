# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': 'Agora connector',
    'version': '15.0.1.0.5',
    'category': 'Extra Tools',
    'summary': """Agora connector: Sales in Odoo""",
    'description': """Agora connector: Sales, Customer, Invoice address, Products in Odoo""",
    'license': 'LGPL-3',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'depends': [
        'base',
        'sale_management',
        'sales_team',
        'mail',
        'sales_team',
        'sale',
        'stock',
        'account',
        'account_accountant',
        'analytic'
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/agora_connector_views.xml',
        'views/sale_api_views.xml',
        'views/sale_order_view.xml',
        'views/views_inherits.xml',
        'views/sale_center.xml',
        'data/agora_data.xml',
        'data/crons.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
