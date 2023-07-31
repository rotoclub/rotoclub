# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Roto Accounting",
    'summary': 'Changes to be consider in Roto CLub Odoo enviroment',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',

    'version': '15.0.1.0.7',

    'depends': [
        'base',
        'purchase',
        'sale_management',
        'account_accountant',
        'account_asset',
        'analytic',
        'stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/roto_view.xml',
        'wizards/sell_assets_inherit_views.xml',
    ],
    'application': False,
}
