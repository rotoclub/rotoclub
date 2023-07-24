# Copyright 2023-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Roto Purchases",
    'summary': 'Changes referent to Purchases',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'category': 'Uncategorized',
    'license': 'LGPL-3',

    'version': '15.0.1.2.3',

    'depends': [
        'base',
        'product',
        'purchase',
        'purchase_stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/roto_view.xml',
        'data/crons.xml'
    ],
    'application': False,
}
