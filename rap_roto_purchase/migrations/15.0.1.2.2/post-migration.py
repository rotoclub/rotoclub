# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration to update some configs
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    force_supplier_update_qty(env)

def force_supplier_update_qty(env):
    """
    Method that re-calculate product supplier prices
    """
    products = env['product.supplierinfo'].search([])
    for product in products:
        _logger.info('Will update Product {}--{}'.format(product.product_name, product.id))
        product._onchange_supplier_qty()
