# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from . import models
from . import wizards
from odoo import api, SUPERUSER_ID


def create_data(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([])
    order_data = get_prep_order_data()
    type_data = get_prep_type_data()
    tax_data = get_tax_data()
    for company in companies:
        env['res.partner'].create({
            'name': 'Generic Client {}'.format(company.name),
            'company_id': company.id
        })
        for order in order_data:
            env['preparation.order'].create({
              'name': order.get('name'),
              'agora_id': order.get('agora_id'),
              'company_id': company.id
            })
        for type in type_data:
            env['preparation.type'].create({
              'name': type.get('name'),
              'agora_id': type.get('agora_id'),
              'company_id': company.id
            })
        for tax in tax_data:
            env['agora.tax'].create({
                'name': tax.get('name'),
                'agora_id': tax.get('agora_id'),
                'company_id': company.id
            })
        env['product.template'].create({
            'name': 'Discount Product [{}]'.format(company.name),
            'type': 'service',
            'default_code': 'Discount',
            'invoice_policy': 'order',
            'is_product_discount': True,
            'company_id': company.id
        })


def get_prep_order_data():
    data = [
        {'name': 'Bebidas', 'agora_id': 1},
        {'name': 'Primeros', 'agora_id': 2},
        {'name': 'Segundos', 'agora_id': 3},
        {'name': 'Postres', 'agora_id': 4},
    ]
    return data


def get_prep_type_data():
    data = [
        {'name': 'Barra', 'agora_id': 1},
        {'name': 'Cocina', 'agora_id': 2},
        {'name': 'Frio', 'agora_id': 3},
        {'name': 'Pescados', 'agora_id': 4},
        {'name': 'Carnes', 'agora_id': 5},
        {'name': 'Sushi', 'agora_id': 6},
        {'name': 'Postres', 'agora_id': 7},
        {'name': 'Cocktails', 'agora_id': 8},
        {'name': 'No imprime Barra', 'agora_id': 9}
    ]
    return data


def get_tax_data():
    data = [
        {'name': 'Exento', 'agora_id': 1},
        {'name': 'Super reducido', 'agora_id': 2},
        {'name': 'Reducido', 'agora_id': 3},
        {'name': 'General', 'agora_id': 4},
    ]
    return data

