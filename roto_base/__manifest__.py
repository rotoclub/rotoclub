# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Roto Base",
    'category': 'Extra Tools',
    'summary': """Module Base for the rigth and general behavior""",
    'description': """All the general functionalities will be group in this module""",
    'license': 'AGPL-3',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",

    'version': '15.0.1.0.0',

    'depends': [
        'base',
        'mail',
        'contacts',
        'base_vat'
    ],
    'data': [
        'views/res_country_view.xml',
    ],
    'application': False,
}
