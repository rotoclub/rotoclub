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
    _logger.info("*****************entre en el post migration")
    update_price_include(env)


def update_price_include(env):
    """
    Method that change to true all the taxes price_include field
    """
    moves = env['account.move'].search([('company_id', '=', 12), ('id', '=', 648916)])
    _logger.info("*****************Estas son las faturas a modficar : %s", len(moves))
    for move in moves:
        move._compute_amount()
