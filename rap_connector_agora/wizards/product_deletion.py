# -*- coding: utf-8 -*-
# Copyright 2021-TODAY Rapsodoo Italia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, api, _


class ProductDeletionWizard(models.TransientModel):
    _name = 'product.deletion.wizard'
    _description = 'Wizard when product is deleted'

    def archive_product_template(self):
        for rec in self:
            rec.active = False
