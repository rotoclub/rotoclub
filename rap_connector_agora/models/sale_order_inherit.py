# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tip_move_id = fields.Many2one(
        string='Tip Move',
        comodel_name='account.move'
    )

    def action_tips_moves(self):
        """ Redirect the user move related with Tips.
        :return:    An action on account.move.
        """
        self.ensure_one()

        action = {
            'name': _("Tips Move"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'form',
            'res_id': self.tip_move_id.id,
        })
        return action

    def generate_tip_account(self):
        """
        Function to create a move account, to compute the tips Amount.
        The tips amount should not be considered with the Invoice directly. That's why is done directly the move.
        """
        # search the journal for sales
        journal_id = self.env['account.mapping'].search([('company_id', '=', self.company_id.id)], limit=1).tip_journal_id
        accounts = self.env['tips.config'].search([('company_id', '=', self.company_id.id),
                                                   ('sale_center_id', '=', self.sale_center_id.id)], limit=1)
        lines_type = ['debit', 'credit']
        # prepare the value dictionary to create the movement
        vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'entry',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'line_ids': [],
        }
        if journal_id:
            vals.update({'journal_id': journal_id.id})
        # add the invoice lines according to the order line list
        for value in lines_type:
            debit = 0.0
            credit = 0.0
            if value == 'debit':
                debit = self.tips_amount
                account_id = accounts.counterpart_account_id.id
            else:
                credit = self.tips_amount
                account_id = accounts.account_id.id
            vals['line_ids'].append((0, 0,
                                     {'analytic_account_id': self.sale_center_id.analytic_id.id if self.sale_center_id else False,
                                      'partner_id': self.partner_id.id,
                                      'name': 'Tip({})'.format(self.name),
                                      'company_id': self.company_id.id,
                                      'account_id': account_id,
                                      'debit': debit,
                                      'credit': credit,
                                      }))
        # create move
        invoice_obj = self.env['account.move'].create(vals)
        # validate the new move
        invoice_obj.action_post()
        self.tip_move_id = invoice_obj


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_addins = fields.Boolean(
        string='Is Addins'
    )
    is_invitation = fields.Boolean(
        string='Invitation'
    )
    index = fields.Integer(
        string='Index',
        help='Number of the line coming from Agora to be identify'
    )
    agora_loss_id = fields.Integer(
        string='Agora Loss'
    )
